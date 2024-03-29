from typing import Any, Optional

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, not_, exists, func

from discord.utils import utcnow

from ..lib.asyncUtil import Parallel
from ..entities.bounties.bountyDivision import BountyDivision
from ..entities.bounties.bounty import Bounty

class BountySpawnerService:
    @property
    @classmethod
    def NotFullClause(cls):
        """A query clause that should be operated on the BountyDivision table, selecting divisions that are not full.
        """
        return or_(
            # Divisions that do not have a bounty at the division's lowest difficulty
            not_(exists( \
                select(1) \
                .select_from(Bounty) \
                .where(and_(Bounty.divisionId == BountyDivision.id, Bounty.techLevel == BountyDivision.minLevel)))),

            # Divisions that have not reached capacity, including both active and escaped criminals
            func.count(Bounty) \
                .where(Bounty.divisionId == BountyDivision.id) \
                < BountyDivision.maxBounties()
        )


    async def pollBountySpawns(self, session: AsyncSession):
        """Trigger new bounty spawns in all divisions which are due a new bounty.
        A division will be affected by this call if:
        - it is not full*
        - its next bounty spawn datetime attribute has passed

        *A division is "full" if it has reached max capacity including both active and escaped criminals,
        AND it has no bounty at the lowest level in its range.
        The bounty spawns are executed in parallel. Exceptions are logged, and then swallowed.
        """
        query = select(BountyDivision[Any]) \
            .where(and_(BountySpawnerService.NotFullClause,
                    # This currently warns that the attribute is never null, because pyright sees
                    # The InstrumentedAttribute rather than the underlying Optional[datetime]
                    or_(BountyDivision.nextBounty == None, # type: ignore[reportUnnecessaryComparison]
                        BountyDivision.nextBounty <= utcnow()))) 
        
        tasks = Parallel()

        for division in await session.execute(query):
            tasks.add(division.t[0].spawnNewBounty())

        if tasks.any():
            await tasks.wait()
            tasks.logExceptions()

    
    def getRouteScaledBountyDelayFixed(self, baseDelay: timedelta, lastSpawn: Optional[Bounty[Any]]) -> timedelta:
        """New bounty delay generator, scaling a fixed delay by the length of the presently spawned bounty.

        :param dict baseDelayDict: A dictionary with "min" and "max" timedeltas describing the amount of time to wait
                                    after a bounty is spawned with route length 1
        :return: A timedelta indicating the time to wait before spawning a new bounty
        :rtype: timedelta
        """
        timeScale = cfg.fallbackRouteScale if lastSpawn is None else len(lastSpawn.route)
        delay = baseDelay * timeScale * cfg.newBountyDelayRouteScaleCoefficient

        if cfg.logNewBountyDelays:
            latestCriminal = "no latest criminal." \
                                if lastSpawn is None else \
                                (f"latest criminal: '{lastSpawn.criminal.name}' Route {len(lastSpawn.route)}")
            botState.client.logger.log("Main", "routeScaleBntyDelayFixed",
                                f"New bounty delay generated, {latestCriminal}" \
                                    + f"\nDelay picked: {td_format_noYM(delay)}",
                                category=LogCategory.newBounties,
                                eventType="NONE_BTY" if lastSpawn is None else "DELAY_GEN", noPrint=True)
        return delay


    def getRouteScaledBountyDelayRandom(self, baseDelayDict: MinMaxDict, lastSpawn: Optional[Bounty[Any]]) -> timedelta:
        """New bounty delay generator, generating a random delay time between two points,
        scaled by the length of the presently spawned bounty.

        :param dict baseDelayDict: A dictionary with "min" and "max" timedeltas describing the amount of time to wait
                                    after a bounty is spawned with route length 1
        :return: A timedelta indicating the time to wait before spawning a new bounty
        :rtype: timedelta
        """
        timeScale = cfg.fallbackRouteScale if lastSpawn is None else len(lastSpawn.route)
        delay = getRandomDelay({"min": baseDelayDict["min"], "max": baseDelayDict["max"]})
        delay *= timeScale * cfg.newBountyDelayRouteScaleCoefficient

        if cfg.logNewBountyDelays:
            latestCriminal = "no latest criminal." \
                                if lastSpawn is None else \
                                (f"latest criminal: '{lastSpawn.criminal.name}' Route {len(lastSpawn.route)}")
            minTime = (baseDelayDict["min"] * timeScale * cfg.newBountyDelayRouteScaleCoefficient) / 60
            maxTime = (baseDelayDict["max"] * timeScale * cfg.newBountyDelayRouteScaleCoefficient) / 60
            botState.client.logger.log("Main", "routeScaleBntyDelayRand",
                                f"New bounty delay generated, {latestCriminal}" \
                                    + f"\nRange: " \
                                        + f"{td_format_noYM(minTime)} - {td_format_noYM(maxTime)}" \
                                    + f"\nDelay picked: {td_format_noYM(delay)}",
                                category=LogCategory.newBounties,
                                eventType="NONE_BTY" if lastSpawn is None else "DELAY_GEN", noPrint=True)

        return delay


    async def getRouteTempScaledBountyDelayRandom(self, baseDelayDict: MinMaxDict, lastSpawn: Optional[Bounty[Any]]) -> timedelta:
        """New bounty delay generator, generating a random delay time between two points,
        scaled by the length of the presently spawned bounty and the current activity temperature at the
        presently spawned bounty's tech level.

        :param dict baseDelayDict: A dictionary with "min" and "max" timedeltas describing the amount of time to wait
                                    after a bounty is spawned with route length 1
        :return: A timedelta indicating the time to wait before spawning a new bounty
        :rtype: timedelta
        """
        timeScale = cfg.fallbackRouteScale if lastSpawn is None else len(lastSpawn.route)
        tempScale = self.temperature ** - 0.1
        delay = getRandomDelay({"min": baseDelayDict["min"], "max": baseDelayDict["max"]})
        delay *= tempScale * timeScale * cfg.newBountyDelayRouteScaleCoefficient

        if cfg.logNewBountyDelays:
            latestCriminal = "no latest criminal." \
                                if lastSpawn is None else \
                                (f"latest criminal: '{(await lastSpawn.criminal).name}' Route {len(lastSpawn.route)}")
            minTime = (baseDelayDict["min"] * timeScale * tempScale * cfg.newBountyDelayRouteScaleCoefficient) / 60
            maxTime = (baseDelayDict["max"] * timeScale * tempScale * cfg.newBountyDelayRouteScaleCoefficient) / 60
            botState.client.logger.log("Main", "getRouteTempScaledBountyDelayRandom",
                                f"New bounty delay generated, temp {self.temperature} -> scale {tempScale:.2f}" \
                                    + f"\n{latestCriminal}"
                                    + f"\nRange: " \
                                        + f"{td_format_noYM(minTime)} - {td_format_noYM(maxTime)}" \
                                    + f"\nDelay picked: {td_format_noYM(delay)}",
                                category=LogCategory.newBounties,
                                eventType="NONE_BTY" if lastSpawn is None else "DELAY_GEN", noPrint=True)
        return delay
    

    async def nextBountyTime(self, lastSpawn: Optional[Bounty[Any]]) -> datetime:
        """Get the time at which the next bounty should spawn automatically, assuming the division is not full.

        :param lastSpawn: The most recent bounty to be spawned in this division
        :type lastSpawn: Optional[Bounty[Any]]
        :raises ValueError: If `cfg.newBountyDelayType` is set to an unsupported delay generator
        :return: A utc datetime representing time at which the next bounty should spawn automatically
        :rtype: datetime
        """
        if cfg.newBountyDelayType == "fixed":
            return utcnow() + cfg.timeouts.newBountyFixedDelta
        
        if cfg.newBountyDelayType == "random":
            return utcnow() + getRandomDelay(BOUNTY_SPAWN_DELAY_RAND_RANGE)
        
        if cfg.newBountyDelayType == "fixed-routeScale":
            return utcnow() + self.getRouteScaledBountyDelayFixed(cfg.timeouts.newBountyFixedDelta, lastSpawn)
        
        if cfg.newBountyDelayType == "random-routeScale":
            return utcnow() + self.getRouteScaledBountyDelayRandom(BOUNTY_SPAWN_DELAY_RAND_RANGE, lastSpawn)
        
        if cfg.newBountyDelayType == "random-routeScale-tempScale":
            return utcnow() + await self.getRouteTempScaledBountyDelayRandom(BOUNTY_SPAWN_DELAY_RAND_RANGE, lastSpawn)
        
        raise ValueError(f"Unknown bounty delay generator type in cfg: {cfg.newBountyDelayType}")
