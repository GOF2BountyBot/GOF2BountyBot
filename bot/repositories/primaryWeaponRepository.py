from typing import Any, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from .snowflakeRepository import SnowflakeRepository
from ..entities.items.weapons.primaryWeapon import PrimaryWeapon
from ..lib.sql import SqlColumnExpression, SqlFilterExpression, randomRows

class PrimaryWeaponRepository(SnowflakeRepository[PrimaryWeapon]):
    def __init__(self, session: AsyncSession):
        super().__init__(PrimaryWeapon, session)


    async def filteredRandom(self, filter: SqlFilterExpression, withOnlyFields: Optional[Tuple[SqlColumnExpression[Any], ...]] = None) -> Optional[PrimaryWeapon]:
        """Get one random record. Returns `None` if no records exist.

        :return: A random stored record, or `None` if none exist
        :rtype: Optional[PrimaryWeapon]
        """
        query = randomRows(PrimaryWeapon).where(filter).limit(1)

        if withOnlyFields:
            query = query.with_only_columns(*withOnlyFields)

        result = await self.session.execute(query)
        row = result.first()

        return None if row is None else row.t[0]
    