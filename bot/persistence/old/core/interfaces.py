from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, Dict, Any, Union
from datetime import datetime
import asyncio

T = TypeVar('T')
EntityType = TypeVar('EntityType')
IDType = TypeVar('IDType')

class IEntity(ABC):
    """Base interface for all entities that can be persisted"""
    
    @property
    @abstractmethod
    def id(self) -> Any:
        """Return the unique identifier for this entity"""
        pass
    
    @abstractmethod
    def serialize(self, **kwargs) -> Dict[str, Any]:
        """Serialize this entity to a dictionary"""
        pass
    
    @classmethod
    @abstractmethod
    def deserialize(cls, data: Dict[str, Any], **kwargs) -> 'IEntity':
        """Deserialize a dictionary to create an entity instance"""
        pass

class IRepository(Generic[EntityType, IDType], ABC):
    """Base repository interface for all data access operations"""
    
    @abstractmethod
    async def get_by_id(self, entity_id: IDType) -> Optional[EntityType]:
        """Retrieve an entity by its ID"""
        pass
    
    @abstractmethod
    async def get_all(self) -> List[EntityType]:
        """Retrieve all entities of this type"""
        pass
    
    @abstractmethod
    async def add(self, entity: EntityType) -> EntityType:
        """Add a new entity"""
        pass
    
    @abstractmethod
    async def update(self, entity: EntityType) -> EntityType:
        """Update an existing entity"""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: IDType) -> bool:
        """Delete an entity by ID"""
        pass
    
    @abstractmethod
    async def exists(self, entity_id: IDType) -> bool:
        """Check if an entity exists"""
        pass
    
    @abstractmethod
    async def count(self) -> int:
        """Get the total count of entities"""
        pass

class IS
