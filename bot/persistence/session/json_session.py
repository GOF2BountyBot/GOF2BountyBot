import asyncio
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
import copy
import json

from bot.persistence.core.interfaces import ISession, IStorageBackend
from bot.persistence.core.exceptions import SessionException
from bot.persistence.config.settings import SessionConfig

logger = logging.getLogger(__name__)

class JsonSession(ISession):
    """Session implementation for JSON storage with transaction-like behavior"""
    
    def __init__(self, storage_backend: IStorageBackend, config: SessionConfig):
        self.storage_backend = storage_backend
        self.config = config
        
        self._is_active = False
        self._changes: Dict[str, Dict[str, Any]] = {}  # key -> data
        self._deletions: Set[str] = set()
        self._original_data: Dict[str, Dict[str, Any]] = {}  # For rollback
        self._start_time: Optional[datetime] = None
        self._lock = asyncio.Lock()
    
    @property
    def is_active(self) -> bool:
        return self._is_active
    
    async def begin(self) -> None:
        """Begin a new session"""
        async with self._lock:
            if self._is_active:
                raise SessionException("Session is already active")
            
            self._is_active = True
            self._start_time = datetime.now()
            self._changes.clear()
            self._deletions.clear()
            self._original_data.clear()
            
            logger.debug("Session started")
    
    async def commit(self) -> None:
        """Commit all changes in this session"""
        async with self._lock:
            if not self._is_active:
                raise SessionException("No active session to commit")
            
            try:
                # Check for timeout
                if self._start_time:
                    elapsed = datetime.now() - self._start_time
                    if elapsed.total_seconds() > self.config.timeout_seconds:
                        raise SessionException("Session timeout")
                
                # Apply deletions first
                for key in self._deletions:
                    await self.storage_backend.delete(key)
                
                # Apply changes
                for key, data in self._changes.items():
                    await self.storage_backend.write(key, data)
                
                logger.info(f"Session committed: {len(self._changes)} writes, {len(self._deletions)} deletions")
                
            except Exception as e:
                logger.error(f"Failed to commit session: {e}")
                raise SessionException(f"Commit failed: {e}")
            finally:
                await self._reset()
    
    async def rollback(self) -> None:
        """Rollback all changes in this session"""
        async with self._lock:
            if not self._is_active:
                raise SessionException("No active session to rollback")
            
            logger.info(f"Session rolled back: {len(self._changes)} changes discarded")
            await self._reset()
    
    async def close(self) -> None:
        """Close the session"""
        if self._is_active:
            if self.config.auto_commit:
                await self.commit()
            else:
                await self.rollback()
    
    async def _reset(self):
        """Reset session state"""
        self._is_active = False
        self._changes.clear()
        self._deletions.clear()
        self._original_data.clear()
        self._start_time = None
    
    async def read(self, key: str) -> Optional[Dict[str, Any]]:
        """Read data within session context"""
        if not self._is_active:
            return await self.storage_backend.read(key)
        
        # Check if we have changes for this key
        if key in self._changes:
            return copy.deepcopy(self._changes[key])
        
        # Check if key was deleted
        if key in self._deletions:
            return None
        
        # Read from storage and cache original data
        data = await self.storage_backend.read(key)
        if data is not None and key not in self._original_data:
            self._original_data[key] = copy.deepcopy(data)
        
        return data
    
    async def write(self, key: str, data: Dict[str, Any]) -> bool:
        """Write data within session context"""
        if not self._is_active:
            return await self.storage_backend.write(key, data)
        
        # Store original data for rollback if not already stored
        if key not in self._original_data:
            original = await self.storage_backend.read(key)
            if original is not None:
                self._original_data[key] = copy.deepcopy(original)
        
        # Store change in session
        self._changes[key] = copy.deepcopy(data)
        self._deletions.discard(key)  # Remove from deletions if present
        
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete data within session context"""
        if not self._is_active:
            return await self.storage_backend.delete(key)
        
        # Store original data for rollback if not already stored
        if key not in self._original_data:
            original = await self.storage_backend.read(key)
            if original is not None:
                self._original_data[key] = copy.deepcopy(original)
        
        # Mark for deletion
        self._deletions.add(key)
        self._changes.pop(key, None)  # Remove from changes if present
        
        return True

class SessionManager:
    """Manages multiple sessions and provides session pooling"""
    
    def __init__(self, storage_backend: IStorageBackend, config: SessionConfig):
        self.storage_backend = storage_backend
        self.config = config
        self._active_sessions: Dict[str, JsonSession] = {}
        self._session_counter = 0
        self._lock = asyncio.Lock()
    
    async def create_session(self, session_id: Optional[str] = None) -> JsonSession:
        """Create a new session"""
        async with self._lock:
            if len(self._active_sessions) >= self.config.max_concurrent_sessions:
                raise SessionException("Maximum concurrent sessions reached")
            
            if session_id is None:
                self._session_counter += 1
                session_id = f"session_{self._session_counter}"
            
            if session_id in self._active_sessions:
                raise SessionException(f"Session {session_id} already exists")
            
            session = JsonSession(self.storage_backend, self.config)
            self._active_sessions[session_id] = session
            
            return session
    
    async def close_session(self, session_id: str):
        """Close and remove a session"""
        async with self._lock:
            if session_id in self._active_sessions:
                session = self._active_sessions[session_id]
                await session.close()
                del self._active_sessions[session_id]
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        now = datetime.now()
        expired_sessions = []
        
        for session_id, session in self._active_sessions.items():
            if (session._start_time and 
                (now - session._start_time).total_seconds() > self.config.timeout_seconds):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            logger.warning(f"Cleaning up expired session: {session_id}")
            await self.close_session(session_id)