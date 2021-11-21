from __future__ import annotations
from typing import Dict, TYPE_CHECKING
if TYPE_CHECKING:
    from .bountyDB import BountyDB

from ..baseClasses.serializable import Serializable
from ..baseClasses.aliasableDict import AliasableDict
from ..gameObjects.bounties.bounty import Bounty
from ..gameObjects.bounties.criminal import Criminal
from ..gameObjects.bounties.bountyConfig import BountyConfig
from ..gameObjects.bounties.bountyBoards.bountyBoardChannel import BountyBoardChannel
from ..cfg import cfg, bbData
from .. import botState, lib
from ..scheduling.timedTask import TimedTask, DynamicRescheduleTask
from traceback import format_stack

from datetime import timedelta
import random
from typing import List, Any, Union
from discord import TextChannel, Client


class BountyDivision(Serializable):
    """A database of Bounties for a range of tech levels.
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
    delayRandRange = {"min": timedelta(**cfg.timeouts.newBountyDelayRandomMin),
                        "max": timedelta(**cfg.timeouts.newBountyDelayRandomMax)}

    def __init__(self, owningDB: "BountyDB", minLevel: int, maxLevel: int, temperature: int = cfg.minGuildActivity,
                bounties: Dict[int, AliasableDict[Criminal, Bounty]] = None, bountyBoardChannel: BountyBoardChannel = None,
                escapedBounties: Dict[int, AliasableDict[Criminal, Bounty]] = None, alertRoleID: int = -1) -> None:
        """
        :param BountyDB owningDB: The BountyDB that owns this division
        :param int minLevel: The lowest level of bounties available in this division
        :param int maxLevel: The highest level of bounties available in this division
        :param BountyBoardChannel bountyBoardChannel: A BountyBoardChannel object implementing this division's bounty board
                                                        channel if it has one, None otherwise. (Default None)
        :param int alertRoleID: The ID of the role to ping when new bounties are spawned into this division. -1 for no role.
                                (Default -1)
        """
        self.minLevel = minLevel
        self.maxLevel = maxLevel
        self.temperature = temperature
        self.isActive = False
        self.updateIsActive()
        self.latestBounty: Bounty = None
        self.bountyBoardChannel = bountyBoardChannel
        self.alertRoleID = alertRoleID
        # Dictionary of tech level : dict of criminal : bounty
        if bounties is None:
            self.bounties: Dict[int, AliasableDict[Criminal, Bounty]] = {l: AliasableDict()
                                                                        for l in range(self.minLevel, self.maxLevel + 1)}
        else:
            self.bounties = bounties
            for tlBounties in self.bounties.values():
                for bty in tlBounties.values():
                    if self.latestBounty is None or bty.issueTime > self.latestBounty.issueTime:
                        self.latestBounty = bty

        # Dictionary of tech level : dict of criminal : bounty
        if escapedBounties is None:
            self.escapedBounties: Dict[int, AliasableDict[Criminal, Bounty]] = {l: AliasableDict()
                                                                        for l in range(self.minLevel, self.maxLevel + 1)}
        else:
            self.escapedBounties = escapedBounties
        self.owningDB = owningDB

        self.newBountyTT: Union[TimedTask, None] = None
        if not self.hasMinTLBounty() or not self.isFull():
            self.tryStartBountySpawner()


    def hasMinTLBounty(self, includeEscaped: bool = True) -> bool:
        """Decide whether the division has at least one bounty at the division's lowest level.
        This is used for division full-ness decisions.
        Give includeEscaped=False to only consider those bounties which are currently active.

        :param bool includeEscaped: Whether or not to also consider escaped bounties (Default True)
        :return: True if at least one bounty exists at the division's lowest level, False otherwise
        :rtype: bool
        """
        if includeEscaped:
            return bool(self.bounties[self.minLevel]) or bool(self.escapedBounties[self.minLevel])
        else:
            return bool(self.bounties[self.minLevel])


    def tryStartBountySpawner(self):
        """Create a new self.newBountyTT and schedule it onto the botState.taskScheduler, if the division is not already full.
        If the division is full, do nothing.
        Also does nothing in the case that a newBountyTT is already running, to work around race conditions.
        """
        if self.newBountyTT is not None:
            botState.logger.log("BountyDivision", "tryStartBountySpawner", "Attempted to tryStartBountySpawner when a newBountyTT already exists",
                                "newBounties", "TT_EXISTS", "\n".join(format_stack()))
        elif self.isFull() and not self.hasMinTLBounty():
            botState.logger.log("BountyDivision", "tryStartBountySpawner", "Attempted to tryStartBountySpawner when the division is already full",
                                "newBounties", "DIV_FULL", "\n".join(format_stack()))
        else:
            bountyDelayGenerators = {"random": lib.timeUtil.getRandomDelay,
                                    "fixed-routeScale": self.getRouteScaledBountyDelayFixed,
                                    "random-routeScale": self.getRouteScaledBountyDelayRandom,
                                    "random-routeScale-tempScale": self.getRouteTempScaledBountyDelayRandom}

            bountyDelayGeneratorArgs = {"random": self.delayRandRange,
                                        "fixed-routeScale": cfg.newBountyFixedDelta,
                                        "random-routeScale": self.delayRandRange,
                                        "random-routeScale-tempScale": self.delayRandRange}

            if cfg.newBountyDelayType == "fixed":
                self.newBountyTT = TimedTask(expiryDelta=timedelta(**cfg.newBountyFixedDelta),
                                            expiryFunction=self.spawnNewBounty, autoReschedule=True,
                                            rescheduleOnExpiryFuncFailure=True)
            else:
                self.newBountyTT = DynamicRescheduleTask(bountyDelayGenerators[cfg.newBountyDelayType], autoReschedule=True,
                                                        delayTimeGeneratorArgs=bountyDelayGeneratorArgs[cfg.newBountyDelayType],
                                                        rescheduleOnExpiryFuncFailure=True, expiryFunction=self.spawnNewBounty)

            botState.taskScheduler.scheduleTask(self.newBountyTT)


    def stopBountySpawner(self):
        """Stop and delete the new bounty spawner.

        :raise ValueError: If no newBountyTT exists already
        """
        if self.newBountyTT is None:
            raise ValueError("Attempted to stopBountySpawner when newBountyTT already doesnt exist")

        self.newBountyTT.autoReschedule = False
        self.newBountyTT.gravestone = True
        botState.taskScheduler.unscheduleTask(self.newBountyTT)
        self.newBountyTT = None


    def updateIsActive(self):
        """Manually updates the state of self.isActive by attempting to find a temperature above the minimum
        """
        self.isActive = self.temperature != cfg.minGuildActivity


    def getNumBounties(self, level : int = -1, includeEscaped : bool = True) -> int:
        """Decide the number of bounties currently stored in this division.
        Give a tech level for the number of bounties at that level, or -1 for a count across all levels.
        If includeEscaped is given as true, escaped bounties will also be counted.

        :param int level: The tech level whose bounties to count, or -1 for all levels (Default -1)
        :param bool includeEscaped: Whether or not to count escaped bounties as well as active bounties (Default True)
        :return: The number of bounties stored at the given level if one is provided, or in the entire division if given -1
        :rtype: int
        """
        if level == -1:
            if includeEscaped:
                return sum(len(self.bounties[l]) + len(self.escapedBounties[l])
                            for l in range(self.minLevel, self.maxLevel + 1))
            return sum(len(self.bounties[l]) for l in range(self.minLevel, self.maxLevel + 1))
        if includeEscaped:
            return len(self.bounties[level]) + len(self.escapedBounties[level])
        return len(self.bounties[level])


    def bountyObjExists(self, bounty : Bounty) -> bool:
        """Check whether a given bounty object exists in the division.
        Existence is checked by checking if the bounty's criminal is in the division at the bounty's level.

        :param Bounty bounty: The bounty object to check for existence in the division
        :return: True if the bounty's criminal exists here at the bounty's level
        :rtype: bool
        """
        return bounty.criminal in self.bounties[bounty.techLevel]


    def criminalObjExists(self, crim : Criminal) -> bool:
        """Check whether a given criminal object exists in the division.
        Existence is checked across all levels.

        :param Criminal crim: The criminal object to check for existence in the division
        :return: True if the given criminal is found at any level in the division, False otherwise
        :rtype: bool
        """
        return any((crim in tlBounties) for tlBounties in self.bounties.values())


    def escapedCriminalExists(self, crim):
        """Decide whether a criminal is recorded in the escaped criminals database.
        
        :param criminal crim: The criminal to check for existence
        :return: True if crim is in this division's escaped criminals record, False otherwise
        :rtype: bool
        """
        return any((crim in tlBounties) for tlBounties in self.escapedBounties.values())


    def maxBounties(self) -> int:
        """Decide the maximum number of bounties that the division can currently contain, based on the level of
        player activity.

        :return: The maximum number of bounties the division can currently contain
        :rtype: int
        """
        return min(cfg.maxBountiesPerDivision, max(1, self.temperature))


    def pickNewTL(self) -> int:
        """Pick a tech level for a new bounty.
        In ascending order, if a tech level has no bounties, it is returned.
        If all tech levels have at least one bounty, a level is picked at random.

        :return: A tech level to be spawned into this division
        :rtype: int
        :raise OverflowError: When the division has no more space for bounties
        """
        if self.isFull():
            raise OverflowError("Attempted to spawn a new bounty when the DB is currently full")
        try:
            return next(l for l in range(self.minLevel, self.maxLevel + 1) if not self.bounties[l])
        except StopIteration:
            return random.randint(self.minLevel, self.maxLevel)
        

    async def spawnNewBounty(self) -> Bounty:
        """Generate, spawn and announce a random bounty.
        This method ensures that at least one bounty is present at the min tech level of the division,
        and will spawn bounties at random levels otherwise.

        If the division is full after spawning the new bounty, the newBountyTT destroyed

        :return: The newly spawned bounty object
        :rtype: Bounty
        :raise OverflowError: If the division is currently full
        """
        # if no min level bounties exist, ignore the division being full
        if not self.hasMinTLBounty():
            level = self.minLevel
        else:
            if self.isFull():
                raise OverflowError("Attempted to spawn a new bounty when the division is already full")
            level = self.pickNewTL()

        newBounty = Bounty(division=self, config=BountyConfig(techLevel=level).generate(self))
        self.bounties[level][newBounty.criminal] = newBounty

        if self.isFull() and self.hasMinTLBounty():
            self.stopBountySpawner()

        await self.owningDB.owningBasedGuild.announceNewBounty(newBounty)


    async def respawnBounty(self, bounty: Bounty):
        """Regenerate, respawn and announce the given escaped bounty.
        The bounty's attributes are modified in place, no new Bounty object is created.

        :raise OverflowError: If the division is currently full
        :raise KeyError: When given a bounty that is not stored in this division's escaped bounties
        :raise IndexError: When given a bounty whose tech level is not stored in this division
        """
        if bounty.criminal not in self.escapedBounties[bounty.techLevel]:
            raise KeyError("Attempted to respawn a bounty that is not registered as an escaped bounty: " \
                            + bounty.criminal.name)
        if self.isFull(includeEscaped=False):
            raise OverflowError("Attempted to respawn a bounty when the DB is currently full: " + bounty.criminal.name)
        if bounty.techLevel < self.minLevel or bounty.techLevel > self.maxLevel:
            raise IndexError("Attempted to respawn a bounty whose tech level is not stored in this division: " \
                                + bounty.criminal.name + " (" + str(bounty.techLevel) + ")")

        del self.escapedBounties[bounty.techLevel][bounty.criminal]
        bounty.__init__(config=bounty.makeRespawnConfig().generate(self))
        self.bounties[bounty.techLevel][bounty.criminal] = bounty

        if self.isFull() and self.hasMinTLBounty():
            self.stopBountySpawner()

        await self.owningDB.owningBasedGuild.announceNewBounty(bounty)


    def setTemp(self, newTemp: float, updateActive: bool = True):
        """Directly set the division's activity temperature to a given number.

        :param float newTemp: The new temperature
        :param bool updateActive: When True, self.updateIsActive will be called once temp changing is complete (default True)
        """
        wasFull = self.isFull()
        # truncate to 2 decimal places and apply lower bound
        self.temperature = max(cfg.minGuildActivity, round(newTemp, 2))
        if updateActive:
            self.updateIsActive()
        if wasFull or not self.hasMinTLBounty():
            self.tryStartBountySpawner()


    def decayTemp(self, updateActive : bool = True):
        """Multiplies the activity temperature by cfg.guildActivityDecayRate,
        with a lower temperature bound of cfg.minGuildActivity.

        :param bool updateActive: When True, self.updateIsActive will be called once temp decaying is complete (default True)
        """
        if self.isActive:
            # truncate to 2 decimal places and lower bound
            self.temperature = max(cfg.minGuildActivity, round(self.temperature * cfg.guildActivityDecayRate, 1))
            if updateActive:
                self.updateIsActive()


    def raiseTemp(self, amount: float):
        """Raise the activity temperature by a given amount. The operation is a simple addition.
        This operation always sets self.isActive to True.

        :param float amount: The amount to raise the temperature by
        """
        self.temperature += amount
        if not self.isActive:
            self.isActive = True


    def getRouteScaledBountyDelayFixed(self, baseDelayDict: Dict[str, timedelta]) -> timedelta:
        """New bounty delay generator, scaling a fixed delay by the length of the presently spawned bounty.

        :param dict baseDelayDict: A dictionary with "min" and "max" timedeltas describing the amount of time to wait
                                    after a bounty is spawned with route length 1
        :return: A timedelta indicating the time to wait before spawning a new bounty
        :rtype: timedelta
        """
        timeScale = cfg.fallbackRouteScale if self.latestBounty is None else len(self.latestBounty.route)
        delay = timedelta(**baseDelayDict) * timeScale * cfg.newBountyDelayRouteScaleCoefficient

        if cfg.logNewBountyDelays:
            latestCriminal = "no latest criminal." \
                                if self.latestBounty is None else \
                                (f"latest criminal: '{self.latestBounty.criminal.name}' Route {len(self.latestBounty.route)}")
            botState.logger.log("Main", "routeScaleBntyDelayFixed",
                                f"New bounty delay generated, {latestCriminal}" \
                                    + f"\nDelay picked: {lib.timeUtil.td_format_noYM(delay)}",
                                category="newBounties",
                                eventType="NONE_BTY" if self.latestBounty is None else "DELAY_GEN", noPrint=True)
        return delay


    def getRouteScaledBountyDelayRandom(self, baseDelayDict: Dict[str, timedelta]) -> timedelta:
        """New bounty delay generator, generating a random delay time between two points,
        scaled by the length of the presently spawned bounty.

        :param dict baseDelayDict: A dictionary with "min" and "max" timedeltas describing the amount of time to wait
                                    after a bounty is spawned with route length 1
        :return: A timedelta indicating the time to wait before spawning a new bounty
        :rtype: timedelta
        """
        timeScale = cfg.fallbackRouteScale if self.latestBounty is None else len(self.latestBounty.route)
        delay = lib.timeUtil.getRandomDelay({"min": baseDelayDict["min"], "max": baseDelayDict["max"]})
        delay *= timeScale * cfg.newBountyDelayRouteScaleCoefficient

        if cfg.logNewBountyDelays:
            latestCriminal = "no latest criminal." \
                                if self.latestBounty is None else \
                                (f"latest criminal: '{self.latestBounty.criminal.name}' Route {len(self.latestBounty.route)}")
            minTime = (baseDelayDict["min"] * timeScale * cfg.newBountyDelayRouteScaleCoefficient) / 60
            maxTime = (baseDelayDict["max"] * timeScale * cfg.newBountyDelayRouteScaleCoefficient) / 60
            botState.logger.log("Main", "routeScaleBntyDelayRand",
                                f"New bounty delay generated, {latestCriminal}" \
                                    + f"\nRange: " \
                                        + f"{lib.timeUtil.td_format_noYM(minTime)} - {lib.timeUtil.td_format_noYM(maxTime)}" \
                                    + f"\nDelay picked: {lib.timeUtil.td_format_noYM(delay)}",
                                category="newBounties",
                                eventType="NONE_BTY" if self.latestBounty is None else "DELAY_GEN", noPrint=True)

        return delay


    def getRouteTempScaledBountyDelayRandom(self, baseDelayDict: Dict[str, timedelta]) -> timedelta:
        """New bounty delay generator, generating a random delay time between two points,
        scaled by the length of the presently spawned bounty and the current activity temperature at the
        presently spawned bounty's tech level.

        :param dict baseDelayDict: A dictionary with "min" and "max" timedeltas describing the amount of time to wait
                                    after a bounty is spawned with route length 1
        :return: A timedelta indicating the time to wait before spawning a new bounty
        :rtype: timedelta
        """
        timeScale = cfg.fallbackRouteScale if self.latestBounty is None else len(self.latestBounty.route)
        tempScale = self.temperature ** - 0.1
        delay = lib.timeUtil.getRandomDelay({"min": baseDelayDict["min"], "max": baseDelayDict["max"]})
        delay *= tempScale * timeScale * cfg.newBountyDelayRouteScaleCoefficient

        if cfg.logNewBountyDelays:
            latestCriminal = "no latest criminal." \
                                if self.latestBounty is None else \
                                (f"latest criminal: '{self.latestBounty.criminal.name}' Route {len(self.latestBounty.route)}")
            minTime = (baseDelayDict["min"] * timeScale * tempScale * cfg.newBountyDelayRouteScaleCoefficient) / 60
            maxTime = (baseDelayDict["max"] * timeScale * tempScale * cfg.newBountyDelayRouteScaleCoefficient) / 60
            botState.logger.log("Main", "getRouteTempScaledBountyDelayRandom",
                                f"New bounty delay generated, temp {self.temperature} -> scale {tempScale:.2f}" \
                                    + f"\n{latestCriminal}"
                                    + f"\nRange: " \
                                        + f"{lib.timeUtil.td_format_noYM(minTime)} - {lib.timeUtil.td_format_noYM(maxTime)}" \
                                    + f"\nDelay picked: {lib.timeUtil.td_format_noYM(delay)}",
                                category="newBounties",
                                eventType="NONE_BTY" if self.latestBounty is None else "DELAY_GEN", noPrint=True)
        return delay


    def isEmpty(self, includeEscaped: bool = True) -> bool:
        """Decide whether this division contains any bounties.

        :param bool includeEscaped: Whether or not to consider escaped criminals (Default True)
        :return: True if there are no bounties in the division, False otherwise
        :rtype: bool
        """
        if includeEscaped:
            return not any(i for i in self.bounties.values()) or any(i for i in self.escapedBounties.values())
        else:
            return not any(i for i in self.bounties.values())


    def isFull(self, includeEscaped: bool = True) -> bool:
        """Decide whether this division has space for more bounties.

        :param bool includeEscaped: Whether or not to consider escaped criminals (Default True)
        :return: True if the division is at capacity, False otherwise
        :rtype: bool
        """
        return self.getNumBounties(includeEscaped=includeEscaped) >= self.maxBounties()


    async def clear(self, includeEscaped: bool = True):
        """Remove all bounties from the division.
        If any division was full before, restart its new bounty spawner

        :param bool includeEscaped: Whether to also clear escaped bounties (Default True)
        """
        wasFull = self.isFull()
        for tlBounties in self.bounties.values():
            tlBounties.clear()
        if includeEscaped:
            for tlBounties in self.escapedBounties.values():
                for bty in tlBounties.values():
                    await bty.respawnTT.forceExpire(callExpiryFunc=False)
                tlBounties.clear()
        if wasFull or not self.hasMinTLBounty():
            self.tryStartBountySpawner()


    async def resetNewBountyCool(self):
        """Force expiry on the new bounty TimedTask, immediately triggering a new bounty spawn.
        
        :raise OverflowError: If the division is full
        """
        if self.isFull():
            raise OverflowError("Attempted to resetNewBountyCool but the division is full")
        else:
            await self.newBountyTT.forceExpire(callExpiryFunc=True)

    
    async def addBountyBoardChannel(self, channel : TextChannel, client : Client):
        """Set this division's bounty board channel.

        :param discord.Channel channel: The channel where bounty listings should be posted
        :param discord.Client client: A logged in client used to fetch the channel and any existing listings.
        :raise RuntimeError: If the guild already has an active bountyBoardChannel
        """
        if self.bountyBoardChannel is not None:
            raise RuntimeError(f"Attempted to assign a bountyboard channel for division {self.minLevel}-{self.maxLevel} " \
                                + f"in guild {self.owningDB.owningBasedGuild.id} but one is already assigned")
        self.bountyBoardChannel = BountyBoardChannel(channel.id, {}, -1)
        await self.bountyBoardChannel.init(client)


    def removeBountyBoardChannel(self):
        """Deactivate this division's bountyBoardChannel. This does not remove any active bounty listing messages.

        :raise RuntimeError: If this division does not have an active bountyBoardChannel.
        """
        if self.bountyBoardChannel is None:
            raise RuntimeError(f"Attempted to remove a bountyboard channel from division {self.minLevel}-{self.maxLevel} " \
                                + f"in guild {self.owningDB.owningBasedGuild.id} but none is assigned")
        self.bountyBoardChannel = None


    def _addBounty(self, bounty : Bounty, dbReload=False):
        """This is a private method. To ensure unique criminal names across a bountyDB, you should instead call
        BountyDB.addBounty. The BountyDB that owns this division can be accessed through the owningDB attribute. 

        Add the given bounty object to the division.
        If the division is now full, stop the new bounty spawner.

        :param Bounty bounty: the bounty object to add to the database
        :raise OverflowError: if the division is already at capacity
        :raise ValueError: if the criminal is already wanted in the division
        """
        if not dbReload and self.isFull():
            raise OverflowError(f"Attempted to addBounty but the division is full")
        
        if self.criminalObjExists(bounty.criminal):
            raise ValueError(f"Attempted to add {bounty} for a criminal who is already wanted: {bounty.criminal} by {bounty}")

        self.bounties[bounty.techLevel][bounty.criminal] = bounty
        if self.latestBounty is None or bounty.issueTime > self.latestBounty.issueTime:
            self.latestBounty = bounty
        if self.isFull() and self.hasMinTLBounty():
            try:
                self.stopBountySpawner()
            except ValueError as e:
                if not dbReload:
                    raise e


    def _addEscapedBounty(self, bounty : Bounty, dbReload: bool = False, ignoreFull: bool = False):
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
        if not ignoreFull and not dbReload and self.isFull():
            raise OverflowError(f"Attempted to addEscapedBounty but the division is full")
        
        if self.escapedCriminalExists(bounty.criminal):
            raise ValueError(f"Attempted to add {bounty} for a criminal who is already escaped: {bounty.criminal} by {bounty}")

        self.escapedBounties[bounty.techLevel][bounty.criminal] = bounty
        if self.isFull() and self.hasMinTLBounty():
            try:
                self.stopBountySpawner()
            except ValueError as e:
                if not dbReload and not ignoreFull:
                    raise e


    def removeBountyObj(self, bounty : Bounty):
        """Remove a given bounty object from the division.
        If the division was full before, restart the new bounty spawner

        :param Bounty bounty: the bounty object to remove from the database
        """
        wasFull = self.isFull()
        try:
            del self.bounties[bounty.techLevel][bounty.criminal]
        except KeyError:
            raise KeyError("Bounty not found: " + bounty.criminal.name)
        if wasFull or not self.hasMinTLBounty():
            self.tryStartBountySpawner()
    

    def removeEscapedBountyObj(self, bounty : Bounty):
        """Remove a given escaped bounty object from the division.
        If the division was full before, restart the new bounty spawner

        :param Bounty bounty: the bounty object to remove from the database
        """
        wasFull = self.isFull()
        try:
            del self.escapedBounties[bounty.techLevel][bounty.criminal]
        except KeyError:
            raise KeyError("Escaped bounty not found: " + bounty.criminal.name)
        if wasFull or not self.hasMinTLBounty():
            self.tryStartBountySpawner()


    def toDict(self, **kwargs) -> dict:
        """Serialize this division into dictionary format, to be recreated completely.

        :return: A dictionary containing all of the current bounties and the activity temperature
        :rtype: dict
        """
        data = {"temperature": self.temperature, "minLevel": self.minLevel, "maxLevel": self.maxLevel,
                "bounties": {l: [b.toDict(**kwargs) for b in self.bounties[l]]
                            for l in range(self.minLevel, self.maxLevel + 1) if self.bounties[l]},
                "escapedBounties": {l: [b.toDict(**kwargs) for b in self.escapedBounties[l]]
                            for l in range(self.minLevel, self.maxLevel + 1) if self.escapedBounties[l]}}
        if self.bountyBoardChannel is not None:
            data["bountyBoardChannel"] = self.bountyBoardChannel.toDict(**kwargs)
        return data


    @classmethod
    def fromDict(cls, data: dict, owningDB : "BountyDB" = None, **kwargs) -> BountyDivision:
        """Recreate a dictionary-serialized BountyDivision

        :param dict data: A dictionary containing all of the current bounties and the current activity temperature
        :return: A BountyDivision object as specified by the attributes in data
        :rtype: BountyDivision
        """
        if type(owningDB) != BountyDB:
            raise ValueError(f"Expected type BountyDB for kwarg owningDB but received {type(owningDB.__name__)}")
        crims = set()

        bounties = {l: AliasableDict() for l in range(data["minLevel"], data["maxLevel"] + 1)}
        if "bounties" in data:
            for l in data["bounties"]:
                for bty in data["bounties"][l]:
                    newBounty = Bounty.fromDict(bty, owningDB=owningDB, **kwargs)
                    if newBounty.criminal in crims:
                        botState.logger.log("BountyDivision", "fromDict",
                                            f"2 listings for the same criminal found: {bty.criminal.name}. Ignoring one." \
                                                + "Neither was escaped.", category="bountiesDB", eventType="DUPE_CRIM")
                    else:
                        crims.add(newBounty.criminal)
                        bounties[l][newBounty.criminal] = newBounty

        escapedBounties = {l: AliasableDict() for l in range(data["minLevel"], data["maxLevel"] + 1)}
        if "escapedBounties" in data:
            for l in data["escapedBounties"]:
                for bty in data["escapedBounties"][l]:
                    newBounty = Bounty.fromDict(bty, owningDB=owningDB, **kwargs)
                    if newBounty.criminal in crims:
                        botState.logger.log("BountyDivision", "fromDict",
                                            f"2 listings for the same criminal found: {bty.criminal.name}. Ignoring one." \
                                                + "At least one was escaped.", category="bountiesDB", eventType="DUPE_CRIM")
                    else:
                        crims.add(newBounty.criminal)
                        escapedBounties[l][newBounty.criminal] = newBounty

        newDiv = BountyDivision(owningDB, data["minLevel"], data["maxLevel"],
                                **cls._makeDefaults(data, ("type",), bounties=bounties, escapedBounties=escapedBounties))
        
        if "bountyBoardChannel" in data and data["bountyBoardChannel"] is not None:
            newDiv.bountyBoardChannel = BountyBoardChannel.fromDict(data["bountyBoardChannel"], division=newDiv)

        return newDiv
