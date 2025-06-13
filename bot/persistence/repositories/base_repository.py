import asyncio
import logging
from typing import TypeVar, Generic, List, Optional, Dict, Any, Callable
from datetime import datetime, timedelta
from abc import ABC

from bot.persistence.core.interfaces import IRepository, IEntity, IStorageBackend, ISession
from bot.persistence.core.exceptions import EntityNotFoundException, EntityAlreadyExistsException, ValidationException
from bot.persistence.config.settings import PersistenceConfig

EntityType = TypeVar('EntityType', bound=IEntity)
IDType = TypeVar('IDType')

logger = logging.getLogger(__name__)

class BaseRepository(IRepository[EntityType, IDType], Generic[EntityType, IDType]):
    """Base implementation of repository pattern with caching and validation"""
    
    def __init__(self, 
                 entity_class: type,
                 storage_backend: IStorageBackend,
                 config: PersistenceConfig,
                 collection_key: str):
        self.entity_class = entity_class
        self.storage_backend = storage_backend
        self.config = config
        self.collection_key = collection_key
        
        # In-memory cache
        self._cache: Dict[IDType, EntityType] = {}
        self._cache_timestamps: Dict[IDType, datetime] = {}
        self._dirty_entities: set = set()  # Track entities that need saving
        
        # Validation functions
        self._validators: List[Callable[[EntityType], bool]] = []
        
        logger.info(f"Initialized repository for {entity_class.__name__}")
    
    def add_validator(self, validator: Callable[[EntityType], bool]):
        """Add a custom validator function"""
        self._validators.append(validator)
    
    def _validate_entity(self, entity: EntityType) -> bool:
        """Run all validators on an entity"""
        if not self.config.validation.validate_on_save:
            return True
            
        for validator in self._validators:
            if not validator(entity):
                return False
        return True
    
    def _is_cache_valid(self, entity_id: IDType) -> bool:
        """Check if cached entity is still valid"""
        if not self.config.cache.enabled:
            return False
            
        if entity_id not in self._cache_timestamps:
            return False
            
        age = datetime.now() - self._cache_timestamps[entity_id]
        return age.total_seconds() < self.config.cache.ttl_seconds
    
    def _cache_entity(self, entity: EntityType):
        """Add entity to cache"""
        if self.config.cache.enabled:
            self._cache[entity.id] = entity
            self._cache_timestamps[entity.id] = datetime.now()
    
    def _remove_from_cache(self, entity_id: IDType):
        """Remove entity from cache"""
        self._cache.pop(entity_id, None)
        self._cache_timestamps.pop(entity_id, None)
    
    async def _load_collection(self) -> Dict[str, Any]:
        """Load the entire collection from storage"""
        data = await self.storage_backend.read(self.collection_key)
        return data or {}
    
    async def _save_collection(self, data: Dict[str, Any]) -> bool:
        """Save the entire collection to storage"""
        return await self.storage_backend.write(self.collection_key, data)
    
    async def get_by_id(self, entity_id: IDType) -> Optional[EntityType]:
        """Retrieve an entity by its ID"""
        # Check cache first
        if self._is_cache_valid(entity_id):
            logger.debug(f"Cache hit for {self.entity_class.__name__}#{entity_id}")
            return self._cache[entity_id]
        
        # Load from storage
        collection_data = await self._load_collection()
        entity_key = str(entity_id)  # JSON keys are strings
        
        if entity_key not in collection_data:
            return None
        
        try:
            entity = self.entity_class.deserialize(collection_data[entity_key], id=entity_id)
            self._cache_entity(entity)
            return entity
        except Exception as e:
            logger.error(f"Failed to deserialize {self.entity_class.__name__}#{entity_id}: {e}")
            return None
    
    async def get_all(self) -> List[EntityType]:
        """Retrieve all entities of this type"""
        collection_data = await self._load_collection()
        entities = []
        
        for entity_id_str, entity_data in collection_data.items():
            try:
                # Convert string ID back to appropriate type
                entity_id = int(entity_id_str) if entity_id_str.isdigit() else entity_id_str
                entity = self.entity_class.deserialize(entity_data, id=entity_id)
                self._cache_entity(entity)
                entities.append(entity)
            except Exception as e:
                logger.warning(f"Failed to deserialize entity {entity_id_str}: {e}")
                continue
        
        return entities
    
    async def add(self, entity: EntityType) -> EntityType:
        """Add a new entity"""
        if not self._validate_entity(entity):
            raise ValidationException(f"Entity validation failed for {entity}")
        
        # Check if entity already exists
        if await self.exists(entity.id):
            raise EntityAlreadyExistsException(f"Entity {entity.id} already exists")
        
        # Load collection, add entity, save
        collection_data = await self._load_collection()
        collection_data[str(entity.id)] = entity.serialize()
        
        await self._save_collection(collection_data)
        self._cache_entity(entity)
        
        logger.info(f"Added {self.entity_class.__name__}#{entity.id}")
        return entity
    
    async def update(self, entity: EntityType) -> EntityType:
        """Update an existing entity"""
        if not self._validate_entity(entity):
            raise ValidationException(f"Entity validation failed for {entity}")
        
        if not await self.exists(entity.id):
            raise EntityNotFoundException(f"Entity {entity.id} not found")
        
        # Load collection, update entity, save
        collection_data = await self._load_collection()
        collection_data[str(entity.id)] = entity.serialize()
        
        await self._save_collection(collection_data)
        self._cache_entity(entity)
        
        logger.info(f"Updated {self.entity_class.__name__}#{entity.id}")
        return entity
    
    async def delete(self, entity_id: IDType) -> bool:
        """Delete an entity by ID"""
        collection_data = await self._load_collection()
        entity_key = str(entity_id)
        
        if entity_key not in collection_data:
            return False
        
        del collection_data[entity_key]
        await self._save_collection(collection_data)
        self._remove_from_cache(entity_id)
        
        logger.info(f"Deleted {self.entity_class.__name__}#{entity_id}")
        return True
    
    async def exists(self, entity_id: IDType) -> bool:
        """Check if an entity exists"""
        # Check cache first
        if self._is_cache_valid(entity_id):
            return True
        
        collection_data = await self._load_collection()
        return str(entity_id) in collection_data
    
    async def count(self) -> int:
        """Get the total count of entities"""
        collection_data = await self._load_collection()
        return len(collection_data)
    
    async def get_or_add(self, entity_id: IDType, factory: Callable[[], EntityType]) -> EntityType:
        """Get an entity or create it if it doesn't exist"""
        entity = await self.get_by_id(entity_id)
        if entity is None:
            entity = factory()
            await self.add(entity)
        return entity
    
    async def batch_update(self, entities: List[EntityType]) -> List[EntityType]:
        """Update multiple entities in a single operation"""
        collection_data = await self._load_collection()
        
        for entity in entities:
            if not self._validate_entity(entity):
                raise ValidationException(f"Entity validation failed for {entity}")
            collection_data[str(entity.id)] = entity.serialize()
            self._cache_entity(entity)
        
        await self._save_collection(collection_data)
        logger.info(f"Batch updated {len(entities)} {self.entity_class.__name__} entities")
        return entities