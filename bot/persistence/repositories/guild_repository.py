from typing import Optional, Dict, Any
from bot.persistence.repositories.repository_base import BaseRepository

class GuildRepository(BaseRepository[Dict[str, Any]]):
    """
    Repository for managing Guild data.
    Currently works with raw dictionaries - we'll improve this in Phase 2!
    """
    
    def get_by_id(self, guild_id: str) -> Optional[Dict[str, Any]]:
        """
        Get guild data by ID.
        
        Args:
            guild_id: The Discord guild ID as a string
            
        Returns:
            Guild data dictionary if found, None otherwise
        """
        all_guilds = self._facade.get_guilds_db_raw()
        return all_guilds.get(guild_id)
    
    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all guilds.
        
        Returns:
            Dictionary mapping guild IDs to guild data dictionaries
        """
        return self._facade.get_guilds_db_raw()
    
    def save(self, guild_data: Dict[str, Any]) -> None:
        """
        Save guild data.
        Note: guild_data must contain an 'id' field!
        
        Args:
            guild_data: Dictionary containing guild information
        """
        if 'id' not in guild_data:
            raise ValueError("Guild data must contain an 'id' field")
            
        guild_id = str(guild_data['id'])
        all_guilds = self._facade.get_guilds_db_raw()
        all_guilds[guild_id] = guild_data
        self._facade.save_guilds_db_raw(all_guilds)
    
    def delete(self, guild_id: str) -> bool:
        """
        Delete a guild by ID.
        
        Args:
            guild_id: The Discord guild ID as a string
            
        Returns:
            True if guild was deleted, False if not found
        """
        all_guilds = self._facade.get_guilds_db_raw()
        
        if guild_id in all_guilds:
            del all_guilds[guild_id]
            self._facade.save_guilds_db_raw(all_guilds)
            return True
        
        return False
    
    def exists(self, guild_id: str) -> bool:
        """
        Check if a guild exists.
        
        Args:
            guild_id: The Discord guild ID as a string
            
        Returns:
            True if guild exists, False otherwise
        """
        all_guilds = self._facade.get_guilds_db_raw()
        return guild_id in all_guilds