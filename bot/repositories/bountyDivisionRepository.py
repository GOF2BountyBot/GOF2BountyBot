from typing import Any, Collection, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from .snowflakeRepository import SnowflakeRepository
from ..entities.bounties.bountyDivision import BountyDivision, AnyBountyDivision
from ..cfg import cfg
from ..lib.sql import SqlColumnExpression

class BountyDivisionRepository(SnowflakeRepository["BountyDivision[Any]"]):
    def __init__(self, session: AsyncSession):
        super().__init__(BountyDivision[Any], session)

    
    async def getForGuild(self, guildId: int, withOnlyFields: Optional[Tuple[SqlColumnExpression[Any], ...]] = None) -> Collection[AnyBountyDivision]:
        """Get all bounty divisions associated with the given guild. Returns an empty array if the guild does not exist.

        :param int recordId: integer ID for the :class:`BasedGuild` whose divisions to get
        :return: The stored divisions
        :rtype: Optional[TRecord]
        """
        query = select(AnyBountyDivision).where(AnyBountyDivision.id == guildId)
        
        if withOnlyFields:
            query = query.with_only_columns(*withOnlyFields)

        result = await self.session.execute(query)
        row = result.one_or_none()
        return None if row is None else row.t[0]


    async def divisionForLevel(self, guildId: int, tl: int, withOnlyFields: Optional[Tuple[SqlColumnExpression[Any], ...]] = None) -> BountyDivision:
        """Get the stored BountyDivision which handles bounties of the given level.

        :param int tl: The techlevel whose division to find
        :return: The BountyDivison responsible for bounties of the given level
        :rtype: BountyDivision
        :raise KeyError: When no division is found for bounties of the given level
        """
        query = select(BountyDivision[Any]).where(and_(
            BountyDivision.guildId == guildId,
            BountyDivision.minLevel <= tl,
            BountyDivision.maxLevel >= tl
        ))
        
        if withOnlyFields:
            query = query.with_only_columns(*withOnlyFields)

        result = await self.session.execute(query)
        row = result.one_or_none()
        if row is None:
            raise KeyError(f"No BountyDivision is registered for bounties of TL {tl}")
        
        return row.t[0]


    async def divisionForName(self, guildId: int, name: str) -> BountyDivision:
        """Get the stored BountyDivision for the given division name, as specified in cfg.bountyDivisionNames.

        :param str name: The name of the division to get
        :return: The BountyDivison of the given name
        :rtype: BountyDivision
        :raise KeyError: When no division is found for the given name
        """
        try:
            divID = cfg.bountyDivisionNames.index(name)
        except ValueError:
            raise KeyError(f"No BountyDivision with the given name: {name}")
        
        return await self.divisionForLevel(guildId, cfg.bountyDivisionLevels[divID][0])
