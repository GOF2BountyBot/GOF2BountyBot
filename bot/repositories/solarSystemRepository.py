from typing import Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from bot.lib.sql import SqlColumnExpression, randomRows

from .snowflakeRepository import SnowflakeRepository
from ..entities.bounties.solarSystem import AnySolarSystem

class SolarSystemRepository(SnowflakeRepository[AnySolarSystem]):
    def __init__(self, session: AsyncSession):
        super().__init__(AnySolarSystem, session)


    async def getRandom(self, withOnlyFields: Optional[Tuple[SqlColumnExpression[Any], ...]] = None, withJumpGate: Optional[bool] = None) -> Optional[AnySolarSystem]:
        """Get one random system. Returns `None` if no systems exist.

        :param Optional[bool] withJumpGate: `True`/`False`: the system must/must not have a jump gate. `None`: No filter (default `None`)
        :return: A random stored system, or `None` if none exist
        :rtype: Optional[AnySolarSystem]
        """
        query = randomRows(AnySolarSystem).limit(1)

        if withOnlyFields:
            query = query.with_only_columns(*withOnlyFields)

        result = await self.session.execute(query)
        row = result.first()

        return None if row is None else row.t[0]
