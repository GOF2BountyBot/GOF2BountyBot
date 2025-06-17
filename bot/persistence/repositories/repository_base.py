from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, Dict, Any
from bot.persistence.facade import PersistenceFacade

T = TypeVar('T')

class BaseRepository(ABC, Generic[T]):
    """
    Base class for all repositories.
    Provides common functionality for data access.
    """
    
    def __init__(self):
        self._facade = PersistenceFacade.get()
    
    @abstractmethod
    def get_by_id(self, id: str) -> Optional[T]:
        """Get a single item by its ID"""
        pass
    
    @abstractmethod
    def get_all(self) -> Dict[str, T]:
        """Get all items"""
        pass
    
    @abstractmethod  
    def save(self, item: T) -> None:
        """Save a single item"""
        pass
    
    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete an item by ID, returns True if deleted"""
        pass
