"""
Database configuration and session management for GOF2BountyBot.
Provides database-agnostic connection handling with SQLAlchemy.
"""
import os
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError
from contextlib import asynccontextmanager

from models import Base

class DatabaseConfig:
    """Database configuration management."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.engine = None
        self.session_factory = None
        self._initialized = False

    def get_connection_url(self) -> str:
        """Generate database connection URL from configuration."""
        db_type = self.config.get("type", "sqlite")

        if db_type == "sqlite":
            db_path = self.config.get("path", "data/bot.db")
            # Ensure directory exists
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            return f"sqlite+aiosqlite:///{db_path}"

        elif db_type == "postgresql":
            return URL.create(
                "postgresql+asyncpg",
                username=self.config.get("username"),
                password=self.config.get("password"),
                host=self.config.get("host", "localhost"),
                port=self.config.get("port", 5432),
                database=self.config.get("database")
            )

        elif db_type == "mysql":
            return URL.create(
                "mysql+aiomysql",
                username=self.config.get("username"),
                password=self.config.get("password"),
                host=self.config.get("host", "localhost"),
                port=self.config.get("port", 3306),
                database=self.config.get("database")
            )

        else:
            raise ValueError(f"Unsupported database type: {db_type}")

    async def initialize(self) -> bool:
        """Initialize database connection and create tables."""
        try:
            # Create engine with connection pooling
            connection_url = self.get_connection_url()

            engine_kwargs = {
                "echo": self.config.get("echo", False),
                "pool_pre_ping": True,
            }

            # Add connection pool settings for non-SQLite databases
            if not connection_url.startswith("sqlite"):
                engine_kwargs.update({
                    "pool_size": self.config.get("pool_size", 5),
                    "max_overflow": self.config.get("max_overflow", 10),
                    "pool_timeout": self.config.get("pool_timeout", 30),
                    "pool_recycle": self.config.get("pool_recycle", 3600),
                })

            self.engine = create_async_engine(connection_url, **engine_kwargs)

            # Create session factory
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            self._initialized = True
            print(f"Database initialized successfully with {self.config.get('type', 'sqlite')}")
            return True

        except SQLAlchemyError as e:
            print(f"Database initialization failed: {e}")
            self.engine = None
            self.session_factory = None
            self._initialized = False
            return False

    async def close(self):
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self.session_factory = None
            self._initialized = False

    @asynccontextmanager
    async def get_session(self):
        """Get database session with automatic cleanup."""
        if not self._initialized or not self.session_factory:
            raise RuntimeError("Database not initialized")

        async with self.session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    def is_available(self) -> bool:
        """Check if database is available and initialized."""
        return self._initialized and self.session_factory is not None

    async def health_check(self) -> Dict[str, Any]:
        """Perform database health check."""
        if not self.is_available():
            return {
                "status": "unavailable",
                "error": "Database not initialized"
            }

        try:
            async with self.get_session() as session:
                await session.execute("SELECT 1")
                return {
                    "status": "healthy",
                    "type": self.config.get("type", "unknown"),
                    "pool_size": getattr(self.engine.pool, 'size', None) if hasattr(self.engine, 'pool') else None,
                    "checked_out": getattr(self.engine.pool, 'checked_out', None) if hasattr(self.engine, 'pool') else None
                }
        except SQLAlchemyError as e:
            return {
                "status": "error",
                "error": str(e)
            }


class DatabaseManager:
    """Central database manager for the bot."""

    def __init__(self):
        self.config_manager: Optional[DatabaseConfig] = None

    async def initialize_from_config(self, config: Dict[str, Any]) -> bool:
        """Initialize database from configuration dictionary."""
        db_config = config.get("database", {})

        # If no database config or disabled, return False (JSON-only mode)
        if not db_config or not db_config.get("enabled", True):
            print("Database disabled or not configured - running in JSON-only mode")
            return False

        self.config_manager = DatabaseConfig(db_config)
        return await self.config_manager.initialize()

    def get_session_factory(self):
        """Get session factory for repository injection."""
        if self.config_manager and self.config_manager.is_available():
            return self.config_manager.session_factory
        return None

    async def close(self):
        """Close database connections."""
        if self.config_manager:
            await self.config_manager.close()
            self.config_manager = None

    def is_available(self) -> bool:
        """Check if database is available."""
        return (self.config_manager is not None and 
                self.config_manager.is_available())

    async def health_check(self) -> Dict[str, Any]:
        """Get database health status."""
        if not self.config_manager:
            return {"status": "not_configured"}

        return await self.config_manager.health_check()


# Convenience functions for common operations
async def create_database_manager(config: Dict[str, Any]) -> DatabaseManager:
    """Create and initialize database manager from configuration."""
    manager = DatabaseManager()
    await manager.initialize_from_config(config)
    return manager

def get_default_database_config() -> Dict[str, Any]:
    """Get default database configuration for development."""
    return {
        "database": {
            "enabled": True,
            "type": "sqlite",
            "path": "data/bot.db",
            "echo": False,
            "pool_size": 5,
            "max_overflow": 10,
            "pool_timeout": 30,
            "pool_recycle": 3600
        }
    }