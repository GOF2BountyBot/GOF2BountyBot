"""
Hybrid repository implementation with passive migration.
Handles automatic migration from JSON to database storage.
"""
import os
import json
import asyncio
from typing import Dict, Any, Optional, List, Type
from pathlib import Path
import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError

from base_repository import BaseRepository, RepositoryResult, DataSource
from models import Base, User, Guild, Bounty, GameData

class HybridRepository(BaseRepository):
    """Base hybrid repository with passive migration capabilities."""

    def __init__(self, entity_class: Type[Base], json_filename: str, 
                 data_dir: str = "data", db_session_factory=None):
        super().__init__(data_dir, db_session_factory)
        self.entity_class = entity_class
        self.json_filename = json_filename
        self.json_path = Path(data_dir) / json_filename

    async def get(self, entity_id: str) -> RepositoryResult:
        """Retrieve entity with database-first, JSON-fallback strategy."""
        # First, try database
        if self._db_available:
            try:
                async with self.db_session_factory() as session:
                    result = await session.execute(
                        select(self.entity_class).where(self.entity_class.id == entity_id)
                    )
                    entity = result.scalar_one_or_none()

                    if entity:
                        return RepositoryResult(
                            success=True,
                            data=entity.to_dict(),
                            source=DataSource.DATABASE
                        )
            except SQLAlchemyError as e:
                # Database error, fall through to JSON
                print(f"Database error in get({entity_id}): {e}")

        # Fallback to JSON
        json_data = await self._load_json_data()
        if entity_id in json_data:
            entity_dict = json_data[entity_id]

            # Attempt passive migration to database
            migration_success = await self._migrate_entity_to_db(entity_id, entity_dict)

            return RepositoryResult(
                success=True,
                data=entity_dict,
                source=DataSource.JSON,
                migrated=migration_success
            )

        # Entity not found in either storage
        return RepositoryResult(
            success=False,
            error=f"Entity {entity_id} not found"
        )

    async def save(self, entity_id: str, data: Dict[str, Any]) -> RepositoryResult:
        """Save entity with database-first, JSON-fallback strategy."""
        # Ensure ID is set in data
        data["id"] = entity_id

        # Try database first
        if self._db_available:
            try:
                async with self.db_session_factory() as session:
                    # Check if entity exists
                    result = await session.execute(
                        select(self.entity_class).where(self.entity_class.id == entity_id)
                    )
                    existing_entity = result.scalar_one_or_none()

                    if existing_entity:
                        # Update existing entity
                        entity = self.entity_class.from_dict(data)
                        for key, value in entity.__dict__.items():
                            if not key.startswith('_') and key != 'id':
                                setattr(existing_entity, key, value)
                    else:
                        # Create new entity
                        entity = self.entity_class.from_dict(data)
                        session.add(entity)

                    await session.commit()

                    # Remove from JSON if migration successful
                    await self._remove_from_json(entity_id)

                    return RepositoryResult(
                        success=True,
                        data=data,
                        source=DataSource.DATABASE
                    )

            except SQLAlchemyError as e:
                print(f"Database error in save({entity_id}): {e}")
                # Fall through to JSON storage

        # Fallback to JSON storage
        success = await self._save_to_json(entity_id, data)
        return RepositoryResult(
            success=success,
            data=data if success else None,
            source=DataSource.JSON,
            error=None if success else "Failed to save to JSON"
        )

    async def delete(self, entity_id: str) -> RepositoryResult:
        """Delete entity from both storage backends."""
        db_deleted = False
        json_deleted = False

        # Delete from database
        if self._db_available:
            try:
                async with self.db_session_factory() as session:
                    await session.execute(
                        delete(self.entity_class).where(self.entity_class.id == entity_id)
                    )
                    await session.commit()
                    db_deleted = True
            except SQLAlchemyError as e:
                print(f"Database error in delete({entity_id}): {e}")

        # Delete from JSON
        json_deleted = await self._remove_from_json(entity_id)

        success = db_deleted or json_deleted
        return RepositoryResult(
            success=success,
            error=None if success else f"Entity {entity_id} not found in any storage"
        )

    async def list_all(self) -> RepositoryResult:
        """List all entities from both storage backends."""
        entities = {}

        # Get from database first
        if self._db_available:
            try:
                async with self.db_session_factory() as session:
                    result = await session.execute(select(self.entity_class))
                    db_entities = result.scalars().all()

                    for entity in db_entities:
                        entities[entity.id] = entity.to_dict()
            except SQLAlchemyError as e:
                print(f"Database error in list_all(): {e}")

        # Get from JSON (exclude already loaded from DB)
        json_data = await self._load_json_data()
        for entity_id, entity_data in json_data.items():
            if entity_id not in entities:
                entities[entity_id] = entity_data

        return RepositoryResult(
            success=True,
            data=list(entities.values()),
            source=DataSource.DATABASE if entities else DataSource.JSON
        )

    async def exists(self, entity_id: str) -> RepositoryResult:
        """Check if entity exists in either storage backend."""
        # Check database first
        if self._db_available:
            try:
                async with self.db_session_factory() as session:
                    result = await session.execute(
                        select(self.entity_class.id).where(self.entity_class.id == entity_id)
                    )
                    if result.scalar_one_or_none():
                        return RepositoryResult(
                            success=True,
                            data=True,
                            source=DataSource.DATABASE
                        )
            except SQLAlchemyError as e:
                print(f"Database error in exists({entity_id}): {e}")

        # Check JSON
        json_data = await self._load_json_data()
        exists_in_json = entity_id in json_data

        return RepositoryResult(
            success=True,
            data=exists_in_json,
            source=DataSource.JSON if exists_in_json else DataSource.NONE
        )

    async def get_migration_status(self) -> Dict[str, Any]:
        """Get detailed migration status."""
        status = await super().get_migration_status()

        # Count entities in each storage
        db_count = 0
        json_count = 0

        if self._db_available:
            try:
                async with self.db_session_factory() as session:
                    result = await session.execute(select(self.entity_class.id))
                    db_count = len(result.scalars().all())
            except SQLAlchemyError:
                pass

        json_data = await self._load_json_data()
        json_count = len(json_data)

        status.update({
            "entity_type": self.entity_class.__name__,
            "total_entities": db_count + json_count,
            "migrated_entities": db_count,
            "json_only_entities": json_count
        })

        return status

    async def _load_json_data(self) -> Dict[str, Any]:
        """Load data from JSON file."""
        if not self.json_path.exists():
            return {}

        try:
            async with aiofiles.open(self.json_path, 'r') as f:
                content = await f.read()
                return json.loads(content) if content.strip() else {}
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading JSON from {self.json_path}: {e}")
            return {}

    async def _save_to_json(self, entity_id: str, data: Dict[str, Any]) -> bool:
        """Save entity data to JSON file."""
        try:
            # Ensure directory exists
            self.json_path.parent.mkdir(parents=True, exist_ok=True)

            # Load existing data
            json_data = await self._load_json_data()

            # Update with new data
            json_data[entity_id] = data

            # Save back to file
            async with aiofiles.open(self.json_path, 'w') as f:
                await f.write(json.dumps(json_data, indent=2))

            return True
        except IOError as e:
            print(f"Error saving to JSON {self.json_path}: {e}")
            return False

    async def _remove_from_json(self, entity_id: str) -> bool:
        """Remove entity from JSON file."""
        try:
            json_data = await self._load_json_data()

            if entity_id in json_data:
                del json_data[entity_id]

                async with aiofiles.open(self.json_path, 'w') as f:
                    await f.write(json.dumps(json_data, indent=2))

                return True
            return False
        except IOError as e:
            print(f"Error removing from JSON {self.json_path}: {e}")
            return False

    async def _migrate_entity_to_db(self, entity_id: str, entity_data: Dict[str, Any]) -> bool:
        """Attempt to migrate a single entity from JSON to database."""
        if not self._db_available:
            return False

        try:
            async with self.db_session_factory() as session:
                # Check if already exists in database
                result = await session.execute(
                    select(self.entity_class).where(self.entity_class.id == entity_id)
                )
                if result.scalar_one_or_none():
                    return True  # Already migrated

                # Create new entity and add to database
                entity = self.entity_class.from_dict(entity_data)
                session.add(entity)
                await session.commit()

                # Remove from JSON after successful migration
                await self._remove_from_json(entity_id)

                print(f"Successfully migrated {self.entity_class.__name__} {entity_id} to database")
                return True

        except SQLAlchemyError as e:
            print(f"Failed to migrate {entity_id} to database: {e}")
            return False


# Specific repository implementations
class UserRepository(HybridRepository):
    """Repository for User entities."""

    def __init__(self, data_dir: str = "data", db_session_factory=None):
        super().__init__(User, "users.json", data_dir, db_session_factory)

    async def get_user_credits(self, user_id: str) -> int:
        """Get user credits with default fallback."""
        result = await self.get(user_id)
        if result.success and result.data:
            return result.data.get("credits", 0)
        return 0

    async def update_user_credits(self, user_id: str, amount: int) -> RepositoryResult:
        """Update user credits by amount."""
        result = await self.get(user_id)

        if result.success and result.data:
            user_data = result.data
        else:
            # Create new user
            user_data = {
                "id": user_id,
                "username": None,
                "credits": 0,
                "reputation": 0,
                "inventory": {},
                "settings": {}
            }

        user_data["credits"] += amount
        return await self.save(user_id, user_data)


class GuildRepository(HybridRepository):
    """Repository for Guild entities."""

    def __init__(self, data_dir: str = "data", db_session_factory=None):
        super().__init__(Guild, "guilds.json", data_dir, db_session_factory)

    async def get_guild_prefix(self, guild_id: str) -> str:
        """Get guild command prefix with default fallback."""
        result = await self.get(guild_id)
        if result.success and result.data:
            return result.data.get("prefix", "!")
        return "!"


class BountyRepository(HybridRepository):
    """Repository for Bounty entities."""

    def __init__(self, data_dir: str = "data", db_session_factory=None):
        super().__init__(Bounty, "bounties.json", data_dir, db_session_factory)

    async def get_open_bounties(self, guild_id: str) -> RepositoryResult:
        """Get all open bounties for a guild."""
        all_bounties_result = await self.list_all()

        if not all_bounties_result.success:
            return all_bounties_result

        open_bounties = [
            bounty for bounty in all_bounties_result.data
            if bounty.get("guild_id") == guild_id and bounty.get("status") == "open"
        ]

        return RepositoryResult(
            success=True,
            data=open_bounties,
            source=all_bounties_result.source
        )


class GameDataRepository(HybridRepository):
    """Repository for Game Data entities."""

    def __init__(self, data_dir: str = "data", db_session_factory=None):
        super().__init__(GameData, "game_data.json", data_dir, db_session_factory)

    async def get_by_category(self, category: str) -> RepositoryResult:
        """Get all game data items by category."""
        all_data_result = await self.list_all()

        if not all_data_result.success:
            return all_data_result

        category_items = [
            item for item in all_data_result.data
            if item.get("category") == category
        ]

        return RepositoryResult(
            success=True,
            data=category_items,
            source=all_data_result.source
        )
