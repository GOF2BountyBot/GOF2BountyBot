from typing import List, Optional
import logging

from bot.persistence.repositories.base_repository import BaseRepository
from bot.persistence.core.interfaces import IStorageBackend
from bot.persistence.config.settings import PersistenceConfig

logger = logging.getLogger(__name__)

class UserRepository(BaseRepository):
    """Repository for BasedUser entities"""
    
    def __init__(self, storage_backend: IStorageBackend, config: PersistenceConfig):
        super().__init__(
            entity_class=None,  # Will be set during integration
            storage_backend=storage_backend,
            config=config,
            collection_key="users"
        )
        
        # Add user-specific validators
        self.add_validator(self._validate_user_credits)
        self.add_validator(self._validate_user_id)
    
    def _validate_user_credits(self, user) -> bool:
        """Validate user credits are non-negative"""
        return hasattr(user, 'credits') and user.credits >= 0
    
    def _validate_user_id(self, user) -> bool:
        """Validate user ID is valid"""
        return hasattr(user, 'id') and user.id > 0
    
    async def get_by_home_guild(self, guild_id: int) -> List:
        """Get all users with a specific home guild"""
        all_users = await self.get_all()
        return [user for user in all_users 
                if hasattr(user, 'homeGuildID') and user.homeGuildID == guild_id]
    
    async def get_top_by_credits(self, limit: int = 10) -> List:
        """Get top users by credits"""
        all_users = await self.get_all()
        sorted_users = sorted(all_users, 
                            key=lambda u: getattr(u, 'credits', 0), 
                            reverse=True)
        return sorted_users[:limit]
    
    async def get_by_credit_range(self, min_credits: int, max_credits: int) -> List:
        """Get users within a credit range"""
        all_users = await self.get_all()
        return [user for user in all_users 
                if min_credits <= getattr(user, 'credits', 0) <= max_credits]

### persistence/repositories/guild_repository.py

class GuildRepository(BaseRepository):
    """Repository for BasedGuild entities"""
    
    def __init__(self, storage_backend: IStorageBackend, config: PersistenceConfig):
        super().__init__(
            entity_class=None,  # Will be set during integration
            storage_backend=storage_backend,
            config=config,
            collection_key="guilds"
        )
        
        # Add guild-specific validators
        self.add_validator(self._validate_guild_id)
    
    def _validate_guild_id(self, guild) -> bool:
        """Validate guild ID is valid"""
        return hasattr(guild, 'id') and guild.id > 0
    
    async def get_active_guilds(self) -> List:
        """Get all guilds that are not disabled"""
        all_guilds = await self.get_all()
        return [guild for guild in all_guilds 
                if not getattr(guild, 'bountiesDisabled', True)]
    
    async def get_guilds_with_bounties(self) -> List:
        """Get guilds that have bounties enabled"""
        all_guilds = await self.get_all()
        return [guild for guild in all_guilds 
                if not getattr(guild, 'bountiesDisabled', True)]