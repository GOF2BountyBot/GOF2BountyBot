from typing import Any, Awaitable, List, Collection, Optional, Union, overload

import random

from sqlalchemy import select, and_, not_, exists, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

import discord

from ..repositories.bountyDivisionRepository import BountyDivisionRepository
from . import bountySpawnerService, bountyService, bountyBoardChannelService
from ..entities.bounties.bountyDivision import AnyBountyDivision
from ..entities.bounties.criminal import AnyCriminal
from ..entities.bounties.bounty import AnyBounty, Bounty
from ..entities.bounties.bounty_json import SerializedActiveBounty, SerializedEscapedBounty
from ..entities.bounties.bountyRouteEntry import BountyRouteEntry
from ..entities.bounties.bountyConfig import BountyConfigFactory, NpcBountyConfig
from ..entities.bounties.bountyBoardChannel import BountyBoardChannel
from ..entities.guilds.basedGuild import BasedGuild
from ..lib.sql import getSession
from .. import client
from ..lib.asyncUtil import Parallel

class BountyDivisionService:
    def __init__(self,
                 bountyDivisionRepository: BountyDivisionRepository,
                 bountyConfigFactory: BountyConfigFactory,
                 bountySpawnerService: "bountySpawnerService.BountySpawnerService",
                 bountyService: "bountyService.BountyService",
                 bountyBoardChannelService: "bountyBoardChannelService.BountyBoardChannelService",
                 client: "client.BasedClient"):
        self.bountyDivisionRepository = bountyDivisionRepository
        self.bountyConfigFactory = bountyConfigFactory
        self.bountySpawnerService = bountySpawnerService
        self.bountyService = bountyService
        self.bountyBoardChannelService = bountyBoardChannelService
        self.client = client


    async def allActiveCriminals(self, division: AnyBountyDivision) -> List[AnyCriminal]:
        """Flatten all of this division's active criminals into a single list

        :return: All currently active criminals
        :rtype: List[Criminal]
        """
        session = getSession(division)

        query = select(AnyCriminal) \
            .join(AnyBounty).join(AnyBountyDivision) \
            .where(and_(AnyBountyDivision.id == division.id, not_(AnyBounty.isEscaped)))

        result = await session.execute(query)

        return [t[0] for t in result.all()]


    async def allEscapedCriminals(self, division: AnyBountyDivision) -> List[AnyCriminal]:
        """Flatten all of this division's escaped bounties into a single list

        :return: All currently escaped bounties
        :rtype: List[Bounty]
        """
        session = getSession(division)

        query = select(AnyCriminal) \
            .join(AnyBounty).join(AnyBountyDivision) \
            .where(and_(AnyBountyDivision.id == division.id, AnyBounty.isEscaped))

        result = await session.execute(query)

        return [t[0] for t in result.all()]

    
    async def allActiveBountiesForSystem(self, division: AnyBountyDivision, systemId: int) -> List[AnyBounty]:
        """Get all active bounties in this division whose routes contain `system`.

        :return: all active bounties in this division whose routes contain `system`
        :rtype: List[Bounty]
        """
        session = getSession(division)
        
        query = select(AnyBounty) \
            .join(AnyBountyDivision).join(BountyRouteEntry) \
            .where(and_(
                AnyBountyDivision.id == division.id,
                BountyRouteEntry.systemId == systemId,
                not_(AnyBounty.isEscaped))) \
            .distinct(AnyBounty.id) # Just in case a route contains this system twice!

        result = await session.execute(query)

        return [t[0] for t in result.all()]


    async def hasMinTLBounty(self, division: AnyBountyDivision, includeEscaped: bool = True) -> bool:
        # TODO: Make this an eagerly loaded attribute: https://docs.sqlalchemy.org/en/20/orm/mapped_sql_expr.html
        """Decide whether the division has at least one bounty at the division's lowest level.
        This is used for division full-ness decisions.
        Give includeEscaped=False to only consider those bounties which are currently active.

        :param bool includeEscaped: Whether or not to also consider escaped bounties (Default True)
        :return: True if at least one bounty exists at the division's lowest level, False otherwise
        :rtype: bool
        """
        session = getSession(division)

        if includeEscaped:
            minLevelExists = exists(
                select(AnyBounty) \
                .where(and_(AnyBounty.divisionId == division.id, AnyBounty.techLevel == division.minLevel)))
        else:
            minLevelExists = exists(
                select(AnyBounty) \
                .where(and_(
                    AnyBounty.divisionId == division.id,
                    AnyBounty.techLevel == division.minLevel,
                    not_(AnyBounty.isEscaped))))
        
        query = select(1).where(minLevelExists)
        
        result = await session.execute(query)
        return result.first() is not None
    

    async def activeBounties(self, division: AnyBountyDivision) -> "Collection[Bounty[SerializedActiveBounty]]":
        session = getSession(division)
        query = select(Bounty[SerializedActiveBounty]).where(and_(Bounty.divisionId == division.id, not_(Bounty.isEscaped)))
        result = await session.execute(query)
        return [row[0] for row in result.all()]
    

    @overload
    async def escapedBounties(self, division: AnyBountyDivision, /) -> "Collection[Bounty[SerializedEscapedBounty]]": ...

    @overload
    async def escapedBounties(self, divisionId: int, session: AsyncSession, /) -> "Collection[Bounty[SerializedEscapedBounty]]": ...

    async def escapedBounties(self, divisionOrId: Union[AnyBountyDivision, int], session: Optional[AsyncSession] = None) -> "Collection[Bounty[SerializedEscapedBounty]]":
        if isinstance(divisionOrId, int):
            if session is None:
                raise ValueError("session is required if division is specified by id")
            divisionId = divisionOrId
        else:
            session = getSession(divisionOrId)
            divisionId = divisionOrId.id

        query = select(Bounty[SerializedEscapedBounty]).where(and_(Bounty.divisionId == divisionId, Bounty.isEscaped))
        result = await session.execute(query)
        return [row[0] for row in result.all()]


    async def getNumBounties(self, division: AnyBountyDivision, level: Optional[int] = None, includeEscaped: bool = True) -> int:
        """Decide the number of bounties currently stored in this division.
        Give a tech level for the number of bounties at that level, or None for a count across all levels.
        If includeEscaped is given as true, escaped bounties will also be counted.

        :param int level: The tech level whose bounties to count, or None for all levels (Default None)
        :param bool includeEscaped: Whether or not to count escaped bounties as well as active bounties (Default True)
        :return: The number of bounties stored at the given level if one is provided, or in the entire division if given None
        :rtype: int
        """
        session = getSession(division)
        query = select(func.count()).select_from(Bounty).where(Bounty.divisionId == division.id)

        if not includeEscaped:
            query = query.where(not_(Bounty.isEscaped))
        
        if level is not None:
            query = query.where(Bounty.techLevel == level)
        
        return await session.scalar(query) or 0


    async def bountyObjExists(self, division: AnyBountyDivision, bounty: Bounty[Any]) -> bool:
        """Check whether a given bounty object exists in the division.
        Existence is checked by checking if the bounty's criminal is in the division at the bounty's level.

        :param Bounty bounty: The bounty object to check for existence in the division
        :return: True if the bounty's criminal exists here at the bounty's level
        :rtype: bool
        """
        session = getSession(division)

        # TODO: Should this just look up the bounty id...?
        query = select(func.count()).select_from(Bounty).where(and_(
            Bounty.divisionId == division.id,
            Bounty.criminalId == bounty.criminalId,
            Bounty.techLevel == bounty.techLevel
        ))

        return await session.scalar(query) == 1


    def criminalObjExists(self, division: AnyBountyDivision, crim: AnyCriminal) -> Awaitable[bool]:
        """Check whether a given criminal object exists in the division.
        Existence is checked across all levels.

        :param Criminal crim: The criminal object to check for existence in the division
        :return: True if the given criminal is found at any level in the division, False otherwise
        :rtype: bool
        """
        return self.criminalIdExists(division, crim.id)
    

    async def criminalIdExists(self, division: AnyBountyDivision, crim: int) -> bool:
        """Check whether a given criminal object exists in the division.
        Existence is checked across all levels.

        :param int crim: The criminal id to check for existence in the division
        :return: True if the given criminal is found at any level in the division, False otherwise
        :rtype: bool
        """
        session = getSession(division)

        # TODO: Should this just look up the bounty id...?
        query = select(func.count()).select_from(Bounty).where(and_(
            Bounty.divisionId == division.id,
            Bounty.criminalId == crim
        ))

        return await session.scalar(query) == 1


    async def escapedCriminalIdExists(self, division: AnyBountyDivision, crim: int):
        """Decide whether a criminal is recorded in the escaped criminals database.
        
        :param criminal crim: The criminal to check for existence
        :return: True if crim is in this division's escaped criminals record, False otherwise
        :rtype: bool
        """
        session = getSession(division)

        # TODO: Should this just look up the bounty id...?
        query = select(func.count()).select_from(Bounty).where(and_(
            Bounty.divisionId == division.id,
            Bounty.criminalId == crim,
            Bounty.isEscaped
        ))

        return await session.scalar(query) == 1
    

    def escapedCriminalExists(self, division: AnyBountyDivision, crim: AnyCriminal) -> Awaitable[bool]:
        """Decide whether a criminal is recorded in the escaped criminals database.
        
        :param int crim: The criminal id to check for existence
        :return: True if crim is in this division's escaped criminals record, False otherwise
        :rtype: bool
        """
        return self.escapedCriminalIdExists(division, crim.id)


    async def pickNewTL(self, division: AnyBountyDivision) -> int:
        """Pick a tech level for a new bounty.
        In ascending order, if a tech level has no bounties, it is returned.
        If all tech levels have at least one bounty, a level is picked at random.

        :return: A tech level to be spawned into this division
        :rtype: int
        :raise OverflowError: When the division has no more space for bounties
        """
        if not await self.canMakeBounty(division):
            raise OverflowError("Attempted to spawn a new bounty when the DB is currently full")
        if not await self.hasMinTLBounty(division):
            return division.minLevel
        
        session = getSession(division)

        # TODO: This is a big waste of queries, we could probably do all the counts in a single query
        for level in range(division.minLevel, division.maxLevel + 1):
            query = select(func.count()).select_from(Bounty).where(and_(
                Bounty.divisionId == division.id,
                Bounty.techLevel == level
            ))
            levelCount = await session.scalar(query)
            if levelCount == 0:
                return level

        return random.randint(division.minLevel, division.maxLevel)
        

    async def spawnNewBounty(self, division: AnyBountyDivision) -> Bounty[Any]:
        """Generate, spawn and announce a random bounty.
        This method ensures that at least one bounty is present at the min tech level of the division,
        and will spawn bounties at random levels otherwise.

        If the division is full after spawning the new bounty, the newBountyTT destroyed

        :return: The newly spawned bounty object
        :rtype: Bounty
        :raise OverflowError: If the division is currently full
        """
        session = getSession(division)
        # if no min level bounties exist, ignore the division being full
        if not await self.hasMinTLBounty(division):
            level = division.minLevel
        else:
            if await self.isFull(division):
                raise OverflowError("Attempted to spawn a new bounty when the division is already full")
            level = await self.pickNewTL(division)

        template = NpcBountyConfig(techLevel=level)
        config = await self.bountyConfigFactory.generate(template, division)

        newBounty: Bounty[Any] = Bounty(division=division, config=config)
        session.add(newBounty)

        if not await self.canMakeBounty(division):
            division.nextBounty = None
        else:
            division.nextBounty = await self.bountySpawnerService.nextBountyTime(newBounty)

        await (await division.guild).announceNewBounty(newBounty)
        return newBounty


    async def respawnBounty(self, division: AnyBountyDivision, bountyId: int):
        """Regenerate, respawn and announce the given escaped bounty.
        The bounty's attributes are modified in place, no new Bounty object is created.

        :raise OverflowError: If the division is currently full
        :raise KeyError: When given a bounty that is not stored in this division's escaped bounties
        :raise IndexError: When given a bounty whose tech level is not stored in this division
        """
        session = getSession(division)
        result = await session.execute(select(Bounty[Any]).where(Bounty.id == bountyId))
        row = result.one_or_none()
        if row is None: raise KeyError(f"Unknown bounty id: {bountyId}")
        bounty = row.t[0]

        if bounty.divisionId != division.id:
            raise KeyError(f"Attempted to respawn a bounty that does not belong to this division: criminal #{bounty.criminalId}")
        if not bounty.isEscaped:
            raise KeyError(f"Attempted to respawn a bounty that is not escaped: criminal #{bounty.criminalId}")
        if bounty.techLevel < division.minLevel or bounty.techLevel > division.maxLevel:
            raise IndexError(f"Attempted to respawn a bounty whose tech level is not stored in this division: criminal #{bounty.criminalId} (level {bounty.techLevel})")
        if await self.isFull(division, includeEscaped=False):
            raise OverflowError(f"Attempted to respawn a bounty when the DB is currently full: criminal #{bounty.criminalId}")

        await self.bountyService.respawnReconfigure(bounty)

        if not await self.canMakeBounty(division):
            division.nextBounty = None

        await session.commit()
        
        await (await division.guild).announceNewBounty(bounty, isRespawn=True)


    async def announceBountyExpiry(self, division: AnyBountyDivision, bounty: AnyBounty, dbReload: bool = False):
        """Announce the expiry of a bounty, updating any existing bountyboard channel, and sending a message in the play
        channel. Does not handle removal of the bounty from the division's records

        :param bounty: The bounty that expired
        :type bounty: Bounty
        :param bool dbReload: Give True if this bounty is being expired during bot bootup, False otherwise.
                                This currently toggles whether the passed bounty is checked for existence or not.
                                (Default False)
        :raises KeyError: If no record is kept for the bounty
        """
        if not dbReload and bounty.divisionId != division.id:
            raise KeyError(f"Unknown bounty: criminal #{bounty.criminalId}")

        bbc: Optional[BountyBoardChannel[Any]] = await division.awaitable_attrs.bountyBoardChannel
        if bbc is not None:
            if bounty.isEscaped:
                await self.bountyBoardChannelService.updateEscapedBountiesMessage(bbc, ignoredBounties=(bounty,))
            elif await bbc.hasMessageForBounty(bounty):
                await self.bountyBoardChannelService.removeBounty(bbc, bounty)
                
        await (await division.guild).announceBountyExpired(bounty)


    async def isEmpty(self, division: AnyBountyDivision, includeEscaped: bool = True) -> bool:
        """Decide whether this division contains any bounties.

        :param bool includeEscaped: Whether or not to consider escaped criminals (Default True)
        :return: True if there are no bounties in the division, False otherwise
        :rtype: bool
        """
        session = getSession(division)
        
        query = select(Bounty.id).where(Bounty.divisionId == division.id) 
        if not includeEscaped:
            query = query.where(not_(Bounty.isEscaped))

        return await session.scalar(query) is not None


    async def isFull(self, division: AnyBountyDivision, includeEscaped: bool = True) -> bool:
        """Decide whether this division is full. Does not consider whether a min TL bounty exists.

        :param bool includeEscaped: Whether or not to consider escaped criminals (Default True)
        :return: True if the division is at capacity, False otherwise
        :rtype: bool
        """
        return await self.getNumBounties(division, includeEscaped=includeEscaped) >= division.maxBounties()

    
    async def canMakeBounty(self, division: AnyBountyDivision) -> bool:
        """Decide whether this division has space for more bounties.
        This is True if the division is not full, or if the division is full but has no min TL bounty.

        :return: True if the division is can accept another bounty, False otherwise
        :rtype: bool
        """
        session = getSession(division)
        
        query = select(AnyBountyDivision.id).where(and_(
            AnyBountyDivision.id == division.id,
            bountySpawnerService.BountySpawnerService.NotFullClause))

        return await session.scalar(query) is not None


    async def clear(self, division: AnyBountyDivision, includeEscaped: bool = True):
        """Remove all bounties from the division.
        If any division was full before, restart its new bounty spawner

        :param bool includeEscaped: Whether to also clear escaped bounties (Default True)
        """
        session = getSession(division)

        query = delete(Bounty[Any]).where(Bounty.divisionId == division.id)

        if not includeEscaped:
            query = query.where(not_(Bounty.isEscaped))

        await session.execute(query)

        division.nextBounty = await self.bountySpawnerService.nextBountyTime(None)

        if division.bountyBoardChannelId is None: return

        bbc = await division.bountyBoardChannel
        if bbc is None: return

        await self.bountyBoardChannelService.clear(bbc)

        if not includeEscaped: return
        await self.bountyBoardChannelService.updateEscapedBountiesMessage(bbc)


    @overload
    async def clearAllForGuild(self, guild: BasedGuild, /, includeEscaped: bool = True) -> None: ...

    @overload
    async def clearAllForGuild(self, guildId: int, /, includeEscaped: bool = True) -> None: ...

    async def clearAllForGuild(self, guild: Union[BasedGuild, int], /, includeEscaped: bool = True) -> None:
        """Remove all bounties from the division.
        If any division was full before, restart its new bounty spawner

        :param bool includeEscaped: Whether to also clear escaped bounties (Default True)
        """
        guildId = guild if isinstance(guild, int) else guild.id
        session = getSession(guild)

        divisions = await self.bountyDivisionRepository.getForGuild(guildId)
        divisionIds = [d.id for d in divisions]

        query = delete(AnyBounty).where(AnyBounty.divisionId.in_(divisionIds))

        if not includeEscaped:
            query = query.where(not_(Bounty.isEscaped))

        await session.execute(query)

        async def update(division: AnyBountyDivision):
            await self.setNextBountyTime(division, None)

            bbc = await division.bountyBoardChannel
            if bbc is not None:
                await self.bountyBoardChannelService.clear(bbc)


        tasks = Parallel(update(division) for division in divisions)
        await tasks.wait()
        tasks.raiseExceptions()


    def resetNewBountyCool(self, division: AnyBountyDivision):
        """Trigger a new bounty spawn, if there is space.
        """
        division.nextBounty = None

    
    async def addBountyBoardChannel(self, division: AnyBountyDivision, channel: discord.TextChannel):
        """Set this division's bounty board channel.

        :param discord.Channel channel: The channel where bounty listings should be posted
        :param discord.Client client: A logged in client used to fetch the channel and any existing listings.
        :raise RuntimeError: If the guild already has an active bountyBoardChannel
        """
        session = getSession(division)

        if division.bountyBoardChannelId is not None:
            raise RuntimeError(f"Attempted to assign a bountyboard channel for division {division.minLevel}-{division.maxLevel} " \
                                + f"in guild {division.guildId} but one is already assigned")
        
        bbc: BountyBoardChannel[Any] = BountyBoardChannel(divisionId=division.id, channelId=channel.id)
        session.add(bbc)

        division.setBountyBoardChannel(bbc)


    async def removeBountyBoardChannel(self, division: AnyBountyDivision):
        """Deactivate this division's bountyBoardChannel.
        This does delete the boundyBoardChannel from the bot's database, but it does not have 
        any effect on discord - e.g active bounty listing messages will not be removed.

        :raise RuntimeError: If this division does not have an active bountyBoardChannel.
        """
        if division.bountyBoardChannelId is None:
            raise RuntimeError(f"Attempted to remove a bountyboard channel from division {division.minLevel}-{division.maxLevel} " \
                                + f"in guild {division.guildId} but none is assigned")
        
        session = getSession(division)
        await session.delete(division)

        division.setBountyBoardChannel(None)


    async def addBounty(self, division: AnyBountyDivision, bounty: Bounty[Any], dbReload: bool = False, isRespawn: bool = False):
        """Add the given bounty object to the division.
        If the division is now full, stop the new bounty spawner.

        :param Bounty bounty: the bounty object to add to the database
        :param bool isRespawn: Skips division fullness checks
        :raise OverflowError: if the division is already at capacity
        :raise ValueError: if the criminal is already wanted in the division
        """
        if not isRespawn and not dbReload and await self.isFull(division):
            raise OverflowError(f"Attempted to addBounty but the division is full")
        
        if await self.criminalIdExists(division, bounty.criminalId):
            raise ValueError(f"Attempted to add {bounty} for a criminal who is already wanted: {bounty.criminalId} by {bounty.id}")

        session = getSession(bounty)
        if session is not getSession(division):
            raise ValueError("The bounty does not belong to the same session as the division")

        await self._addBountyInternal(session, division, bounty)


    async def _addBountyInternal(self, session: AsyncSession, division: AnyBountyDivision, bounty: Bounty[Any]):
        """This is a private method.
        """
        bounty.divisionId = division.id
        await session.commit()

        if not await self.canMakeBounty(division):
            division.nextBounty = None


    async def addEscapedBounty(self, division: AnyBountyDivision, bounty: Bounty[Any], dbReload: bool = False, ignoreFull: bool = False):
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
        
        if not ignoreFull and not dbReload and await self.isFull(division):
            raise OverflowError(f"Attempted to addEscapedBounty but the division is full")
        
        if await self.escapedCriminalIdExists(division, bounty.criminalId):
            raise ValueError(f"Attempted to add {bounty} for a criminal who is already escaped: {bounty.criminal} by {bounty}")

        session = getSession(bounty)
        if session is not getSession(division):
            raise ValueError("The bounty does not belong to the same session as the division")

        bounty.divisionId = division.id
        await session.commit()

        if not await self.canMakeBounty(division):
            division.nextBounty = None


    async def moveBounty(self, toDivision: AnyBountyDivision, bounty: Bounty[Any]):
        """Move a given bounty object from its old division to a new one.

        :param BountyDivision toDivisionId: the id of the division to move the bounty to
        :param Bounty bounty: the bounty to move
        """
        if bounty.divisionId == toDivision.id:
            raise KeyError("The bounty already belongs to this division")

        session = getSession(bounty)
        if session is not getSession(toDivision):
            raise ValueError("The bounty does not belong to the same session as the division")

        oldDivision = await bounty.division

        wasFull = await self.isFull(oldDivision)
        await self._addBountyInternal(session, toDivision, bounty)

        if oldDivision.nextBounty is None and (wasFull or not await self.hasMinTLBounty(oldDivision)):
            await self.setNextBountyTime(oldDivision, None)


    async def setNextBountyTime(self, division: AnyBountyDivision, lastSpawn: Optional[Bounty[Any]]):
        """Set the time at which the next bounty should spawn automatically, assuming the division is not full.

        :param lastSpawn: The most recent bounty to be spawned in this division
        :type lastSpawn: Optional[Bounty[Any]]
        :raises ValueError: If `cfg.newBountyDelayType` is set to an unsupported delay generator
        :return: A utc datetime representing time at which the next bounty should spawn automatically
        :rtype: datetime
        """
        division.nextBounty = await self.bountySpawnerService.nextBountyTime(lastSpawn)
