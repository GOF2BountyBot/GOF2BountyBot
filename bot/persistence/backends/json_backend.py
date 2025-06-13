import json
import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import shutil
import fcntl
import tempfile
import logging

from bot.persistence.core.interfaces import IStorageBackend
from bot.persistence.core.exceptions import StorageException
from bot.persistence.config.settings import StorageConfig

logger = logging.getLogger(__name__)

class JsonStorageBackend(IStorageBackend):
    """JSON file-based storage backend with atomic operations"""
    
    def __init__(self, config: StorageConfig):
        self.config = config
        self.base_path = Path(config.base_path)
        self.backup_path = Path(config.backup_path)
        self._locks = {}  # File-level locks for thread safety
        
        # Create directories
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.backup_path.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, key: str) -> Path:
        """Get the file path for a given key"""
        return self.base_path / f"{key}.json"
    
    def _get_lock(self, key: str) -> asyncio.Lock:
        """Get or create a lock for the given key"""
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]
    
    async def read(self, key: str) -> Optional[Dict[str, Any]]:
        """Read data from JSON file with proper locking"""
        file_path = self._get_file_path(key)
        
        if not file_path.exists():
            return None
        
        lock = self._get_lock(key)
        async with lock:
            try:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    return json.loads(content)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to read {key}: {e}")
                raise StorageException(f"Failed to read {key}: {e}")
    
    async def write(self, key: str, data: Dict[str, Any]) -> bool:
        """Write data to JSON file atomically"""
        file_path = self._get_file_path(key)
        lock = self._get_lock(key)
        
        async with lock:
            try:
                # Write to temporary file first for atomic operation
                temp_path = file_path.with_suffix('.tmp')
                
                async with aiofiles.open(temp_path, 'w', encoding='utf-8') as f:
                    content = json.dumps(data, indent=2, ensure_ascii=False)
                    await f.write(content)
                    await f.flush()
                
                # Atomic move
                temp_path.replace(file_path)
                return True
                
            except (IOError, OSError) as e:
                logger.error(f"Failed to write {key}: {e}")
                # Clean up temp file if it exists
                if temp_path.exists():
                    temp_path.unlink(missing_ok=True)
                raise StorageException(f"Failed to write {key}: {e}")
    
    async def delete(self, key: str) -> bool:
        """Delete a JSON file"""
        file_path = self._get_file_path(key)
        lock = self._get_lock(key)
        
        async with lock:
            try:
                if file_path.exists():
                    file_path.unlink()
                    return True
                return False
            except OSError as e:
                logger.error(f"Failed to delete {key}: {e}")
                raise StorageException(f"Failed to delete {key}: {e}")
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists"""
        return self._get_file_path(key).exists()
    
    async def list_keys(self, prefix: str = "") -> List[str]:
        """List all keys with optional prefix"""
        keys = []
        pattern = f"{prefix}*.json" if prefix else "*.json"
        
        for file_path in self.base_path.glob(pattern):
            key = file_path.stem
            keys.append(key)
        
        return sorted(keys)
    
    async def backup(self, backup_path: str) -> bool:
        """Create a backup of all data"""
        try:
            backup_dir = Path(backup_path)
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"backup_{timestamp}.tar.gz"
            
            # Create compressed backup
            import tarfile
            with tarfile.open(backup_file, "w:gz") as tar:
                tar.add(self.base_path, arcname="data")
            
            logger.info(f"Backup created: {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            raise StorageException(f"Backup failed: {e}")
    
    async def restore(self, backup_path: str) -> bool:
        """Restore data from backup"""
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                raise StorageException(f"Backup file not found: {backup_path}")
            
            # Create temporary restore directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Extract backup
                import tarfile
                with tarfile.open(backup_file, "r:gz") as tar:
                    tar.extractall(temp_path)
                
                # Replace current data
                if self.base_path.exists():
                    shutil.rmtree(self.base_path)
                shutil.move(temp_path / "data", self.base_path)
            
            logger.info(f"Restore completed from: {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            raise StorageException(f"Restore failed: {e}")