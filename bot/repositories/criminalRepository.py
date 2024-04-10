from typing import Optional, cast

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_

from ..lib.sql import randomRows
from ..entities.bounties.criminal import AnyCriminal
from ..entities.bounties.bountyDivision import AnyBountyDivision
from ..entities.bounties.bounty import AnyBounty
from .snowflakeRepository import SnowflakeRepository

class CriminalRepository(SnowflakeRepository[AnyCriminal]):
    def __init__(self, session: AsyncSession):
        super().__init__(AnyCriminal, session)


    async def randomCriminal(self, forGuild: Optional[int] = None, forFaction: Optional[str] = None) -> AnyCriminal:
        """Select a random criminal.
        If `forGuild` is given, the returned criminal is guaranteed not to already be wanted or escaped in `forGuild`.
        If `forFaction` is given, the criminal will belong to `forFaction`.

        :param Optional[int] forGuild: The ID of a guild whose active/excaped criminals to exclude
        :param Optional[str] forFaction: Filter criminals to only those belonging to this faction
        :return: A random criminal
        :rtype: Criminal
        :raise OverflowError: When no criminals can be found, or when all criminals are wanted in `forGuild` and/or `forFaction`
        """
        query = randomRows(AnyCriminal).limit(1)
        if forGuild is not None:
            # isouter renders as a LEFT OUTER join. This returns all Criminal rows, regardless of
            # whether there is a matching Bounty/BountyDivision row. Rows without a matching Bounty/BountyDivision
            # will have a None id, so I'm casting here to allow for that.
            #
            # This matches criminals who do not have an active bounty in any guild:
            #   Bounty.id == None
            # This matches criminals who do not have an active bounty in the supplied guild:
            #   BountyDivision.guildId != forGuild
            #
            # The BountyDivision join is also LEFT OUTER, because Criminals with no Bounty will also
            # have no BountyDivision. A Criminal can only have no BountyDivision if it also has no Bounty,
            # so we don't need to add an OR clause for BountyDivision.id == None.
            query = query.join(AnyBounty, isouter=True) \
                .join(AnyBountyDivision, isouter=True) \
                .where(or_(
                    AnyBounty.id == cast(int, None),
                    AnyBountyDivision.guildId != forGuild,
                ))
            
        if forFaction is not None:
            query = query.where(AnyCriminal.faction == forFaction)
        
        result = await self.session.execute(query)
        row = result.first()

        if row is None:
            raise OverflowError(
                ("No criminals found in database" if forGuild is None else f"No non-wanted criminals in guild {forGuild}")
                + "" if forFaction is None else f" for faction {forFaction}"
            )
        
        return row.t[0]
