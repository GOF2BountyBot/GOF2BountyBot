# Typing imports
from __future__ import annotations
from typing import Dict, Union, TYPE_CHECKING
if TYPE_CHECKING:
    from ...databases.bountyDivision import BountyDivision
    from ...databases.bountyDB import BountyDB

from .bountyConfig import BountyConfig
from ...cfg import bbData, cfg
from . import criminal
from ...baseClasses import serializable
from ...scheduling.timedTask import TimedTask
from datetime import datetime, timedelta
from ... import lib, botState
from ..items.shipItem import Ship


class Bounty(serializable.Serializable):
    """A bounty listing for a criminal, to be hunted down by players.

    :var criminal: The criminal who is being hunted
    :vartype criminal: criminal
    :var issueTime: The time at which the bounty was created
    :vartype issueTime: datetime.datetime
    :var route: the names of systems that are in the route
    :vartype route: list[str]
    :var reward: the number of credits available to contributing players
    :vartype reward: int
    :var endTime: the time at which the bounty should automatically expire
    :vartype endTime: datetime.datetime
    :var faction: the faction to which this bounty belongs
    :vartype faction: str
    :var checked: A dictionary tracking which player checked each system. Keys are system names, values are user ids.
                    values for unchecked systems are -1.
    :vartype checked: dict[str, int]
    :var answer: The name of the system where the criminal is located
    :vartype answer: str
    :var activeShip: The ship equipped by this criminal
    :vartype activeShip: shipItem
    :var hasShip: Whether this criminal has a ship equipped or not
    :vartype hasShip: bool
    :var techLevel: The current difficulty level of the bounty
    :vartype techLevel: int
    """

    def __init__(self, criminalObj : criminal.Criminal = None, config : BountyConfig = None,
                    division : BountyDivision = None, dbReload : bool = False):
        """
        :param criminalObj: The criminal to be wanted. Give None to randomly generate a criminal. (Default None)
        :type criminalObj: criminal or None
        :param config: a bountyconfig describing all aspects of this bounty. Give None to randomly generate one (Default None)
        :type config: BountyConfig or None
        :param owningDB: The database of currenly active bounties. This is required unless dbReload is True. (Default None)
        :type owningDB: BountyDB or None
        :param bool dbReload: Give True if this bounty is being created during bot bootup, False otherwise.
                                This currently toggles whether the passed bounty is checked for existence or not.
                                (Default False)
        :raise ValueError: When dbReload is False but owningDB is not given
        """
        if not dbReload and division is None:
            raise ValueError("Bounty constructor: No bounty database given")
        makeFresh = criminalObj is None
        self.activeShip = None
        self.hasShip = False

        if config is None:
            # generate bounty details and validate given details
            if makeFresh:
                config = BountyConfig()
            else:
                config = BountyConfig(faction=criminalObj.faction,
                                        name=criminalObj.name)

        if not config.generated:
            config.generate(division, noCriminal=makeFresh, forceKeepChecked=dbReload, forceNoDBCheck=dbReload)

        if makeFresh:
            if config.builtIn:
                self.criminal = bbData.builtInCriminalObjs[config.name]
                # builtIn criminals cannot be players, so just equip the ship
                # self.equipShip(config.ship)
            else:
                self.criminal = criminal.Criminal(config.name, config.faction, config.icon, isPlayer=config.isPlayer,
                                                    aliases=config.aliases, wiki=config.wiki)
                # Don't just claim player ships! players could unequip ship items. Take a deep copy of the ship
                if config.isPlayer:
                    self.copyShip(config.ship)

        else:
            self.criminal = criminalObj

        if not self.hasShip:
            # Don't just claim player ships! players could unequip ship items. Take a deep copy of the ship
            if config.isPlayer:
                self.copyShip(config.activeShip)
            else:
                self.equipShip(config.activeShip)

        self.faction = self.criminal.faction
        self.issueTime = config.issueTime
        self.endTime = config.endTime
        self.route = config.route
        self.reward = config.reward
        self.rewardPerSys = config.rewardPerSys
        self.checked = config.checked.copy()
        self.answer = config.answer

        self.techLevel = config.techLevel
        self.respawnTT: TimedTask = None
        self.division = division


    def clearShip(self):
        """Delete the equipped ship, removing it from memory

        :raise RuntimeError: If the criminal does not have a ship equipped
        """
        if not self.hasShip:
            raise RuntimeError("CRIM_CLEARSH_NOSHIP: Attempted to clearShip on a Criminal with no active ship")
        del self.activeShip
        self.hasShip = False
        self.techLevel = -1


    def unequipShip(self):
        """unequip the equipped ship, without deleting the object

        :raise RuntimeError: If the criminal does not have a ship equipped
        """
        if not self.hasShip:
            raise RuntimeError("CRIM_UNEQSH_NOSHIP: Attempted to unequipShip on a Criminal with no active ship")
        self.activeShip = None
        self.hasShip = False
        self.techLevel = -1


    def equipShip(self, newShip : Ship):
        """Equip the given ship, by reference to the given object

        :param shipItem ship: The ship to equip
        :raise RuntimeError: If the criminal already has a ship equipped
        """
        if self.hasShip:
            raise RuntimeError("CRIM_EQUIPSH_HASSH: Attempted to equipShip on a Criminal that already has an active ship")
        self.activeShip = newShip
        self.hasShip = True


    def copyShip(self, newShip : Ship):
        """Equip the given ship, by taking a deep copy of the given object

        :param shipItem ship: The ship to equip
        :raise RuntimeError: If the criminal already has a ship equipped
        """
        if self.hasShip:
            raise RuntimeError("CRIM_COPYSH_HASSH: Attempted to copyShip on a Criminal that already has an active ship")
        self.activeShip = Ship.fromDict(newShip.toDict())
        self.hasShip = True


    def check(self, system : str, userID : int) -> int:
        """Check a system along the route. The integer returned by this method indicates the results of the check:
        0 => This system is not in the bounty route.
        1 => this system has already been checked.
        2 => The system was unchecked, but is not the answer.
        3 => answer found.

        :param str system: The name of the system to check
        :param int userID: The id of the user checking the system
        :return: A symbollic integer representing the result of the check, as defined above
        :rtype: int
        """
        if system not in self.route:
            return 0
        elif self.systemChecked(system):
            return 1
        else:
            self.checked[system] = userID
            if self.answer == system:
                return 3
            return 2


    def systemChecked(self, system : str) -> bool:
        """Decide whether or not a system has been checked.

        :param str system: The system to inspect for checking
        :return: True if system has been checked yet, False otherwise
        :rtype: bool
        """
        return self.checked[system] != -1


    def calcRewards(self) -> Dict[int, Dict[str, Union[int, bool]]]:
        """Calculate the winning user and how many credits (and in the future, xp points) to award to which contributing users

        :return: A dictionary of user IDs to rewards. rewards are given as a dict, giving the number of systems checked,
                    the reward credits, and whether this user ID won or not.
        :rtype: dict[int, dict[str, int or bool]]]
        """
        creditsPool = self.reward
        rewards = {}
        checkedSystems = 0
        for system in self.route:
            if self.systemChecked(system):
                checkedSystems += 1
                if self.checked[system] not in rewards:
                    rewards[self.checked[system]] = {"reward": 0, "checked": 0, "won": False, "xp":0}

        winningUserID = self.checked[self.answer]

        for system in self.route:
            if self.systemChecked(system):
                rewards[self.checked[system]]["checked"] += 1
                if self.checked[system] != winningUserID:
                    # currentReward = int(self.reward / len(self.route))
                    # currentReward = bbConfig.bPointsToCreditsRatio
                    currentReward = self.rewardPerSys
                    rewards[self.checked[system]]["reward"] += currentReward
                    creditsPool -= currentReward

        rewards[self.checked[self.answer]]["reward"] = creditsPool
        rewards[self.checked[self.answer]]["won"] = True

        for user in rewards:
            rewards[user]["xp"] = int(rewards[user]["reward"] * cfg.bountyRewardToXPGainMult)
        return rewards


    def isEscaped(self) -> bool:
        """Decide whether this bounty has escaped and is awaiting respawn.

        :return: True if the bounty is escaped and waiting to respawn, False otherwise
        :rtype: bool
        """
        return self.respawnTT is not None


    def escape(self, respawnTT : TimedTask = None, dbReload=False):
        """Mark this bounty as escaped.
        Does not schedule respawning or register the bounty as escaped in the owning bountyDB.

        :param TimedTask respawnTT: The timedtask responsible for the respawning of the bounty
        :raise ValueError: If the bounty is already marked as escaped
        """
        if self.isEscaped():
            raise ValueError("Attempted to mark a bounty as escaped that is already escaped: " + self.criminal.name)
        
        if respawnTT is None:
            self.respawnTT = TimedTask(expiryDelta=timedelta(minutes=len(self.route)), 
                                        expiryFunction=self._respawn,
                                        rescheduleOnExpiryFuncFailure=True)
        else:
            self.respawnTT = respawnTT

        if self.criminal in self.division.bounties[self.techLevel]:
            self.division.owningDB.removeBountyObj(self)
        botState.taskScheduler.scheduleTask(self.respawnTT)
        self.division.owningDB.addEscapedBounty(self, dbReload=dbReload, ignoreFull=True)


    async def _respawn(self):
        if not self.isEscaped():
            raise ValueError("Attempted to respawn on a bounty that is not awaiting respawn: " + self.criminal.name)

        respawnArgs = {"newBounty": self,
                        "newConfig": BountyConfig(faction=self.criminal.faction,
                                                                techLevel=self.techLevel)}
        await self.division.owningDB.owningBasedGuild.spawnAndAnnounceBounty(respawnArgs)
        # This is handled by spawnAndAnnounceBounty
        # self.division.owningDB.removeEscapedCriminal(self.criminal)
        self.respawnTT = None


    def cancelRespawn(self):
        """Cancel the respawning of the bounty, by forcing the expiry of its respawn TimedTask.

        :raise ValueError: If the bounty is not escaped
        """
        if not self.isEscaped():
            raise ValueError("Attempted to cancelRespawn on a bounty that is not awaiting respawn: " + self.criminal.name)
        self.respawnTT.forceExpire(callExpiryFunc=False)
        self.respawnTT = None
        self.division.owningDB.removeEscapedCriminal(self.criminal)


    def forceRespawn(self):
        """Force the immediate respawning of the bounty, by forcing the expiry of its respawn TimedTask.

        :raise ValueError: If the bounty is not escaped
        """
        if not self.isEscaped():
            raise ValueError("Attempted to forceRespawn on a bounty that is not awaiting respawn: " + self.criminal.name)
        self.respawnTT.forceExpire(callExpiryFunc=True)


    def makeRespawnConfig(self):
        """Create a new, partially configured, ungenerated BountyConfig object, to be used in the respawning of this bounty.

        :return: A new BountyConfig with the right attributes left ungenerated, to be populated on bounty respawn
        :rtype: BountyConfig
        """
        return BountyConfig(faction=self.faction, name=self.name, isPlayer=self.criminal.isPlayer,
                            issueTime=self.issueTime, activeShip=self.activeShip, techLevel=self.techLevel)


    def toDict(self, **kwargs) -> dict:
        """Serialize this bounty to dictionary, to be saved to file.

        :return: A dictionary representation of this bounty.
        :rtype: dict
        """
        data = {"faction": self.faction, "route": self.route, "answer": self.answer, "checked": self.checked,
                "reward": self.reward, "issueTime": self.issueTime, "endTime": self.endTime, "isEscaped": self.isEscaped(),
                "criminal": self.criminal.toDict(**kwargs), "rewardPerSys": self.rewardPerSys, "techLevel": self.techLevel}
        
        if self.isEscaped():
            data["respawnTime"] = self.respawnTT.expiryTime.timestamp()

        if self.hasShip:
            data["activeShip"] = self.activeShip.toDict()

        return data


    @classmethod
    def fromDict(cls, data : dict, owningDB: BountyDB = None, dbReload: bool = False, **kwargs) -> Bounty:
        """Factory function constructing a new bounty from a dictionary serialized description - the opposite of bounty.toDict

        :param dict bounty: Dictionary containing all information needed to construct the desired bounty
        :param bool dbReload: Give True if this bounty is being created during bot bootup, False otherwise.
                                This currently toggles whether the passed bounty is checked for existence or not.
                                (Default False)
        """
        if type(data) != dict:
            raise ValueError(str(data))
        if owningDB is None:
            raise ValueError("missing required argument: owningDB")

        if "activeShip" in data:
            activeShip = Ship.fromDict(data["activeShip"])
        else:
            activeShip = None

        if "techLevel" in data:
            techLevel = data["techLevel"]
        elif activeShip is not None:
            techLevel = activeShip.techLevel
        else:
            raise ValueError(f"Missing required data: Bounty tech level. Data: {str(data)}")
            # techLevel = -1

        newCfg = BountyConfig(faction=data["faction"], route=data["route"],
                                answer=data["answer"], checked=data["checked"], reward=data["reward"],
                                issueTime=data["issueTime"], endTime=data["endTime"],
                                rewardPerSys=data["rewardPerSys"], activeShip=activeShip,
                                techLevel=techLevel)
                                            
        newBounty = Bounty(dbReload=dbReload, config=newCfg, division=owningDB.divisionForLevel(techLevel),
                            criminalObj=criminal.Criminal.fromDict(data["criminal"]))
        
        if data.get("isEscaped", False):
            if "respawnTime" not in data:
                raise ValueError("Not given respawnTime for escaped criminal " + data["criminal"]["name"])
            respawnTT = TimedTask(issueTime=datetime.utcfromtimestamp(data["issueTime"]),
                                    expiryTime=datetime.utcfromtimestamp(data["respawnTime"]), 
                                    expiryFunction=newBounty._respawn,
                                    rescheduleOnExpiryFuncFailure=True)
            newBounty.escape(respawnTT=respawnTT, dbReload=dbReload)

        return newBounty
