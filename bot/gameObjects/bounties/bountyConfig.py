# Typing imports
from __future__ import annotations, division
from typing import TYPE_CHECKING, List, Dict, Optional, Protocol, Any, Type, Union
if TYPE_CHECKING:
    from ...databases import bountyDivision

import random
from datetime import datetime, timedelta

from ...cfg import bbData, cfg
from ... import lib, botState
from ...lib import gameMaths
from ...logging import LogCategory
from ..items.modules import armourModule, shieldModule, moduleItem
from ..items.ships import shipItem
from ..items.weapons import primaryWeapon, turretWeapon
from ...databases import bountyDB

class ValidatorWithKwargs(Protocol):
    def __call__(self, tl: int, **kwargs) -> bool: ...


class ValidatorNoKwargs(Protocol):
    def __call__(self, tl: int) -> bool: ...


ValidatorType = Union[ValidatorNoKwargs, ValidatorWithKwargs]


def findItemTL(center: int, minTL: int, maxTL: int, upperBound: int, validator: ValidatorType, **kwargs) -> int:
    """Attempt to find an integer tl where:
        minTL <= tl <= min(maxTL, center + upperBound)
        validator(tl) == True

    first [minTL... center] will be searched in descending order.
    then, [center + 1... min(maxTL, center + upperBound)] will be searched in ascending order.
    upperBound is provided for convenience, identical behaviour can be made by giving upperBound = 0 and
    maxTL as center + upperBound' where upperBound' is the value which would have been given for upperBound

    :param int center: The center of the search, being the upper bound for downward searching and
                        the lower bound for upward searching
    :param int minTL: The lowest bound for searching
    :param int maxTL: The upper bound for searching
    :param int upperBound: The maximum number of steps above center to search
    :param function validator: A function deciding whether or not a tl is acceptible.
                                validator must take one positional argument, being the tl, and return a bool.
                                If kwargs are given, they will be passed to validator
    :return: If one exists, a number tl, between minTL and min(maxTL, center + upperBound), and validator(tl)
            is True. -1 if no such number exists.
    """
    if minTL > maxTL:
        raise ValueError("maxTL must be at least minTL. minTL = " + str(minTL) + ", maxTL = " + str(maxTL))
    if center < minTL or center > maxTL:
        raise ValueError("center must be between minTL and maxTL, inclusive. " \
                            + "minTL = " + str(minTL) + ", maxTL = " + str(maxTL) + ", center = " + str(center))
    if upperBound < 0:
        raise ValueError("upperBound must be at least 0. Given " + str(upperBound))
    tl = center
    maxTL = min(maxTL, center + upperBound)

    while tl >= minTL:
        if validator(tl, **kwargs):
            return tl
        tl -= 1
    
    if center < maxTL:
        tl = center + 1
        while tl <= maxTL:
            if validator(tl, **kwargs):
                return tl
            tl += 1
    
    return -1

    # # Old implementation
    # tlsTried = 0
    # upward = False
    # while tlsTried < maxTL - minTL:
    #     if validator(tl):
    #         return tl
    #     else:
    #         tlsTried += 1
    #         if tl == minTL:
    #             if tl < maxTL - 1:
    #                 upward = True
    #                 tl = center + 1
    #             else:
    #                 break
    #         elif upward:
    #             if tl - center < upperBound:
    #                 tl += 1
    #             else:
    #                 break
    #         else:
    #             tl -= 1
    # return -1


def shipTLHasPrimaries(tl: int) -> bool:
    """Decide if at least one ship exists with the given tech level and has at least one primary weapon slot.

    :param int tl: The tech level to search
    :return: True if at least one ship exists with tech level tl and has at least one primary weapon slot. False otherwise
    :rtype: False
    """
    for shipKey in bbData.shipKeysByTL[tl]:
        shipData = bbData.builtInShipData[shipKey]
        # Ignoring here because pyright doesn't know the structure of a serialized ship
        if "maxPrimaries" in shipData and shipData["maxPrimaries"] > 0: # type: ignore[reportGeneralTypeIssues]
            return True
    return False


def tlDBHasType(index: int, db: List[List[Any]], itemType: type = object) -> bool:
    """Decide if db[index] contains an element of the given type.

    :param int index: The index of the sub-list in db to search for an element of the given type
    :param List[List[Any]] db: A list containing lists of objects to type check
    :param type itemType: The element class to search for
    :return: True if at least one element of the index'th sub-list in db is an instance of itemType, False otherwise
    :rtype: bool
    """
    for item in db[index]:
        if isinstance(item, itemType):
            return True
    return False


def tlDBHasEquippableType(index: int, db: List[List[Any]], itemType: type,
                            activeShip: shipItem.Ship) -> bool:
    """Decide if db[index] contains an element of the given type, and the type of that element is an equippable module on
    the given ship.

    :param int index: The index of the sub-list in db to search for an element of the given type
    :param List[List[Any]] db: A list containing lists of objects to type check
    :param type itemType: The element class to search for
    :param Ship activeShip: The ship to test for element equippability
    :return: True if at least one element of the index'th sub-list in db is an instance of itemType and is equippable on
                activeShip, False otherwise
    :rtype: bool
    """
    for item in db[index]:
        if isinstance(item, itemType) and activeShip.canEquipModuleType(type(item)):
            return True
    return False


class BountyConfig:
    """Configurator class describing all attributes needed for a bounty object.

    :var faction: The faction owning this bounty
    :vartype faction: str
    :var name: The name of the wanted criminal. If this is a player bounty, name should be the player mention.
    :vartype name: str
    :var isPlayer: Whether or not the target criminal is a player or an npc
    :vartype isPlayer: bool
    :var route: the names of systems in this bounty's route
    :vartype route: list[str]
    :var start: The name of the system at the start of the route
    :vartype start: str
    :var end: The name of the system at the end of the route
    :vartype end: str
    :var answer: The name of the system where the criminal is located
    :vartype answer: str
    :var checked: Dictionary of system names to user IDs, where the id corresponds to the user who checked that system,
                    or -1 if the system is unchecked.
    :vartype checked: dict[str, int]
    :var reward: Prize pool of credits to award to contributing users
    :vartype reward: int
    :var issueTime: A utc timestamp representing the time at which the bounty was issued
    :vartype issueTime: float
    :var endTime: A utc timestamp representing the time at which the bounty should automatically expire
    :vartype endTime: flaot
    :var icon: A URL directly linking to an image to use as the criminal's icon
    :vartype icon: str
    :var aliases: Aliases that can be used to refer to this criminal
    :vartype aliases: list[str]
    :var wiki: The page to link to as the criminal's wiki, in their info embed
    :vartype wiki: str
    :var builtIn: whether or not this is a built in npc criminal
    :vartype builtIn: bool
    :var generated: whether or not this config is ready to be used. The config must verify and generate its attributes before
                    they can be used in a bounty.
    :vartype generated: bool
    :var activeShip: The shipItem this criminal should equip
    :vartype activeShip: shipItem
    """

    def __init__(self, faction: str = "", name: str = "", isPlayer: Optional[bool] = None,
                    route: List[str] = [], start: str = "", end: str = "",
                    answer: str = "", checked: Dict[str, int] = {}, reward: int = -1,
                    issueTime: float = -1.0, endTime: float = -1.0, icon: str = "",
                    aliases: List[str] = [], wiki: str = "", activeShip: Optional[shipItem.Ship] = None,
                    techLevel: int = -1, rewardPerSys: int = -1):
        """All parameters are optional. If a parameter is not given, it will be randomly generated.

        :param faction: The faction owning this bounty
        :type faction: str
        :param name: The name of the wanted criminal. If this is a player bounty, name should be the player mention.
        :type name: str
        :param isPlayer: Whether or not the target criminal is a player or an npc
        :type isPlayer: bool
        :param route: the names of systems in this bounty's route
        :type route: list[str]
        :param start: The name of the system at the start of the route
        :type start: str
        :param end: The name of the system at the end of the route
        :type end: str
        :param answer: The name of the system where the criminal is located
        :type answer: str
        :param checked: Dictionary of system names to user IDs, where the id corresponds to the user who checked that system,
                        or -1 if the system is unchecked.
        :type checked: dict[str, int]
        :param reward: Prize pool of credits to award to contributing users
        :type reward: int
        :param issueTime: A utc timestamp representing the time at which the bounty was issued
        :type issueTime: float
        :param endTime: A utc timestamp representing the time at which the bounty should automatically expire
        :type endTime: flaot
        :param icon: A URL directly linking to an image to use as the criminal's icon
        :type icon: str
        :param aliases: Aliases that can be used to refer to this criminal
        :type aliases: list[str]
        :param wiki: The page to link to as the criminal's wiki, in their info embed
        :type wiki: str
        :param activeShip: The shipItem this criminal should equip
        :type activeShip: shipItem
        """
        self.faction = faction.lower()
        self.name = name.title()
        self.isPlayer = False if isPlayer is None else isPlayer
        self.route = []
        for system in route:
            self.route.append(system.title())

        self.start = start.title()
        self.end = end.title()
        self.answer = answer.title()
        self.checked = checked
        self.reward = reward
        self.rewardPerSys = rewardPerSys
        if type(rewardPerSys) == float:
            self.rewardPerSys = int(rewardPerSys)
        if type(reward) == float:
            self.reward = int(reward)
        self.issueTime = issueTime
        self.endTime = endTime
        self.icon = icon
        self.generated = False
        self.builtIn = False

        self.aliases = aliases
        self.wiki = wiki

        self.activeShip = activeShip
        self.techLevel = techLevel


    def generate(self, division: bountyDivision.BountyDivision, noCriminal: bool = True, forceKeepChecked: bool = False,
                    forceNoDBCheck: bool = False) -> BountyConfig:
        """Validate all given config data, and randomly generate missing data.

        :param BountyDB owningDB: Database containing all currently active bounties. When forceNoDBCheck is True,
                                    this is ignored.
        :param bool noCriminal: If this is True, randomly generate a criminal object. (Default True)
        :param bool forceKeepChecked: If this is False, a blank checked dictionary will be used.
                                        This should only be set to be True when using a pre-made checked dictionary;
                                        e.g for custom bounties or for bounties loaded from file. (Default False)
        :param bool forceNoDBCheck: If this is False, do not check if the bounty already exists.
                                        This should only be used as a performance and compatibility measure when
                                        loading in a bounty from file. (Default False)
        :return: This BountyConfig object for chaining
        :rtype: BountyConfig
        :raise ValueError: When requesting an invalid faction, or when requesting an invalid reward amount
        :raise IndexError: When no space is available for a new bounty
        :raise KeyError: When the requested criminal name already exists in a bounty or when requesting an unknown system name
        :raise OverflowError: When attempting to spawn a bounty into a full division
        """
        doDBCheck = not forceNoDBCheck

        if doDBCheck and division.isFull() and (division.hasMinTLBounty() or \
                (not division.hasMinTLBounty() and self.techLevel not in [division.minLevel, -1])):
            raise OverflowError("The given division is full: " + bountyDB.nameForDivision(division))
            
        if noCriminal:
            if self.name in bbData.bountyNames:
                self.builtIn = True
            else:
                if self.faction == "":
                    self.faction = random.choice(bbData.bountyFactions)

                else:
                    if self.faction not in bbData.bountyFactions:
                        raise ValueError("BOUCONF_CONS_INVFAC: Invalid faction requested '" + self.faction + "'")

                if self.name == "":
                    self.builtIn = True
                    self.name = random.choice(bbData.bountyNames[self.faction])
                    while doDBCheck and division.owningDB.bountyNameExists(self.name, noEscapedCrim=False):
                        self.name = random.choice(bbData.bountyNames[self.faction])
                else:
                    if doDBCheck and division.owningDB.bountyNameExists(self.name, noEscapedCrim=False):
                        raise KeyError("BountyConfig: attempted to create config for pre-existing bounty: " + self.name)

                    if self.icon == "":
                        self.icon = bbData.rocketIcon

        if self.techLevel == -1:
            self.techLevel = division.pickNewTL()
            # self.techLevel = gameMaths.pickRandomCriminalTL()

        if self.route == []:
            tries = 3
            success = False
            while tries:
                if self.start == "":
                    startAttempt = random.choice(list(bbData.builtInSystemObjs.keys()))
                    while startAttempt == self.end or not bbData.builtInSystemObjs[startAttempt].hasJumpGate():
                        startAttempt = random.choice(list(bbData.builtInSystemObjs.keys()))
                elif self.start not in bbData.builtInSystemObjs:
                    raise KeyError("BountyConfig: Invalid start system requested '" + self.start + "'")
                else:
                    startAttempt = self.start

                if self.end == "":
                    endAttempt = random.choice(list(bbData.builtInSystemObjs.keys()))
                    while startAttempt == endAttempt or not bbData.builtInSystemObjs[endAttempt].hasJumpGate():
                        endAttempt = random.choice(list(bbData.builtInSystemObjs.keys()))
                elif self.end not in bbData.builtInSystemObjs:
                    raise KeyError("BountyConfig: Invalid end system requested '" + self.end + "'")
                else:
                    endAttempt = self.end

                routeAttempt = lib.pathfinding.bbAStar(startAttempt, endAttempt, bbData.builtInSystemObjs)
                if not isinstance(routeAttempt, lib.pathfinding.PathfindingError):
                    self.route = routeAttempt
                    self.start = startAttempt
                    self.end = endAttempt
                    success = True
                    break
                tries -= 1
            if not success:
                raise ValueError(f"Unable to generate route. Start: {self.start or '<auto>'} -> End: {self.end or '<auto>'}")
        else:
            for system in self.route:
                if system not in bbData.builtInSystemObjs:
                    raise KeyError("BountyConfig: Invalid system in route '" + system + "'")
        if self.answer == "":
            self.answer = random.choice(self.route)
        elif self.answer not in bbData.builtInSystemObjs:
            raise KeyError("Bounty constructor: Invalid answer requested '" + self.answer + "'")
        
        if self.techLevel == 0:
            self.activeShip = shipItem.Ship.deserialize(cfg.level0CrimLoadout)
        elif self.activeShip is None:
            if self.isPlayer:
                raise ValueError("Attempted to generate a player bounty without providing the activeShip")

            # tech leve 0 = guaranteed lowest difficulty loadout
            if self.techLevel == 0:
                self.activeShip = shipItem.Ship.deserialize(cfg.level0CrimLoadout)
            # Otherwise, generate one based on difficulty
            else:
                itemTL = self.techLevel - 1

                # First attempt to find a TL for which a ship exists with primary weapon slots
                shipTL = findItemTL(itemTL, cfg.minTechLevel - 1, cfg.maxTechLevel - 1,
                                    cfg.criminalMaxGearUpgrade, shipTLHasPrimaries)
                shipWithPrimaryExists = shipTL != -1

                if not shipWithPrimaryExists:
                    # If no such TL could be found, settle for a TL for which a ship exists
                    shipTL = findItemTL(itemTL, cfg.minTechLevel - 1, cfg.maxTechLevel - 1,
                                        # Ignoring a warning here because tlDBHasType is a valid validator
                                        cfg.criminalMaxGearUpgrade, tlDBHasType, # type: ignore[reportGeneralTypeIssues]
                                        db=bbData.shipKeysByTL, itemType=str)

                    # If no such TL could be found, there must be no ships in the game
                    if shipTL == -1:
                        raise ValueError("Unable to create no criminal, no ships registered in the game.")
                
                shipKey = random.choice(bbData.shipKeysByTL[shipTL])
                if shipWithPrimaryExists:
                    # Ignoring here because pyright doesn't know the structure of a serialized ship
                    shipHasPrimary = "maxPrimaries" in bbData.builtInShipData[shipKey] \
                                            and bbData.builtInShipData[shipKey]["maxPrimaries"] > 0 # type: ignore[reportGeneralTypeIssues]
                    while not shipHasPrimary:
                        # Ignoring here because pyright doesn't know the structure of a serialized ship
                        shipKey = random.choice(bbData.shipKeysByTL[shipTL])
                        shipHasPrimary = "maxPrimaries" in bbData.builtInShipData[shipKey] \
                                            and bbData.builtInShipData[shipKey]["maxPrimaries"] > 0 # type: ignore[reportGeneralTypeIssues]
                                            
                self.activeShip = shipItem.Ship.deserialize(bbData.builtInShipData[shipKey])

                if shipWithPrimaryExists:
                    # Attempt to find damage-dealing weapons first
                    weaponTL = findItemTL(itemTL, cfg.minTechLevel - 1, cfg.maxTechLevel - 1, cfg.criminalMaxGearUpgrade,
                                            # Ignoring a warning here because my lambda is a valid validator
                                            lambda i, db, itemType: tlDBHasType(i, db, itemType) \
                                                                    and any(x.dps for x in db[i]), # type: ignore[reportGeneralTypeIssues]
                                            db=bbData.weaponObjsByTL, itemType=primaryWeapon.PrimaryWeapon)
                    dpsWeapons = weaponTL != -1
                    
                    # Couldn't find a TL with damage dealing weapons
                    if not dpsWeapons:
                        # Try for TLs with non-damaging weapons
                        weaponTL = findItemTL(itemTL, cfg.minTechLevel - 1, cfg.maxTechLevel - 1, cfg.criminalMaxGearUpgrade,
                                                # Ignoring a warning here because tlDBHasType is a valid validator
                                                tlDBHasType, db=bbData.weaponObjsByTL, itemType=primaryWeapon.PrimaryWeapon) # type: ignore[reportGeneralTypeIssues]

                        if weaponTL == -1:
                            botState.client.logger.log("BountyConfig", "generate",
                                                "unable to find any TLs containing weapons",
                                                eventType="NO_ITEMS", category=LogCategory.bountyConfig)

                    if weaponTL != -1:
                        numWeapons = random.randint(max(1, self.activeShip.maxPrimaries - 1), self.activeShip.maxPrimaries)
                        for _ in range(numWeapons):
                            currentWeapon = random.choice(bbData.weaponObjsByTL[weaponTL])
                            # The chosen weapon doesnt deal damage. If the TL has damage-dealing weapons,
                            # randomly choose whether or not to ensure a damage-dealing weapon is picked
                            if dpsWeapons and not currentWeapon.dps \
                                    and random.randint(0, 100) > cfg.criminalEquipDamagelessWeaponChance:
                                while not currentWeapon.dps:
                                    currentWeapon = random.choice(bbData.weaponObjsByTL[weaponTL])
                            self.activeShip.equipWeapon(currentWeapon)

                moduleTypesToEquip: Dict[Type[moduleItem.ModuleItem], int] = {armourModule.ArmourModule: 0, shieldModule.ShieldModule: 0}
                reservedSlots = 0
                # ensure criminals above TL 1 have armour
                if self.techLevel > 1:
                    moduleTypesToEquip[armourModule.ArmourModule] = 1
                    reservedSlots += 1
                # ensure criminals above TL 3 have shield
                if self.techLevel > 3:
                    moduleTypesToEquip[shieldModule.ShieldModule] = 1
                    reservedSlots += 1

                maxExtraModules = self.activeShip.maxModules - self.activeShip.getNumModulesEquipped() - reservedSlots
                moduleTypesToEquip[moduleItem.ModuleItem] = random.randint(1, maxExtraModules)

                for moduleType in moduleTypesToEquip:
                    while self.activeShip.canEquipMoreModules() and self.activeShip.canEquipModuleType(moduleType) \
                            and moduleTypesToEquip[moduleType] > 0:

                        moduleTL = findItemTL(itemTL, cfg.minTechLevel - 1, cfg.maxTechLevel - 1, cfg.criminalMaxGearUpgrade,
                                                # Ignoring a warning here because tlDBHasEquippableType is a valid validator
                                                tlDBHasEquippableType, db=bbData.moduleObjsByTL, itemType=moduleType, # type: ignore[reportGeneralTypeIssues]
                                                activeShip=self.activeShip)
                        
                        if moduleTL == -1:
                            botState.client.logger.log("BountyConfig", "generate",
                                                "unable to find any TLs containing equippable " + moduleType.__name__ + "s",
                                                eventType="NO_ITEMS", category=LogCategory.bountyConfig)
                            break
                        else:
                            itemToEquip = random.choice(bbData.moduleObjsByTL[moduleTL])
                            while not isinstance(itemToEquip, moduleType):
                                itemToEquip = random.choice(bbData.moduleObjsByTL[moduleTL])

                            if self.activeShip.canEquipModuleType(type(itemToEquip)):
                                self.activeShip.equipModule(itemToEquip)
                                moduleTypesToEquip[moduleType] -= 1

                if self.activeShip.maxTurrets:
                    # Attempt to find damage-dealing turrets first
                    turretTL = findItemTL(itemTL, cfg.minTechLevel - 1, cfg.maxTechLevel - 1, cfg.criminalMaxGearUpgrade,
                                            # Ignoring a warning here because my lambda is a valid validator
                                            lambda i, db, itemType: tlDBHasType(i, db, itemType) \
                                                                    and any(x.dps for x in db[i]), # type: ignore[reportGeneralTypeIssues]
                                            db=bbData.turretObjsByTL, itemType=turretWeapon.TurretWeapon)
                    dpsTurrets = turretTL != -1
                    
                    # Couldn't find a TL with damage dealing turrets
                    if not dpsTurrets:
                        # Try for TLs with non-damaging turrets
                        turretTL = findItemTL(itemTL, cfg.minTechLevel - 1, cfg.maxTechLevel - 1, cfg.criminalMaxGearUpgrade,
                                                # Ignoring a warning here because tlDBHasType is a valid validator
                                                tlDBHasType, db=bbData.turretObjsByTL, itemType=turretWeapon.TurretWeapon) # type: ignore[reportGeneralTypeIssues]

                        if turretTL == -1:
                            botState.client.logger.log("BountyConfig", "generate",
                                                "unable to find any TLs containing turrets",
                                                eventType="NO_ITEMS", category=LogCategory.bountyConfig)

                    if turretTL != -1:
                        numTurrets = random.randint(max(0, self.activeShip.maxTurrets - 1), self.activeShip.maxTurrets)
                        for _ in range(numTurrets):
                            currentTurret = random.choice(bbData.turretObjsByTL[turretTL])
                            # The chosen turret doesnt deal damage. If the TL has damage-dealing turrets,
                            # randomly choose whether or not to ensure a damage-dealing turret is picked
                            if dpsTurrets and not currentTurret.dps \
                                    and random.randint(0, 100) > cfg.criminalEquipDamagelessWeaponChance:
                                while not currentTurret.dps:
                                    currentTurret = random.choice(bbData.turretObjsByTL[turretTL])
                            self.activeShip.equipTurret(currentTurret)

        if self.reward == -1:
            # self.reward = int(len(self.route) * cfg.classic_creditsPerCheck \
            #                 + self.activeShip.getValue() * cfg.shipValueRewardPercentage)
            self.rewardPerSys = gameMaths.rewardPerSysCheck(self.techLevel, self.activeShip.getValue())
            self.reward = self.rewardPerSys * len(self.route)
        elif self.reward < 0:
            raise ValueError("Bounty constructor: Invalid reward requested '" + str(self.reward) + "'")
        if self.issueTime == -1.0:
            self.issueTime = datetime.utcnow().replace(second=0).timestamp()
        if self.endTime == -1.0:
            self.endTime = (datetime.utcfromtimestamp(self.issueTime) + timedelta(days=len(self.route))).timestamp()

        if not forceKeepChecked:
            self.checked = {}
        for station in self.route:
            if (not forceKeepChecked) or station not in self.checked or self.checked == {}:
                self.checked[station] = -1

        self.generated = True
        return self


    def copy(self) -> BountyConfig:
        """Get a new BountyConfig object with the same attributes as this instance.
        If this instance has not yet been generated, neither will the copy.

        :return: A shallow copy of this object
        :rtype: BountyConfig
        """
        return BountyConfig(faction=self.faction, name=self.name, isPlayer=self.isPlayer,
                    route=self.route, start=self.start, end=self.end,
                    answer=self.answer, checked=self.checked, reward=self.reward,
                    issueTime=self.issueTime, endTime=self.endTime, icon=self.icon,
                    aliases=self.aliases, wiki=self.wiki, activeShip=self.activeShip,
                    techLevel=self.techLevel, rewardPerSys=self.rewardPerSys)


class GeneratedConfig(BountyConfig):
    faction: str
    name: str
    isPlayer: bool
    route: List[str]
    start: str
    end: str
    answer: str
    checked: Dict[str, int]
    reward: int
    issueTime: float
    endTime: float
    icon: str
    aliases: List[str]
    wiki: str
    activeShip: shipItem.Ship
    techLevel: int
    rewardPerSys: int
                    