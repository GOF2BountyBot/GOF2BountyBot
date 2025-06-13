from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional
import os

@dataclass
class StorageConfig:
    """Configuration for storage backend"""
    backend_type: str = "json"
    base_path: str = "data"
    backup_path: str = "backups"
    auto_backup: bool = True
    backup_interval_hours: int = 24
    compression: bool = False
    encryption: bool = False
    encryption_key: Optional[str] = None

@dataclass
class CacheConfig:
    """Configuration for caching layer"""
    enabled: bool = True
    ttl_seconds: int = 3600  # 1 hour
    max_size: int = 1000
    cleanup_interval_seconds: int = 300  # 5 minutes
    cache_statistics: bool = True

@dataclass
class SessionConfig:
    """Configuration for session management"""
    auto_commit: bool = False
    timeout_seconds: int = 300  # 5 minutes
    max_concurrent_sessions: int = 10
    enable_deadlock_detection: bool = True

@dataclass
class ValidationConfig:
    """Configuration for entity validation"""
    strict_validation: bool = True
    validate_on_save: bool = True
    validate_on_load: bool = False
    custom_validators: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PersistenceConfig:
    """Main configuration class for persistence layer"""
    storage: StorageConfig = field(default_factory=StorageConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    
    # Logging configuration
    log_level: str = "INFO"
    log_file: Optional[str] = "persistence.log"
    log_sql_queries: bool = False  # For future SQLAlchemy support
    
    # Performance configuration
    async_operations: bool = True
    thread_pool_size: int = 4
    batch_size: int = 100
    
    @classmethod
    def from_env(cls) -> 'PersistenceConfig':
        """Create configuration from environment variables"""
        config = cls()
        
        # Storage configuration
        if base_path := os.getenv('PERSISTENCE_BASE_PATH'):
            config.storage.base_path = base_path
        if backup_path := os.getenv('PERSISTENCE_BACKUP_PATH'):
            config.storage.backup_path = backup_path
        if auto_backup := os.getenv('PERSISTENCE_AUTO_BACKUP'):
            config.storage.auto_backup = auto_backup.lower() == 'true'
            
        # Cache configuration
        if cache_enabled := os.getenv('PERSISTENCE_CACHE_ENABLED'):
            config.cache.enabled = cache_enabled.lower() == 'true'
        if ttl := os.getenv('PERSISTENCE_CACHE_TTL'):
            config.cache.ttl_seconds = int(ttl)
            
        return config
    
    def create_directories(self):
        """Create necessary directories if they don't exist"""
        Path(self.storage.base_path).mkdir(parents=True, exist_ok=True)
        Path(self.storage.backup_path).mkdir(parents=True, exist_ok=True)
