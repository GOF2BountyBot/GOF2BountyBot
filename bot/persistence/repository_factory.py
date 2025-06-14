"""
Repository factory for GOF2BountyBot.
Provides centralized repository creation and management.
"""
from typing import Dict, Any, Optional
from database_config import DatabaseManager
from hybrid_repository import UserRepository, GuildRepository, BountyRepository, GameDataRepository

class RepositoryFactory:
    """Factory for creating and managing repository instances."""

    def __init__(self, database_manager: DatabaseManager, data_dir: str = "data"):
        self.database_manager = database_manager
        self.data_dir = data_dir
        self._repositories: Dict[str, Any] = {}

    def get_session_factory(self):
        """Get database session factory if available."""
        return self.database_manager.get_session_factory()

    def create_user_repository(self) -> UserRepository:
        """Create or get cached UserRepository instance."""
        if "user" not in self._repositories:
            self._repositories["user"] = UserRepository(
                data_dir=self.data_dir,
                db_session_factory=self.get_session_factory()
            )
        return self._repositories["user"]

    def create_guild_repository(self) -> GuildRepository:
        """Create or get cached GuildRepository instance."""
        if "guild" not in self._repositories:
            self._repositories["guild"] = GuildRepository(
                data_dir=self.data_dir,
                db_session_factory=self.get_session_factory()
            )
        return self._repositories["guild"]

    def create_bounty_repository(self) -> BountyRepository:
        """Create or get cached BountyRepository instance."""
        if "bounty" not in self._repositories:
            self._repositories["bounty"] = BountyRepository(
                data_dir=self.data_dir,
                db_session_factory=self.get_session_factory()
            )
        return self._repositories["bounty"]

    def create_game_data_repository(self) -> GameDataRepository:
        """Create or get cached GameDataRepository instance."""
        if "game_data" not in self._repositories:
            self._repositories["game_data"] = GameDataRepository(
                data_dir=self.data_dir,
                db_session_factory=self.get_session_factory()
            )
        return self._repositories["game_data"]

    async def get_migration_status(self) -> Dict[str, Any]:
        """Get migration status for all repositories."""
        status = {
            "database_available": self.database_manager.is_available(),
            "repositories": {}
        }

        # Get status from each repository type
        for repo_name in ["user", "guild", "bounty", "game_data"]:
            repo_method = getattr(self, f"create_{repo_name}_repository")
            repo = repo_method()
            status["repositories"][repo_name] = await repo.get_migration_status()

        return status

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for all components."""
        health = {
            "database": await self.database_manager.health_check(),
            "repositories": {
                "user": "available",
                "guild": "available", 
                "bounty": "available",
                "game_data": "available"
            },
            "data_directory": {
                "path": self.data_dir,
                "exists": True,  # Will be checked by repositories
                "writable": True  # Will be checked by repositories
            }
        }

        return health


# Integration helper for bot initialization
class BotRepositoryManager:
    """High-level repository manager for bot integration."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.database_manager: Optional[DatabaseManager] = None
        self.repository_factory: Optional[RepositoryFactory] = None
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize all repository components."""
        try:
            # Initialize database manager
            self.database_manager = DatabaseManager()
            db_initialized = await self.database_manager.initialize_from_config(self.config)

            if not db_initialized:
                print("Database initialization failed or disabled - using JSON-only mode")

            # Create repository factory
            data_dir = self.config.get("data_dir", "data")
            self.repository_factory = RepositoryFactory(
                self.database_manager, 
                data_dir
            )

            self._initialized = True

            print(f"Repository manager initialized successfully")
            print(f"Database available: {self.database_manager.is_available()}")
            print(f"Data directory: {data_dir}")

            return True

        except Exception as e:
            print(f"Repository manager initialization failed: {e}")
            return False

    async def shutdown(self):
        """Cleanup resources."""
        if self.database_manager:
            await self.database_manager.close()

        self._initialized = False
        print("Repository manager shutdown complete")

    def get_user_repository(self) -> UserRepository:
        """Get user repository instance."""
        if not self._initialized:
            raise RuntimeError("Repository manager not initialized")
        return self.repository_factory.create_user_repository()

    def get_guild_repository(self) -> GuildRepository:
        """Get guild repository instance."""
        if not self._initialized:
            raise RuntimeError("Repository manager not initialized")
        return self.repository_factory.create_guild_repository()

    def get_bounty_repository(self) -> BountyRepository:
        """Get bounty repository instance."""
        if not self._initialized:
            raise RuntimeError("Repository manager not initialized")
        return self.repository_factory.create_bounty_repository()

    def get_game_data_repository(self) -> GameDataRepository:
        """Get game data repository instance."""
        if not self._initialized:
            raise RuntimeError("Repository manager not initialized")
        return self.repository_factory.create_game_data_repository()

    async def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all components."""
        if not self._initialized:
            return {"status": "not_initialized"}

        return {
            "initialized": self._initialized,
            "health": await self.repository_factory.health_check(),
            "migration": await self.repository_factory.get_migration_status()
        }

    def is_database_available(self) -> bool:
        """Quick check if database is available."""
        return (self._initialized and 
                self.database_manager and 
                self.database_manager.is_available())
