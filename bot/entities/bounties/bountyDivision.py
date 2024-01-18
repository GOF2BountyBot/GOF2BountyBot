from __future__ import annotations
from typing import Any, Awaitable, Collection, Dict, Optional, Set, Tuple, cast, List, Union, TypeVar
from typing_extensions import Never

from traceback import format_stack
from datetime import datetime, timedelta
import random

from discord import TextChannel, Client
from discord.utils import utcnow

from sqlalchemy.orm import Mapped, relationship, mapped_column, DeclarativeBase
from sqlalchemy import ForeignKey, select, exists, and_, or_, not_, func, delete
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy.ext.asyncio import AsyncSession, AsyncAttrs
from sqlalchemy.exc import InvalidRequestError

from ...baseClasses.aliasableDict import AliasableDict
from .bounty_json import SerializedBounty, SerializedEscapedBounty
from .bounty import AnyBounty, Bounty
from .bountyDivision_json import SerializedBountyDivision
from .criminal import AnyCriminal
from .bountyBoardChannel import BountyBoardChannel, SerializedBountyBoardChannel
from ...cfg import cfg, bbData
from ... import botState, lib
from ...lib.asyncUtil import BasicScheduler
from ...lib import gameMaths
from ...lib.sql import getSession, isMappedInstance
from ...lib.timeUtil import MinMaxDict, getRandomDelay, td_format_noYM
from ...logging import LogCategory
from ...scheduling.timedTask import TimedTask, DynamicRescheduleTask
from ...baseClasses.serializable import SerializesToSchema
from ...repositories.bountyRepository import BountyRepository
from ...database.constants import BountyDivisionTier
from ...database.tables import TableNames
from .bountyRouteEntry import BountyRouteEntry
from ..guilds import basedGuild

BOUNTY_SPAWN_DELAY_RAND_RANGE: MinMaxDict = {
    "min": cfg.timeouts.newBountyDelayRandomMin,
    "max": cfg.timeouts.newBountyDelayRandomMax
}

def divisionNameLevels() -> Dict[str, Tuple[int, int]]:
    return {k: cfg.bountyDivisionLevels[i] for i, k in enumerate(cfg.bountyDivisionNames)}


TSchema = TypeVar("TSchema", bound=SerializedBountyDivision)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class BountyDivision(Base, SerializesToSchema[TSchema]):
    """A guild-level container of Bounties for a range of tech levels.
    The maximum capacity and spawning rates of bounties are based on the "temperature" of the division - an estimate for the
    level of player activity.

    :var temperature: A measure of the level of player activity in this division.
    :vartype temperature: float
    :var minLevel: The lowest level of bounties available in this division
    :varype minLevel: int
    :var maxLevel: The highest level of bounties available in this division
    :varype maxLevel: int
    :var bounties: A record of all currently active bounties, with tech levels as keys
    :vartype bounties: Dict[int, AliasableDict[Criminal, Bounty]]
    :var latestBounty: The most recent bounty to be added to this division. As of writing,
                        this is only used when scaling new bounty delays by the most recent length
    :vartype latestBounty: Union[Bounty, None]
    :var escapedBounties: A record of all currently escaped, inactive bounties, with tech levels as keys
    :vartype escapedBounties: Dict[int, AliasableDict[Criminal, Bounty]]
    :var isActive: True if there is any player activity in this division currently, False otherwise
    :vartype isActive: bool
    :var delayRandRange: A dictionary containing boundary timedeltas for use in random bounty delay generators
    :vartype delayRandRange: Dict[str, timedelta]
    :var bountyBoardChannel: A BountyBoardChannel object implementing this division's bounty board channel if it has one,
                                None otherwise.
    :vartype bountyBoardChannel: BountyBoardChannel
    :var alertRoleID: The ID of the role to ping when new bounties are spawned into this division. -1 if no role is set.
    :vartype alertRoleID: int
    :var newBountyTT: The timedtask responsible for spawning this division's bounties. If the division is full, this is None.
    :vartype newBountyTT: Union[None, TimedTask]
    """
    __tablename__ = TableNames.BountyDivision.value

    id: Mapped[int] = mapped_column(primary_key=True)
    tier: Mapped[BountyDivisionTier]
    temperature: Mapped[float] = mapped_column(default=cfg.minGuildActivity)
    lastSpawnedRouteLength: Mapped[Optional[int]]
    bountyBoardChannelId: Mapped[int] = mapped_column(ForeignKey(f"{TableNames.BountyBoardChannel.value}.id"))
    spawnAlertRoleId: Mapped[Optional[int]]
    guildId: Mapped[int] = mapped_column(ForeignKey(f"{TableNames.Guild.value}.id"))
    _guild: Mapped["basedGuild.BasedGuild"] = relationship()
    _bountyBoardChannel: Mapped[Optional[BountyBoardChannel[SerializedBountyBoardChannel]]] = relationship()
    nextBounty: Mapped[Optional[datetime]]

    @property
    async def guild(self) -> "basedGuild.BasedGuild":
        return await self.awaitable_attrs._guild
    

    @property
    async def bountyBoardChannel(self) -> Optional[BountyBoardChannel[SerializedBountyBoardChannel]]:
        return await self.awaitable_attrs._bountyBoardChannel
    

    @property
    async def activeBounties(self) -> "Collection[Bounty[SerializedBounty]]":
        session = getSession(self)
        query = select(Bounty[SerializedBounty]).where(and_(Bounty.divisionId == self.id, not_(Bounty.isEscaped)))
        result = await session.execute(query)
        return [row[0] for row in result.all()]
    

    @property
    async def escapedBounties(self) -> "Collection[Bounty[SerializedEscapedBounty]]":
        session = getSession(self)
        query = select(Bounty[SerializedEscapedBounty]).where(and_(Bounty.divisionId == self.id, Bounty.isEscaped))
        result = await session.execute(query)
        return [row[0] for row in result.all()]
    

    @hybrid_property
    def name(self) -> str:
        return cfg.bountyDivisionNames[cast(int, self.tier.value) - 1]
    

    @hybrid_property
    def minLevel(self) -> int:
        return cfg.bountyDivisionLevels[cast(int, self.tier.value) - 1][0]
    

    @hybrid_property
    def levelRange(self) -> Collection[int]:
        return range(self.minLevel, self.maxLevel + 1)
    

    @hybrid_property
    def maxLevel(self) -> int:
        return cfg.bountyDivisionLevels[cast(int, self.tier.value) - 1][1]
    

    @hybrid_property
    def isActive(self) -> bool:
        return self.temperature != cfg.minGuildActivity
    
    
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

            # Divisions that are not full
            func.count(Bounty) \
                .where(Bounty.divisionId == BountyDivision.id) \
                < BountyDivision.maxBounties()
        )

    @classmethod
    async def pollBountySpawns(cls, session: AsyncSession):
        """Trigger new bounties spawns in all divisions which are due a new bounty.
        A division will be affected by this call if:
        - it is not full*
        - its next bounty spawn datetime attribute has passed

        The bounty spawns are executed in parallel. Exceptions are logged, and then swallowed.
        """
        query = select(BountyDivision[Any]) \
            .where(and_(BountyDivision.NotFullClause,
                    # This currently warns that the attribute is never null, because pyright sees
                    # The InstrumentedAttribute rathre than the underlying Optional[datetime]
                    or_(BountyDivision.nextBounty == None, # type: ignore[reportUnnecessaryComparison]
                        BountyDivision.nextBounty <= datetime.utcnow()))) 
        
        tasks = BasicScheduler()

        for division in await session.execute(query):
            tasks.add(division.t[0].spawnNewBounty())

        if tasks.any():
            await tasks.wait()
            tasks.logExceptions()


    async def allActiveCriminals(self, session: AsyncSession) -> List[AnyCriminal]:
        """Flatten all of this division's active criminals into a single list

        :return: All currently active criminals
        :rtype: List[Criminal]
        """
        query = select(AnyCriminal) \
            .join(Bounty[Any]).join(BountyDivision) \
            .where(and_(BountyDivision.id == self.id, not_(Bounty.isEscaped)))

        result = await session.execute(query)

        return [t[0] for t in result.all()]


    async def allEscapedCriminals(self, session: AsyncSession) -> List[AnyCriminal]:
        """Flatten all of this division's escaped bounties into a single list

        :return: All currently escaped bounties
        :rtype: List[Bounty]
        """
        query = select(AnyCriminal) \
            .join(Bounty[Any]).join(BountyDivision) \
            .where(and_(BountyDivision.id == self.id, Bounty.isEscaped))

        result = await session.execute(query)

        return [t[0] for t in result.all()]

    
    async def allActiveBountiesForSystem(self, session: AsyncSession, systemId: int) -> List[Bounty[Any]]:
        """Get all active bounties in this division whose routes contain `system`.

        :return: all active bounties in this division whose routes contain `system`
        :rtype: List[Bounty]
        """
        query = select(Bounty[Any]) \
            .join(BountyDivision).join(BountyRouteEntry) \
            .where(and_(BountyRouteEntry.systemId == systemId, not_(Bounty.isEscaped))) \
            .distinct(Bounty.id) # Just in case a route contains this system twice!

        result = await session.execute(query)

        return [t[0] for t in result.all()]


    async def hasMinTLBounty(self, includeEscaped: bool = True) -> bool:
        # TODO: Make this an eagerly loaded attribute: https://docs.sqlalchemy.org/en/20/orm/mapped_sql_expr.html
        """Decide whether the division has at least one bounty at the division's lowest level.
        This is used for division full-ness decisions.
        Give includeEscaped=False to only consider those bounties which are currently active.

        :param bool includeEscaped: Whether or not to also consider escaped bounties (Default True)
        :return: True if at least one bounty exists at the division's lowest level, False otherwise
        :rtype: bool
        """
        session = getSession(self)

        if includeEscaped:
            minLevelExists = exists(
                select(BountyDivision[Any]) \
                .where(and_(Bounty.divisionId == BountyDivision.id, Bounty.techLevel == BountyDivision.minLevel)))
        else:
            minLevelExists = exists(
                select(BountyDivision[Any]) \
                .where(and_(
                    Bounty.divisionId == BountyDivision.id,
                    Bounty.techLevel == BountyDivision.minLevel,
                    not_(Bounty.isEscaped))))
        
        query = select(1).where(minLevelExists)
        
        result = await session.execute(query)
        return result.first() is not None
    

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


    async def getNumBounties(self, level: Optional[int] = None, includeEscaped: bool = True) -> int:
        """Decide the number of bounties currently stored in this division.
        Give a tech level for the number of bounties at that level, or None for a count across all levels.
        If includeEscaped is given as true, escaped bounties will also be counted.

        :param int level: The tech level whose bounties to count, or None for all levels (Default None)
        :param bool includeEscaped: Whether or not to count escaped bounties as well as active bounties (Default True)
        :return: The number of bounties stored at the given level if one is provided, or in the entire division if given None
        :rtype: int
        """
        session = getSession(self)
        query = select(func.count()).select_from(Bounty).where(Bounty.divisionId == self.id)

        if not includeEscaped:
            query = query.where(not_(Bounty.isEscaped))
        
        if level is not None:
            query = query.where(Bounty.techLevel == level)
        
        return await session.scalar(query) or 0


    async def bountyObjExists(self, bounty: Bounty[Any]) -> bool:
        """Check whether a given bounty object exists in the division.
        Existence is checked by checking if the bounty's criminal is in the division at the bounty's level.

        :param Bounty bounty: The bounty object to check for existence in the division
        :return: True if the bounty's criminal exists here at the bounty's level
        :rtype: bool
        """
        session = getSession(self)

        # TODO: Should this just look up the bounty id...?
        query = select(func.count()).select_from(Bounty).where(and_(
            Bounty.divisionId == self.id,
            Bounty.criminalId == bounty.criminalId,
            Bounty.techLevel == bounty.techLevel
        ))

        return await session.scalar(query) == 1


    def criminalObjExists(self, crim: AnyCriminal) -> Awaitable[bool]:
        """Check whether a given criminal object exists in the division.
        Existence is checked across all levels.

        :param Criminal crim: The criminal object to check for existence in the division
        :return: True if the given criminal is found at any level in the division, False otherwise
        :rtype: bool
        """
        return self.criminalIdExists(crim.id)
    

    async def criminalIdExists(self, crim: int) -> bool:
        """Check whether a given criminal object exists in the division.
        Existence is checked across all levels.

        :param int crim: The criminal id to check for existence in the division
        :return: True if the given criminal is found at any level in the division, False otherwise
        :rtype: bool
        """
        session = getSession(self)

        # TODO: Should this just look up the bounty id...?
        query = select(func.count()).select_from(Bounty).where(and_(
            Bounty.divisionId == self.id,
            Bounty.criminalId == crim
        ))

        return await session.scalar(query) == 1


    async def escapedCriminalIdExists(self, crim: int):
        """Decide whether a criminal is recorded in the escaped criminals database.
        
        :param criminal crim: The criminal to check for existence
        :return: True if crim is in this division's escaped criminals record, False otherwise
        :rtype: bool
        """
        session = getSession(self)

        # TODO: Should this just look up the bounty id...?
        query = select(func.count()).select_from(Bounty).where(and_(
            Bounty.divisionId == self.id,
            Bounty.criminalId == crim,
            Bounty.isEscaped
        ))

        return await session.scalar(query) == 1
    

    def escapedCriminalExists(self, crim: AnyCriminal) -> Awaitable[bool]:
        """Decide whether a criminal is recorded in the escaped criminals database.
        
        :param int crim: The criminal id to check for existence
        :return: True if crim is in this division's escaped criminals record, False otherwise
        :rtype: bool
        """
        return self.escapedCriminalIdExists(crim.id)


    @hybrid_method
    def maxBounties(self) -> int:
        """Decide the maximum number of bounties that the division can currently contain, based on the level of
        player activity.

        :return: The maximum number of bounties the division can currently contain
        :rtype: int
        """
        return min(cfg.maxBountiesPerDivision, max(1, int(self.temperature)))


    async def pickNewTL(self) -> int:
        """Pick a tech level for a new bounty.
        In ascending order, if a tech level has no bounties, it is returned.
        If all tech levels have at least one bounty, a level is picked at random.

        :return: A tech level to be spawned into this division
        :rtype: int
        :raise OverflowError: When the division has no more space for bounties
        """
        if not await self.canMakeBounty():
            raise OverflowError("Attempted to spawn a new bounty when the DB is currently full")
        if not await self.hasMinTLBounty():
            return self.minLevel
        
        session = getSession(self)

        # TODO: This is a big waste of queries, we could probably do all the counts in a single query
        for level in range(self.minLevel, self.maxLevel + 1):
            query = select(func.count()).select_from(Bounty).where(and_(
                Bounty.divisionId == self.id,
                Bounty.techLevel == level
            ))
            levelCount = await session.scalar(query)
            if levelCount == 0:
                return level

        return random.randint(self.minLevel, self.maxLevel)
        

    async def spawnNewBounty(self) -> Bounty[Any]:
        """Generate, spawn and announce a random bounty.
        This method ensures that at least one bounty is present at the min tech level of the division,
        and will spawn bounties at random levels otherwise.

        If the division is full after spawning the new bounty, the newBountyTT destroyed

        :return: The newly spawned bounty object
        :rtype: Bounty
        :raise OverflowError: If the division is currently full
        """
        session = getSession(self)
        # if no min level bounties exist, ignore the division being full
        if not await self.hasMinTLBounty():
            level = self.minLevel
        else:
            if await self.isFull():
                raise OverflowError("Attempted to spawn a new bounty when the division is already full")
            level = await self.pickNewTL()

        newBounty: Bounty[Any] = Bounty(division=self, config=BountyConfig(techLevel=level).generate(self))
        session.add(newBounty)

        if not await self.canMakeBounty():
            self.nextBounty = None
        else:
            self.nextBounty = await self.nextBountyTime(newBounty)
        await (await self.guild).announceNewBounty(newBounty)
        return newBounty


    async def respawnBounty(self, bountyId: int):
        """Regenerate, respawn and announce the given escaped bounty.
        The bounty's attributes are modified in place, no new Bounty object is created.

        :raise OverflowError: If the division is currently full
        :raise KeyError: When given a bounty that is not stored in this division's escaped bounties
        :raise IndexError: When given a bounty whose tech level is not stored in this division
        """
        session = getSession(self)
        result = await session.execute(select(Bounty[Any]).where(Bounty.id == bountyId))
        row = result.one_or_none()
        if row is None: raise KeyError(f"Unknown bounty id: {bountyId}")
        bounty = row.t[0]

        if bounty.divisionId != self.id:
            raise KeyError(f"Attempted to respawn a bounty that does not belong to this division: {bounty.criminal.name}")
        if not bounty.isEscaped:
            raise KeyError(f"Attempted to respawn a bounty that is not escaped: {bounty.criminal.name}")
        if bounty.techLevel < self.minLevel or bounty.techLevel > self.maxLevel:
            raise IndexError(f"Attempted to respawn a bounty whose tech level is not stored in this division: {bounty.criminal.name} (bounty.techLevel)")
        if await self.isFull(includeEscaped=False):
            raise OverflowError(f"Attempted to respawn a bounty when the DB is currently full: {bounty.criminal.name}")

        bounty.respawnReconfigure()

        if not await self.canMakeBounty():
            self.nextBounty = None

        await session.commit()
        
        await (await self.guild).announceNewBounty(bounty, isRespawn=True)


    async def announceBountyExpiry(self, bounty: Bounty, dbReload: bool = False):
        """Announce the expiry of a bounty, updating any existing bountyboard channel, and sending a message in the play
        channel. Does not handle removal of the bounty from the division's records

        :param bounty: The bounty that expired
        :type bounty: Bounty
        :param bool dbReload: Give True if this bounty is being expired during bot bootup, False otherwise.
                                This currently toggles whether the passed bounty is checked for existence or not.
                                (Default False)
        :raises KeyError: If no record is kept for the bounty
        """
        if not dbReload and bounty.divisionId != self.id:
            raise KeyError(f"Unknown bounty: {bounty.criminal.name}")

        bbc: Optional[BountyBoardChannel[Any]] = await self.awaitable_attrs.bountyBoardChannel
        if bbc is not None:
            if bounty.isEscaped:
                await bbc.updateEscapedBountiesMessage(ignoredBounties=(bounty,))
            elif bbc.hasMessageForBounty(bounty):
                await bbc.removeBounty(bounty)
                
        await (await self.guild).announceBountyExpired(bounty)


    def setTemp(self, newTemp: float):
        """Directly set the division's activity temperature to a given number.

        :param float newTemp: The new temperature
        """
        # truncate to 2 decimal places and apply lower bound
        self.temperature = max(cfg.minGuildActivity, round(newTemp, 2))


    def decayTemp(self):
        """Multiplies the activity temperature by cfg.guildActivityDecayRate,
        with a lower temperature bound of cfg.minGuildActivity.
        """
        if self.isActive:
            self.setTemp(self.temperature * cfg.guildActivityDecayRate)


    def raiseTemp(self, amount: float):
        """Raise the activity temperature by a given amount. The operation is a simple addition.
        This operation always sets self.isActive to True.

        :param float amount: The amount to raise the temperature by
        """
        self.setTemp(self.temperature + amount)


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


    async def isEmpty(self, includeEscaped: bool = True) -> bool:
        """Decide whether this division contains any bounties.

        :param bool includeEscaped: Whether or not to consider escaped criminals (Default True)
        :return: True if there are no bounties in the division, False otherwise
        :rtype: bool
        """
        session = getSession(self)
        
        query = select(Bounty.id).where(Bounty.divisionId == self.id) 
        if not includeEscaped:
            query = query.where(not_(Bounty.isEscaped))

        return await session.scalar(query) is not None


    async def isFull(self, includeEscaped: bool = True) -> bool:
        """Decide whether this division is full. Does not consider whether a min TL bounty exists.

        :param bool includeEscaped: Whether or not to consider escaped criminals (Default True)
        :return: True if the division is at capacity, False otherwise
        :rtype: bool
        """
        return await self.getNumBounties(includeEscaped=includeEscaped) >= self.maxBounties()

    
    async def canMakeBounty(self) -> bool:
        """Decide whether this division has space for more bounties.
        This is True if the division is not full, or if the division is full but has no min TL bounty.

        :return: True if the division is can accept another bounty, False otherwise
        :rtype: bool
        """
        session = getSession(self)
        
        query = select(BountyDivision.id).where(and_(
            BountyDivision.id == self.id,
            BountyDivision.NotFullClause))

        return await session.scalar(query) is not None


    async def clear(self, includeEscaped: bool = True):
        """Remove all bounties from the division.
        If any division was full before, restart its new bounty spawner

        :param bool includeEscaped: Whether to also clear escaped bounties (Default True)
        """
        session = getSession(self)

        query = delete(Bounty[Any]).where(Bounty.divisionId == self.id)

        if not includeEscaped:
            query = query.where(not_(Bounty.isEscaped))

        await session.execute(query)

        self.nextBounty = self.nextBountyTime(None)

        if self.bountyBoardChannel is None: return
        await self.bountyBoardChannel.clear()

        if not includeEscaped: return
        await self.bountyBoardChannel.updateEscapedBountiesMessage()


    def resetNewBountyCool(self):
        """Trigger a new bounty spawn, if there is space.
        """
        self.nextBounty = None

    
    async def addBountyBoardChannel(self, channel: TextChannel, client: Client):
        """Set this division's bounty board channel.

        :param discord.Channel channel: The channel where bounty listings should be posted
        :param discord.Client client: A logged in client used to fetch the channel and any existing listings.
        :raise RuntimeError: If the guild already has an active bountyBoardChannel
        """
        if self.bountyBoardChannel is not None:
            raise RuntimeError(f"Attempted to assign a bountyboard channel for division {self.minLevel}-{self.maxLevel} " \
                                + f"in guild {self.guildId} but one is already assigned")
        self.bountyBoardChannel = BountyBoardChannel(self, channel.id, {}, -1, -1)
        await self.bountyBoardChannel.init(client)


    def removeBountyBoardChannel(self):
        """Deactivate this division's bountyBoardChannel. This does not remove any active bounty listing messages.

        :raise RuntimeError: If this division does not have an active bountyBoardChannel.
        """
        if self.bountyBoardChannel is None:
            raise RuntimeError(f"Attempted to remove a bountyboard channel from division {self.minLevel}-{self.maxLevel} " \
                                + f"in guild {self.guildId} but none is assigned")
        self.bountyBoardChannel = None


    async def _addBounty(self, bounty: Bounty[Any], dbReload: bool = False, isRespawn: bool = False):
        """This is a private method. To ensure unique criminal names across a bountyDB, you should instead call
        BountyDB.addBounty. The BountyDB that owns this division can be accessed through the owningDB attribute. 

        Add the given bounty object to the division.
        If the division is now full, stop the new bounty spawner.

        :param Bounty bounty: the bounty object to add to the database
        :param bool isRespawn: Skips division fullness checks
        :raise OverflowError: if the division is already at capacity
        :raise ValueError: if the criminal is already wanted in the division
        """
        if not isRespawn and not dbReload and await self.isFull():
            raise OverflowError(f"Attempted to addBounty but the division is full")
        
        if await self.criminalObjExists(bounty.criminal):
            raise ValueError(f"Attempted to add {bounty} for a criminal who is already wanted: {bounty.criminal} by {bounty}")

        if getSession(bounty) is not getSession(self):
            raise InvalidRequestError("The bounty does not belong to the same session as the division")

        bounty.divisionId = self.id

        if not await self.canMakeBounty():
            self.nextBounty = None


    async def _addEscapedBounty(self, bounty: Bounty[Any], dbReload: bool = False, ignoreFull: bool = False):
        """This is a private method. To ensure unique criminal names across a bountyDB, you should instead call
        BountyDB.addEscapedBounty. The BountyDB that owns this division can be accessed through the owningDB attribute. 

        Add the given escaped bounty object to the division.
        If the division is now full, stop the new bounty spawner.

        :param Bounty bounty: the escaped bounty object to add to the database
        :param bool dbReload: When true, skip checking for duplicate bounties and full divisions (Default False)
        :param bool ignoreFull: When true, skip checking if the division is full (Default False)
        :raise OverflowError: if the division is already at capacity
        :raise ValueError: if the criminal is already wanted in the division
        """
        if not bounty.isEscaped:
            raise ValueError("The bounty is not escaped")
        
        if not ignoreFull and not dbReload and await self.isFull():
            raise OverflowError(f"Attempted to addEscapedBounty but the division is full")
        
        if await self.escapedCriminalExists(bounty.criminal):
            raise ValueError(f"Attempted to add {bounty} for a criminal who is already escaped: {bounty.criminal} by {bounty}")

        # Make sure both belong to a db session
        getSession(bounty)
        getSession(self)

        bounty.divisionId = self.id

        if not await self.canMakeBounty():
            self.nextBounty = None


    async def removeBountyObj(self, bounty: Bounty[Any]):
        """Remove a given bounty object from the division.
        If the division was full before, restart the new bounty spawner

        :param Bounty bounty: the bounty object to remove from the database
        """
        if bounty.divisionId != self.id:
            raise KeyError("The bounty does not belong to this division")

        # Make sure both belong to a db session
        getSession(bounty)
        getSession(self)

        if not await self.canMakeBounty():
            self.nextBounty = None

        wasFull = await self.isFull()
        bounty.divisionId = -1

        if self.nextBounty is None and (wasFull or not await self.hasMinTLBounty()):
            self.nextBounty = self.nextBountyTime(None)


    def xpToDivUp(self) -> int:
        """Decides the amount of xp a user must have in order to leave this division.

        :return: the amount of xp a user must have in order to leave this division
        :rtype: int
        """
        if self.maxLevel >= cfg.maxTechLevel:
            return gameMaths.bountyHuntingXPForLevel(self.maxLevel)
        return gameMaths.bountyHuntingXPForLevel(self.maxLevel + 1)


    async def serialize(self, **kwargs: Any) -> TSchema:
        """Serialize this division into dictionary format, to be recreated completely.

        :return: A dictionary containing all of the current bounties and the activity temperature
        :rtype: dict
        """
        baseData = await super().serialize(**kwargs)
        activeBounties = await self.activeBounties
        escapedBounties = await self.escapedBounties

        data: SerializedBountyDivision = {
            "temperature": self.temperature, "minLevel": self.minLevel, "maxLevel": self.maxLevel,
                                          
            "bounties": {l: [b.serialize(**kwargs) for b in activeBounties if b.techLevel == l]
                        for l in range(self.minLevel, self.maxLevel + 1) if activeBounties},

            "escapedBounties": {l: [b.serialize(**kwargs) for b in escapedBounties if b.techLevel == l]
                        for l in range(self.minLevel, self.maxLevel + 1) if escapedBounties}
        }
        
        if self.bountyBoardChannel is not None:
            data["bountyBoardChannel"] = self.bountyBoardChannel.serialize(**kwargs)

        return cast(TSchema, {**baseData, **data})


    @classmethod
    async def deserialize(cls, data: TSchema, **kwargs: Any) -> Never:
        """not implemented.
        """
        raise NotImplementedError()


AnyBountyDivision = BountyDivision[SerializedBountyDivision]
