"""
Integration adapter for GOF2BountyBot existing JSON storage system
This provides a bridge between the existing code and the new persistence layer
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Type
from pathlib import Path

from bot.persistence.backends.json_backend import JsonStorageBackend
from bot.persistence.repositories.user_repository import UserRepository
from bot.persistence.repositories.guild_repository import GuildRepository
from bot.persistence.session.json_session import SessionManager
from bot.persistence.config.settings import PersistenceConfig
from bot.persistence.core.exceptions import PersistenceException

# Import existing bot classes (these would be actual imports in implementation)
# from bot.users.basedUser import BasedUser
# from bot.databases.userDB import UserDB
# from bot.guilds.basedGuild import BasedGuild
# from bot.databases.guildDB import GuildDB

logger = logging.getLogger(__name__)

class BotPersistenceAdapter:
    """
    Adapter that provides a bridge between the existing bot code and the new persistence layer.
    This allows gradual migration without breaking existing functionality.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        # Load configuration
        if config_path:
            self.config = PersistenceConfig.from_file(config_path)
        else:
            self.config = PersistenceConfig.from_env()
        
        # Initialize storage backend
        self.storage_backend = JsonStorageBackend(self.config.storage)
        
        # Initialize session manager
        self.session_manager = SessionManager(self.storage_backend, self.config.session)
        
        # Initialize repositories
        self.user_repository = None
        self.guild_repository = None
        
        # Legacy compatibility layer
        self._legacy_adapters = {}
        
        logger.info("BotPersistenceAdapter initialized")
    
    async def initialize(self):
        """Initialize the persistence layer and migrate existing data if needed"""
        try:
            # Create directories
            self.config.create_directories()
            
            # Initialize repositories after importing entity classes
            await self._initialize_repositories()
            
            # Migrate existing data if needed
            await self._migrate_existing_data()
            
            logger.info("Persistence layer initialization complete")
            
        except Exception as e:
            logger.error(f"Failed to initialize persistence layer: {e}")
            raise PersistenceException(f"Initialization failed: {e}")
    
    async def _initialize_repositories(self):
        """Initialize repositories with proper entity classes"""
        # These would use the actual imported classes
        # self.user_repository = UserRepository(self.storage_backend, self.config)
        # self.user_repository.entity_class = BasedUser
        
        # self.guild_repository = GuildRepository(self.storage_backend, self.config)
        # self.guild_repository.entity_class = BasedGuild
        
        logger.info("Repositories initialized")
    
    async def _migrate_existing_data(self):
        """Migrate existing JSON files to the new persistence layer if needed"""
        # Check if legacy files exist
        legacy_paths = {
            'users': 'data/users.json',
            'guilds': 'data/guilds.json',
            'reaction_menus': 'data/reactionMenus.json'
        }
        
        for entity_type, legacy_path in legacy_paths.items():
            if Path(legacy_path).exists():
                logger.info(f"Found legacy {entity_type} data, migrating...")
                await self._migrate_entity_data(entity_type, legacy_path)
    
    async def _migrate_entity_data(self, entity_type: str, legacy_path: str):
        """Migrate a specific entity type from legacy format"""
        try:
            # Read legacy data
            import json
            with open(legacy_path, 'r') as f:
                legacy_data = json.load(f)
            
            # Write to new storage backend
            await self.storage_backend.write(entity_type, legacy_data)
            
            # Create backup of legacy file
            backup_path = f"{legacy_path}.backup"
            Path(legacy_path).rename(backup_path)
            
            logger.info(f"Migrated {entity_type} data from {legacy_path}")
            
        except Exception as e:
            logger.error(f"Failed to migrate {entity_type} data: {e}")
            raise

class LegacyDatabaseAdapter:
    """
    Adapter that makes repositories look like the existing UserDB/GuildDB classes
    This allows existing code to work without changes during migration
    """
    
    def __init__(self, repository, legacy_class_name: str):
        self.repository = repository
        self.legacy_class_name = legacy_class_name
        
        # Cache for backwards compatibility
        self._entities_cache = {}
    
    # UserDB compatibility methods
    def idExists(self, user_id: int) -> bool:
        """Legacy compatibility for UserDB.idExists"""
        return asyncio.run(self.repository.exists(user_id))
    
    def getUser(self, user_id: int):
        """Legacy compatibility for UserDB.getUser"""
        return asyncio.run(self.repository.get_by_id(user_id))
    
    def addID(self, user_id: int):
        """Legacy compatibility for UserDB.addID"""
        # This would create a new user with default values
        # Implementation depends on the actual BasedUser constructor
        pass
    
    def getOrAddID(self, user_id: int):
        """Legacy compatibility for UserDB.getOrAddID"""
        user = self.getUser(user_id)
        if user is None:
            user = self.addID(user_id)
        return user
    
    def serialize(self, **kwargs) -> Dict[str, Any]:
        """Legacy compatibility for database serialization"""
        all_entities = asyncio.run(self.repository.get_all())
        data = {}
        for entity in all_entities:
            data[str(entity.id)] = entity.serialize(**kwargs)
        return data
    
    @property
    def users(self) -> Dict[int, Any]:
        """Legacy compatibility for direct access to users dict"""
        if not self._entities_cache:
            all_entities = asyncio.run(self.repository.get_all())
            self._entities_cache = {entity.id: entity for entity in all_entities}
        return self._entities_cache

### persistence/integration/service_layer.py

class UserService:
    """Service layer for user operations with business logic"""
    
    def __init__(self, user_repository: UserRepository, session_manager: SessionManager):
        self.user_repository = user_repository
        self.session_manager = session_manager
    
    async def create_user(self, user_id: int, **kwargs):
        """Create a new user with validation and business rules"""
        session = await self.session_manager.create_session()
        try:
            await session.begin()
            
            # Check if user already exists
            if await self.user_repository.exists(user_id):
                raise ValueError(f"User {user_id} already exists")
            
            # Create user with default values (would use actual BasedUser)
            # user = BasedUser(user_id, **kwargs)
            # await self.user_repository.add(user)
            
            await session.commit()
            return user
            
        except Exception as e:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    async def transfer_credits(self, from_user_id: int, to_user_id: int, amount: int):
        """Transfer credits between users with transaction safety"""
        session = await self.session_manager.create_session()
        try:
            await session.begin()
            
            from_user = await self.user_repository.get_by_id(from_user_id)
            to_user = await self.user_repository.get_by_id(to_user_id)
            
            if not from_user or not to_user:
                raise ValueError("One or both users not found")
            
            if from_user.credits < amount:
                raise ValueError("Insufficient credits")
            
            # Perform transfer
            from_user.credits -= amount
            to_user.credits += amount
            
            # Update both users
            await self.user_repository.update(from_user)
            await self.user_repository.update(to_user)
            
            await session.commit()
            
        except Exception as e:
            await session.rollback()
            raise
        finally:
            await session.close()

class GuildService:
    """Service layer for guild operations"""
    
    def __init__(self, guild_repository: GuildRepository, session_manager: SessionManager):
        self.guild_repository = guild_repository
        self.session_manager = session_manager
    
    async def create_guild(self, guild_id: int, **kwargs):
        """Create a new guild with default settings"""
        session = await self.session_manager.create_session()
        try:
            await session.begin()
            
            if await self.guild_repository.exists(guild_id):
                raise ValueError(f"Guild {guild_id} already exists")
            
            # Create guild with defaults (would use actual BasedGuild)
            # guild = BasedGuild(guild_id, **kwargs)
            # await self.guild_repository.add(guild)
            
            await session.commit()
            return guild
            
        except Exception as e:
            await session.rollback()
            raise
        finally:
            await session.close()