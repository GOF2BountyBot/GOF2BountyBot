from typing import Optional, Dict
from bot.persistence.repositories.repository_base import BaseRepository
from bot.users.basedUser import BasedUser

class UserRepository(BaseRepository[BasedUser]):
    """
    Repository for managing BasedUser objects.
    Handles all user data access operations.
    """
    
    def __init__(self, users: dict[str, dict] | None = None):
        self._data = users or {}

    @property
    def users(self) -> dict[str, dict]:
        return self._data


    def get_by_id(self, user_id: str) -> Optional[BasedUser]:
        """
        Get a user by their Discord ID.
        
        Args:
            user_id: The Discord user ID as a string
            
        Returns:
            BasedUser object if found, None otherwise
        """
        all_users = self._facade.get_users_db_raw()
        
        if user_id not in all_users:
            return None
            
        user_data = all_users[user_id]
        return BasedUser.deserialize(user_data, id=int(user_id))
    
    def get_all(self) -> Dict[str, BasedUser]:
        """
        Get all users.
        
        Returns:
            Dictionary mapping user IDs to BasedUser objects
        """
        raw_users = self._facade.get_users_db_raw()
        users = {}
        
        for user_id, user_data in raw_users.items():
            users[user_id] = BasedUser.deserialize(user_data, id=int(user_id))
            
        return users
    
    def save(self, user: BasedUser) -> None:
        """
        Save a user to storage.
        
        Args:
            user: The BasedUser object to save
        """
        all_users = self._facade.get_users_db_raw()
        all_users[str(user.id)] = user.serialize()
        self._facade.save_users_db_raw(all_users)
    
    def delete(self, user_id: str) -> bool:
        """
        Delete a user by ID.
        
        Args:
            user_id: The Discord user ID as a string
            
        Returns:
            True if user was deleted, False if not found
        """
        all_users = self._facade.get_users_db_raw()
        
        if user_id in all_users:
            del all_users[user_id]
            self._facade.save_users_db_raw(all_users)
            return True
        
        return False
    
    def exists(self, user_id: str) -> bool:
        """
        Check if a user exists.
        
        Args:
            user_id: The Discord user ID as a string
            
        Returns:
            True if user exists, False otherwise
        """
        all_users = self._facade.get_users_db_raw()
        return user_id in all_users
