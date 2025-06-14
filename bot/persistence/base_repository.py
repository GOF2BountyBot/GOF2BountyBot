"""
Abstract base repository interface for GOF2BountyBot.
Defines the contract that all repository implementations must follow.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum

class DataSource(Enum):
    """Enum to track data source for passive migration monitoring."""
    DATABASE = "database"
    JSON = "json"
    NONE = "none"

@dataclass
class RepositoryResult:
    """Standardized result object for all repository operations."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    source: DataSource = DataSource.NONE
    migrated: bool = False

class BaseRepository(ABC):
    """Abstract base class defining the repository interface."""
    
    def __init__(self, data_dir: str = "data", db_session_factory=None):
        self.data_dir = data_dir
        self.db_session_factory = db_session_factory
        self._db_available = db_session_factory is not None
    
    @abstractmethod
    async def get(self, entity_id: str) -> RepositoryResult:
        """Retrieve an entity by ID with passive migration."""
        pass
    
    @abstractmethod
    async def save(self, entity_id: str, data: Dict[str, Any]) -> RepositoryResult:
        """Save an entity with intelligent storage selection."""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: str) -> RepositoryResult:
        """Delete an entity from both storage backends."""
        pass
    
    @abstractmethod
    async def list_all(self) -> RepositoryResult:
        """List all entities from both storage backends."""
        pass
    
    @abstractmethod
    async def exists(self, entity_id: str) -> RepositoryResult:
        """Check if entity exists in either storage backend."""
        pass
    
    async def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status and statistics."""
        return {
            "db_available": self._db_available,
            "total_entities": 0,
            "migrated_entities": 0,
            "json_only_entities": 0
        }
