from __future__ import annotations
from enum import Enum

from typing import Callable, Optional, Sequence, Tuple, Type, Union, TYPE_CHECKING, Dict, List, MutableSet, cast, TypeVar
from typing_extensions import NotRequired, TypedDict
from datetime import datetime, timedelta
from discord import AllowedMentions, Embed, File, Guild, GuildSticker, HTTPException, Member, Message, MessageReference, PartialMessage, StickerItem, User
from discord.ui import View
from discord.utils import MISSING, utcnow

from bot.gameObjects.items.ships import shipItem, shipBase

if TYPE_CHECKING:
    from bot.gameObjects.battles import duelRequest
    from .. import client

from bot.baseClasses.serializable import SerializesToSchema
from bot.baseClasses.basedEnum import BasedEnum
from bot.cfg import cfg, bbData
from bot.cfg.bbData import ItemCategory, ItemCategoryOrAll, ItemCategoryUnion
from bot.gameObjects import kaamoShop, lomaShop, guildShop
from bot.gameObjects.items import moduleItemFactory, gameItem
from bot.gameObjects.items.weapons import primaryWeapon, turretWeapon
from bot.gameObjects.items.tools import toolItemFactory, toolItem
from bot.gameObjects.items.modules import moduleItem
from bot.gameObjects.userProfile.medal import Medal
from bot.gameObjects.inventories import inventory, userInventory, inventoryListing
from ..userAlerts import userAlerts
from ..users import basedGuild
from .. import lib, botState
from bot.lib import gameMaths
from bot.lib.discordUtil import userNameIn, findBUserDCGuild
from bot.lib.timeUtil import utcfromtimestamp
from ..logging import LogCategory
from ..reactionMenus import reactionMenu


# Dictionary-serialized shipItem to give to new players
defaultShipLoadoutDict: shipBase.TypedBuiltInSerializedShip = \
{
    "name": "Betty", "type": "Ship", "builtIn": True, "nickname": "", "shipUpgrades": [], "turrets": [],
    "weapons": [{"type": "PrimaryWeapon", "name": "Micro Gun MK I", "builtIn": True}],
    "modules": [{"type": "ScannerModule", "name": "Telta Quickscan", "builtIn": True},
                {"type": "ArmourModule", "name": "E2 Exoclad", "builtIn": True},
                {"type": "MiningDrillModule", "name": "IMT Extract 1.3", "builtIn": True}],
}

itemCategoryUserKeys = {
    ItemCategory.ship: "inactiveShips",
    ItemCategory.weapon: "inactiveWeapons",
    ItemCategory.module: "inactiveModules",
    ItemCategory.turret: "inactiveTurrets",
    ItemCategory.tool: "inactiveTools"
}

itemCategoryStoredTypes: Dict[ItemCategory, Type[gameItem.GameItem]] = {
    ItemCategory.ship: shipItem.Ship,
    ItemCategory.weapon: primaryWeapon.PrimaryWeapon,
    ItemCategory.module: moduleItem.ModuleItem,
    ItemCategory.turret: turretWeapon.TurretWeapon,
    ItemCategory.tool: toolItem.ToolItem
}

StoredInventoryUnion = Union[
    inventory.Inventory[shipItem.Ship, shipBase.SerializedShipUnion],
    inventory.Inventory[moduleItem.ModuleItem, moduleItem.SerializedModuleItemUnion],
    inventory.Inventory[primaryWeapon.PrimaryWeapon, primaryWeapon.SerializedWeaponUnion],
    inventory.Inventory[turretWeapon.TurretWeapon, turretWeapon.SerializedWeaponUnion],
    inventory.Inventory[toolItem.ToolItem, toolItem.SerializedToolItemUnion],
]

SerializedStoredItemUnion = Union[
    shipBase.SerializedShipUnion,
    moduleItem.SerializedModuleItemUnion,
    primaryWeapon.SerializedWeaponUnion,
    turretWeapon.SerializedWeaponUnion,
    toolItem.SerializedToolItemUnion
]

# Default attributes to give to new players
defaultUserDict: "SerializedBasedUser" = \
{
    "credits": 0, "bountyCooldownEnd": 0, "lifetimeBountyCreditsWon": 0, "systemsChecked": 0, "bountyWins": 0,
    "activeShip": defaultShipLoadoutDict, "bountyHuntingXP": gameMaths.bountyHuntingXPForLevel(1),
    "inactiveWeapons": [{"item": {"type": "PrimaryWeapon", "name": "Nirai Impulse EX 1", "builtIn": True}, "count": 1}]
}

# Reference value manually added, not pre-calculated from defaultUserDict. This is not used in the game's code,
# but provides a reference for game design.
defaultUserValue = 28970

TItem = TypeVar("TItem", bound=gameItem.GameItem)

class OwnedMenuType(BasedEnum):
    poll = "poll"


class LeaderBoardStat(Enum):
    credits = "current balance"
    lifetimeBountyCreditsWon = "lifetime credits won from bounties"
    lifetimeBountyHuntingXP = "lifetime bounty hunter xp gained"
    systemsChecked = "systems checked"
    bountyWins = "bounties won"
    prestiges = "prestiges"
    totalValue = "current total value"


def guildHasMemberAndPlayChannel(dcClient: "client.BasedClient", guild: Optional[Guild], otherUserId: int) -> bool:
    return guild is not None and guild.get_member(otherUserId) is not None and dcClient.guildsDB.idExists(guild.id) and dcClient.guildsDB.getGuild(guild.id).hasPlayChannel()


class SerializedBasedUser(TypedDict):
    credits: NotRequired[int]
    lifetimeBountyCreditsWon: NotRequired[int]
    bountyCooldownEnd: NotRequired[float]
    systemsChecked: NotRequired[int]
    bountyWins: NotRequired[int]
    activeShip: shipBase.SerializedShipUnion
    duelWins: NotRequired[int]
    duelLosses: NotRequired[int]
    duelCreditsWins: NotRequired[int]
    bountyHuntingXP: NotRequired[Optional[int]]
    duelCreditsLosses: NotRequired[int]
    homeGuildID: NotRequired[int]
    guildTransferCooldownEnd: NotRequired[float]
    prestiges: NotRequired[int]
    alerts: NotRequired[Dict[str, bool]]
    kaamo: NotRequired[guildShop.SerializedShopBase]
    loma: NotRequired[lomaShop.SerializedLomaShop]
    ownedMenus: NotRequired[Dict[str, List[int]]]
    medals: NotRequired[List[str]]
    classicModeEnabled: NotRequired[bool]
    bountyHuntingXpSurplus: NotRequired[int]
    inactiveShips: NotRequired[List[inventoryListing.SerializedInventoryListing[shipBase.SerializedShipUnion]]]
    inactiveWeapons: NotRequired[List[inventoryListing.SerializedInventoryListing[primaryWeapon.SerializedWeaponUnion]]]
    inactiveModules: NotRequired[List[inventoryListing.SerializedInventoryListing[moduleItem.SerializedModuleItemUnion]]]
    inactiveTurrets: NotRequired[List[inventoryListing.SerializedInventoryListing[turretWeapon.SerializedWeaponUnion]]]
    inactiveTools: NotRequired[List[inventoryListing.SerializedInventoryListing[toolItem.TypedSerializedToolItem]]]


class BasedUser(SerializesToSchema[SerializedBasedUser]):
    """A user of the bot. There is currently no guarantee that user still shares any guilds with the bot,
    though this is planned to change in the future.

    TODO: Consider moving alert methods (e.g setAlertByType) to userAlerts.py

    :var id: The user's unique ID. The same as their unique discord ID.
    :vartype id: int
    :var credits: The amount of credits (currency) this user has
    :vartype credits: int
    :var lifetimeBountyCreditsWon: The total amount of credits this user has earned through hunting bounties
    :vartype lifetimeBountyCreditsWon: int
    :var bountyCooldownEnd: A utc timestamp representing when the user's cmd_check cooldown is due to expire
    :vartype bountyCooldownEnd: float
    :var systemsChecked: The total number of space systems this user has checked
    :vartype systemsChecked: int
    :var bountyWins: The total number of bounties this user has won
    :vartype bountyWins: int
    :var activeShip: The user's currently equipped shipItem
    :vartype activeShip: shipItem
    :var inactiveShips: The shipItems currently in this user's inventory (unequipped)
    :vartype inactiveShips: inventory
    :var inactiveModules: The moduleItems currently in this user's inventory (unequipped)
    :vartype inactiveModules: inventory
    :var inactiveWeapons: The primaryWeapons currently in this user's inventory (unequipped)
    :vartype inactiveWeapons: inventory
    :var inactiveTurrets: The turretWeapons currently in this user's inventory (unequipped)
    :vartype inactiveTurrets: inventory
    :var inactiveTools: the toolItems currently in this user's inventory
    :vartype inactiveTools: userInventory.UserToolInventory
    :var duelRequests: A dictionary mapping target BasedUser objects to DuelRequest objects.
                        Only contains duel requests issued by this user.
    :vartype duelRequests: dict[BasedUser, DuelRequest]
    :var duelWins: The total number of duels the user has won
    :vartype duelWins: int
    :var duelLosses: The total number of duels the user has lost
    :vartype duelLosses: int
    :var duelCreditsWins: The total amount of credits the user has won through fighting duels
    :vartype duelCreditsWins: int
    :var duelCreditsLosses: The total amount of credits the user has lost through fighting duels
    :vartype duelCreditsLosses: int
    :var userAlerts: A dictionary mapping userAlerts.UABase subtypes to instances of that subtype
    :vartype userAlerts: dict[type, userAlerts.UABase]
    :var homeGuildID: The id of this user's 'home guild' - the only guild from which they may use several commands
                        e.g buy and check.
    :vartype homeGuildID: int
    :var guildTransferCooldownEnd: A timestamp after which this user is allowed to transfer their homeGuildID.
    :vartype guildTransferCooldownEnd: datetime.datetime
    :var kaamo: The user's Kaamo Club storage, only accessible at bounty hunter level 10. To save memory,
                this is None until the user first uses it. (default None)
    :vartype kaamo: Union[KaamoShop, None]
    :var loma: A shop private to this user, selling special discountable items. To save memory,
                this is None until the user first uses it. (default None)
    :vartype loma: Union[LomaShop, None]
    :var prestiges: The number of times the user has prestiged
    :vartype prestiges: int
    :var ownedMenus: Sets of IDs for all menus that user owns, by IDs.
    :vartype ownedMenus: Dict[OwnedMenuType, MutableSet[int]]
    :var medals: References to all medals awareded to this user
    :vartype medals: MutableSet[Medal]
    :var classicModeEnabled: Whether or not this user is set to use classic mode
    :vartype classicModeEnabled: bool
    :var bountyHuntingXpSurplus: Extra experience to be awarded to the user when they choose to div-up
    :vartype bountyHuntingXpSurplus: int
    """

    def __init__(self, userID: int, activeShip: shipItem.Ship, credits: int = 0, lifetimeBountyCreditsWon: int = 0,
                    bountyHuntingXP: int = gameMaths.bountyHuntingXPForLevel(1), bountyCooldownEnd: float = -1.0,
                    systemsChecked: int = 0, bountyWins: int = 0,
                    inactiveShips: Optional[inventory.Inventory[shipItem.Ship, shipBase.SerializedShipUnion]] = None,
                    inactiveModules: Optional[inventory.Inventory[moduleItem.ModuleItem, moduleItem.SerializedModuleItemUnion]] = None,
                    inactiveWeapons: Optional[inventory.Inventory[primaryWeapon.PrimaryWeapon, primaryWeapon.SerializedWeaponUnion]] = None,
                    inactiveTurrets: Optional[inventory.Inventory[turretWeapon.TurretWeapon, turretWeapon.SerializedWeaponUnion]] = None,
                    inactiveTools: Optional[userInventory.UserToolInventory[toolItem.ToolItem, toolItem.SerializedToolItemUnion]] = None,
                    duelWins: int = 0, duelLosses: int = 0, duelCreditsWins: int = 0,
                    duelCreditsLosses: int = 0, alerts: Dict[Union[Type[userAlerts.UABase], str], Union[userAlerts.UABase, bool]] = {},
                    homeGuildID: int = -1, guildTransferCooldownEnd: Optional[datetime] = None, prestiges: int = 0,
                    kaamo: Union[kaamoShop.KaamoShop, None] = None, loma: Union[lomaShop.LomaShop, None] = None,
                    ownedMenus: Dict[OwnedMenuType, MutableSet[int]] = {}, medals: Optional[MutableSet[Medal]] = None,
                    classicModeEnabled: bool = False, bountyHuntingXpSurplus: int = -1):
        """
        :param int id: The user's unique ID. The same as their unique discord ID.
        :param int credits: The amount of credits (currency) this user has (Default 0)
        :param int lifetimeBountyCreditsWon: The total amount of credits this user has earned through hunting bounties
                                            (Default 0)
        :param int bountyHuntingXP: The amount of XP this user has gained through bounty hunting (Default level 1)
        :param float bountyCooldownEnd: A utc timestamp representing when the user's cmd_check cooldown is due to expire
                                        (Default -1)
        :param int systemsChecked: The total number of space systems this user has checked (Default 0)
        :param int bountyWins: The total number of bounties this user has won (Default 0)
        :param shipItem activeShip: The user's currently equipped shipItem (Default None)
        :param inventory inactiveShips: The shipItems currently in this user's inventory (unequipped)
                                        (Default empty inventory)
        :param inventory inactiveModules: The moduleItems currently in this user's inventory (unequipped)
                                            (Default empty inventory)
        :param inventory inactiveWeapons: The primaryWeapons currently in this user's inventory (unequipped)
                                            (Default empty inventory)
        :param userInventory.UserToolInventory inactiveTurrets: The turretWeapons currently in this user's inventory (unequipped)
                                            (Default empty inventory)
        :param inventory inactiveTools: The toolItems currently in this user's inventory (Default empty inventory)
        :param int duelWins: The total number of duels the user has won (Default 0)
        :param int duelLosses: The total number of duels the user has lost (Default 0)
        :param int duelCreditsWins: The total amount of credits the user has won through fighting duels (Default 0)
        :param int duelCreditsLosses: The total amount of credits the user has lost through fighting duels (Default 0)
        :param alerts: A dictionary mapping either (userAlerts.UABase subtypes or string UA ids from
                        userAlerts.userAlertsIDsTypes) to either (instances of that subtype or booleans
                        representing the alert state) (Default {})
        :type alerts: dict[type or str, userAlerts.UABase or bool]
        :param Guild homeGuildID: The ID of this user's 'home guild' - the only guild from which they may use several
                                    commands e.g buy and check.
        :param datetime.datetime guildTransferCooldownEnd: A timestamp after which this user is allowed to transfer
                                                            their homeGuildID.
        :raise TypeError: When given an argument of incorrect type
        :param kaamo: The user's Kaamo Club storage, only accessible at bounty hunter level 10. To save memory,
                        this is None until the user first uses it. (default None)
        :type kaamo: Union[KaamoShop, None]
        :param loma: A shop private to this user, selling special discountable items. To save memory,
                        this is None until the user first uses it. (default None)
        :type loma: Union[LomaShop, None]
        :param int prestiges: The number of times the user has prestiged (default 0)
        :param ownedMenus: Sets of IDs for all menus that user owns, by IDs. (default {})
        :type ownedMenus: Dict[OwnedMenuType, MutableSet[int]]
        :param MutableSet[Medal] medals: References to all medals awareded to this user (Default [])
        :param bool classicModeEnabled: Whether this user has classic mode enabled (Default False)
        :param int bountyHuntingXpSurplus: Extra experience to be awarded to the user when they choose to div-up (Default -1)
        """
        if type(userID) == float:
            userID = int(userID)
        elif type(userID) != int:
            raise TypeError("id must be int, given " + str(type(userID)))

        if type(credits) == float:
            credits = int(credits)
        elif type(credits) != int:
            raise TypeError("credits must be int, given " + str(type(credits)))

        if type(lifetimeBountyCreditsWon) == float:
            lifetimeBountyCreditsWon = int(lifetimeBountyCreditsWon)
        elif type(lifetimeBountyCreditsWon) != int:
            raise TypeError("lifetimeBountyCreditsWon must be int, given " + str(type(lifetimeBountyCreditsWon)))

        if type(bountyCooldownEnd) == int:
            bountyCooldownEnd = float(bountyCooldownEnd)
        if type(bountyCooldownEnd) != float:
            raise TypeError("bountyCooldownEnd must be float, given " + str(type(bountyCooldownEnd)))

        if type(systemsChecked) == float:
            systemsChecked = int(systemsChecked)
        elif type(systemsChecked) != int:
            raise TypeError("systemsChecked must be int, given " + str(type(systemsChecked)))

        if type(bountyWins) == float:
            bountyWins = int(bountyWins)
        elif type(bountyWins) != int:
            raise TypeError("bountyWins must be int, given " + str(type(bountyWins)))

        if guildTransferCooldownEnd is None:
            guildTransferCooldownEnd = utcnow()

        self.githubIssueSubmitDelayEnd: Union[timedelta, None] = None
        self.classicModeEnabled = classicModeEnabled

        self.id = userID
        self.credits = credits
        self.lifetimeBountyCreditsWon = lifetimeBountyCreditsWon
        # TODO: Should probably change this to a datetime, like guildTransferCooldownEnd etc
        self.bountyCooldownEnd = bountyCooldownEnd
        self.systemsChecked = systemsChecked
        self.bountyWins = bountyWins

        self.activeShip = activeShip
        self.inactiveShips = inactiveShips if inactiveShips is not None else \
                                inventory.Inventory(shipItem.Ship)
        self.inactiveModules = inactiveModules if inactiveModules is not None else \
                                inventory.Inventory(moduleItem.ModuleItem)
        self.inactiveWeapons = inactiveWeapons if inactiveWeapons is not None else \
                                inventory.Inventory(primaryWeapon.PrimaryWeapon)
        self.inactiveTurrets = inactiveTurrets if inactiveTurrets is not None else \
                                inventory.Inventory(turretWeapon.TurretWeapon)
        self.inactiveTools = inactiveTools if inactiveTools is not None else \
                                userInventory.UserToolInventory(self)

        # TODO: should probably be user IDs instead
        self.duelRequests: Dict[BasedUser, duelRequest.DuelRequest] = {}
        self.duelWins = duelWins
        self.duelLosses = duelLosses

        self.duelCreditsWins = duelCreditsWins
        self.duelCreditsLosses = duelCreditsLosses

        self.userAlerts: Dict[Type[userAlerts.UABase], userAlerts.UABase] = {}
        # Convert the given user alerts to types and instances. The given alerts may be IDs instead of types,
        # or booleans instead of instances.
        for alertID in userAlerts.userAlertsIDsTypes:
            alertType = userAlerts.userAlertsIDsTypes[alertID]
            
            if alertType in alerts:
                alertValue = alerts[alertType]

                if isinstance(alertValue, userAlerts.UABase):
                    self.userAlerts[alertType] = alertValue
                elif isinstance(alertValue, bool):
                    # I've just checked that this is a bool!
                    self.userAlerts[alertType] = alertType(alertValue) # type: ignore[reportGeneralTypeIssues]
                else:
                    botState.client.logger.log("bbUsr", "init", "Given unknown alert state type for UA " + alertID \
                        + ". Must be either UABase or bool, given " + type(alertValue).__name__ \
                        + ". Alert reset to default (" + str(alertType(cfg.userAlertsIDsDefaults[alertID])) + ")",
                        category=LogCategory.usersDB, eventType="LOAD-UA_STATE_TYPE")
                    self.userAlerts[alertType] = alertType(cfg.userAlertsIDsDefaults[alertID])
            elif alertID in alerts:
                alertValue = alerts[alertID]
                if isinstance(alertValue, userAlerts.UABase):
                    self.userAlerts[alertType] = alertValue
                elif isinstance(alertValue, bool):
                    # I've just checked that this is a bool!
                    self.userAlerts[alertType] = alertType(alertValue) # type: ignore[reportGeneralTypeIssues]
                else:
                    botState.client.logger.log("bbUsr", "init", "Given unknown alert state type for UA " + alertID \
                        + ". Must be either UABase or bool, given " + type(alertValue).__name__ \
                        + ". Alert reset to default (" + str(alertType(cfg.userAlertsIDsDefaults[alertID])) + ")",
                        category=LogCategory.usersDB, eventType="LOAD-UA_STATE_TYPE")
                    self.userAlerts[alertType] = alertType(cfg.userAlertsIDsDefaults[alertID])
            else:
                self.userAlerts[alertType] = alertType(cfg.userAlertsIDsDefaults[alertID])

        if classicModeEnabled:
            self.bountyHuntingXP = None
            
        else:
            self.bountyHuntingXP = bountyHuntingXP

        self.prestiges = prestiges

        self.homeGuildID = homeGuildID
        self.guildTransferCooldownEnd = guildTransferCooldownEnd

        self.kaamo = kaamo
        self.loma = loma
        self.ownedMenus = ownedMenus
        self.medals = medals if medals is not None else set()
        self.bountyHuntingXpSurplus = bountyHuntingXpSurplus


    def resetUser(self):
        """Reset the user's attributes back to their default values.
        """
        self.classicModeEnabled = False
        self.credits = 0
        self.lifetimeBountyCreditsWon = 0
        self.bountyCooldownEnd = -1.0
        self.systemsChecked = 0
        self.bountyWins = 0
        self.activeShip = shipItem.Ship.deserialize(defaultShipLoadoutDict)
        self.inactiveModules.clear()
        self.inactiveShips.clear()
        self.inactiveWeapons.clear()
        self.inactiveTurrets.clear()
        self.inactiveTools.clear()
        self.duelWins = 0
        self.duelLosses = 0
        self.duelCreditsWins = 0
        self.duelCreditsLosses = 0
        self.bountyHuntingXP = gameMaths.bountyHuntingXPForLevel(1)
        self.bountyHuntingXpSurplus = -1
        self.homeGuildID = -1
        self.guildTransferCooldownEnd = utcnow()
        self.kaamo = None
        self.loma = None
        self.prestiges = 0


    def numInventoryPages(self, itemType: ItemCategoryUnion, maxPerPage: int) -> int:
        """Get the number of pages required to display all of the user's unequipped items of the named type,
        displaying the given number of items per page

        :param str item: The name of the item type whose inventory pages to calculate
        :param int maxPerPage: The maximum number of items that may be present on a single page of items (TODO: Add a default)
        :return: The number of pages of size maxPerPage needed to display all of the user's inactive items of the named type
        :rtype: int
        :raise ValueError: When requesting an invalid item type
        :raise NotImplementedError: When requesting a valid item type, but one that is not yet implemented (e.g commodity)
        """
        numWeapons = self.inactiveWeapons.numKeys
        numModules = self.inactiveModules.numKeys
        numTurrets = self.inactiveTurrets.numKeys
        numShips = self.inactiveShips.numKeys
        numTools = self.inactiveTools.numKeys

        itemsNum = 0

        if itemType is ItemCategoryOrAll.all:
            itemsNum = max(numWeapons, numModules, numTurrets, numShips, numTools)
        else:
            noAll = itemType if isinstance(itemType, ItemCategory) else itemType.noAll()
            if noAll is ItemCategory.module:
                itemsNum = numModules
            elif noAll is ItemCategory.weapon:
                itemsNum = numWeapons
            elif noAll is ItemCategory.turret:
                itemsNum = numTurrets
            elif noAll is ItemCategory.ship:
                itemsNum = numShips
            elif noAll is ItemCategory.tool:
                itemsNum = numTools
            else:
                raise NotImplementedError("Unsupported item name: " + noAll.value)

        return int(itemsNum / maxPerPage) + (0 if itemsNum % maxPerPage == 0 else 1)


    def lastItemNumberOnPage(self, item: ItemCategory, pageNum: int, maxPerPage: int) -> int:
        """Get index of the last item on the given page number, where page numbers are of size maxPerPage.
        This is an absolute index from the start of the inventory, not a relative index from the start of the page.

        :param str item: The name of the item type whose last index to calculate
        :param int maxPerPage: The maximum number of items that may be present on a single page of items (TODO: Add a default)
        :return: The index of the last item on page pageNum, where page numbers are of size maxPerPage
        :rtype: int
        :raise ValueError: When requesting an invalid item type
        :raise NotImplementedError: When requesting a valid item type, but one that is not yet implemented (e.g commodity)
        """
        if pageNum < self.numInventoryPages(item, maxPerPage):
            return pageNum * maxPerPage

        elif item is ItemCategory.ship:
            return self.inactiveShips.numKeys
        elif item is ItemCategory.weapon:
            return self.inactiveWeapons.numKeys
        elif item is ItemCategory.module:
            return self.inactiveModules.numKeys
        elif item is ItemCategory.turret:
            return self.inactiveTurrets.numKeys
        elif item is ItemCategory.tool:
            return self.inactiveTools.numKeys
        else:
            raise NotImplementedError("unsupported item name: " + item.value)


    def unequipAll(self, ship: shipItem.Ship) -> int:
        """Unequip all items from the given shipItem, and move them into the user's inactive items ('hangar')
        The user must own ship.

        :param shipItem ship: the ship whose items to transfer to storage
        :returns: The number of items that were unequipped
        :raise TypeError: When given any other type than shipItem
        :raise RuntimeError: when given a shipItem that is not owned by this user
        """
        if not type(ship) == shipItem.Ship:
            raise TypeError("Can only unequipAll from a shipItem. Given " + str(type(ship)))

        if not self.ownsShip(ship):
            raise RuntimeError("Attempted to unequipAll on a ship that isnt owned by this BasedUser")

        itemsUnequipped = len(ship.weapons) + len(ship.modules) + len(ship.turrets)

        for weapon in ship.weapons:
            self.inactiveWeapons.addItem(weapon)
        ship.clearWeapons()

        for module in ship.modules:
            self.inactiveModules.addItem(module)
        ship.clearModules()

        for turret in ship.turrets:
            self.inactiveTurrets.addItem(turret)
        ship.clearTurrets()

        return itemsUnequipped


    def validateLoadout(self):
        """Ensure that the user's active loadout complies with moduleItemFactory.maxModuleTypeEquips
        This method was written as a transferal measure when maxModuleTypeEquips was first released, and should seldom be used
        """
        incompatibleModules = []

        for currentModule in self.activeShip.modules:
            if not self.activeShip.canEquipModuleType(type(currentModule)):
                incompatibleModules.append(currentModule)
                self.activeShip.unequipModuleObj(currentModule)

        finalModules = []
        for currentModule in incompatibleModules:
            if self.activeShip.canEquipModuleType(type(currentModule)):
                self.activeShip.equipModule(currentModule)
            else:
                finalModules.append(currentModule)

        for currentModule in finalModules:
            self.inactiveModules.addItem(currentModule)


    def ownsShip(self, ship: shipItem.Ship):
        """Decide whether or not this user owns the given shipItem.

        :param shipItem ship: The ship to test for ownership
        :return: True if ship is either equipped or in this user's hanger. False otherwise
        :rtype: bool
        """
        return self.activeShip is ship or ship in self.inactiveShips


    def equipShipObj(self, ship: shipItem.Ship, noSaveActive: bool = False):
        """Equip the given ship, replacing the active ship.
        Give noSaveActive=True to delete the currently equipped ship.

        :param shipItem ship: The ship to equip. Must be owned by this user
        :param bool noSaveActive: Give True to delete the currently equipped ship. Give False to move the active ship
                                    to the hangar. (Default False)
        :raise RuntimeError: When given a shipItem that is not owned by this user
        """
        if not self.ownsShip(ship):
            raise RuntimeError("Attempted to equip a ship that isnt owned by this BasedUser")
        if not noSaveActive and self.activeShip is not None:
            self.inactiveShips.addItem(self.activeShip)
        if ship in self.inactiveShips:
            self.inactiveShips.removeItem(ship)
        self.activeShip = ship


    def equipShipIndex(self, index: int):
        """Equip the ship at the given index in the user's inactive ships

        :param int index: The index from the user's inactive ships of the requested ship
        :raise IndexError: When given an index that is out of range of the user's inactive ships
        """
        if not (0 <= index <= self.inactiveShips.numKeys - 1):
            raise IndexError("Index out of range")
        if self.activeShip is not None:
            self.inactiveShips.addItem(self.activeShip)
        self.activeShip = self.inactiveShips.itemAtIndex(index)
        self.inactiveShips.removeItem(self.activeShip)


    def serialize(self, **kwargs) -> SerializedBasedUser:
        """Serialize this BasedUser to a dictionary representation for saving to file.

        :return: A dictionary containing all information needed to recreate this user
        :rtype: dict
        """
        data: SerializedBasedUser = {"credits": self.credits, "lifetimeBountyCreditsWon": self.lifetimeBountyCreditsWon,
                "bountyCooldownEnd": self.bountyCooldownEnd, "systemsChecked": self.systemsChecked,
                "bountyWins": self.bountyWins, "activeShip": self.activeShip.serialize(**kwargs),
                "duelWins": self.duelWins, "duelLosses": self.duelLosses,
                "duelCreditsWins": self.duelCreditsWins, "bountyHuntingXP": self.bountyHuntingXP,
                "duelCreditsLosses": self.duelCreditsLosses, "homeGuildID": self.homeGuildID,
                "guildTransferCooldownEnd": self.guildTransferCooldownEnd.timestamp(), "prestiges": self.prestiges,
                "alerts": {}, "inactiveShips": [], "inactiveWeapons": [], "inactiveModules": [], "inactiveTools": [], "inactiveTurrets": []}

        data["inactiveShips"] = self.inactiveShips.serialize(**kwargs)["items"]
        data["inactiveModules"] = self.inactiveModules.serialize(**kwargs)["items"]
        data["inactiveWeapons"] = self.inactiveWeapons.serialize(**kwargs)["items"]
        data["inactiveTurrets"] = self.inactiveTurrets.serialize(**kwargs)["items"]

        if "saveType" not in kwargs:
            data[itemCategoryUserKeys[ItemCategory.tool]] = self.inactiveTools.serialize(saveType=True, **kwargs)["items"]
        else:
            data[itemCategoryUserKeys[ItemCategory.tool]] = self.inactiveTools.serialize(**kwargs)["items"]

        data["alerts"] = {}
        for alertType, alertValue in self.userAlerts.items():
            if isinstance(alertValue, userAlerts.StateUserAlert):
                data["alerts"][userAlerts.userAlertsTypesIDs[alertType]] = alertValue.state

        if self.kaamo is not None:
            data["kaamo"] = self.kaamo.serialize(**kwargs)
        if self.loma is not None:
            data["loma"] = self.loma.serialize(**kwargs)

        if len(self.ownedMenus) > 0:
            data["ownedMenus"] = {}
            for menuTypeID in self.ownedMenus:
                if self.ownedMenus[menuTypeID]:
                    data["ownedMenus"][menuTypeID.value] = []
                    for menuID in self.ownedMenus[menuTypeID]:
                        if menuID in botState.client.reactionMenusDB \
                                and reactionMenu.isSaveableMenuInstance(botState.client.reactionMenusDB[menuID]):
                            data["ownedMenus"][menuTypeID.value].append(menuID)
        
        if self.medals:
            for m in [i for i in self.medals if i.name.lower() not in bbData.medalObjs]:
                self.medals.remove(m)
            data["medals"] = [m.name.lower() for m in self.medals]

        if self.classicModeEnabled:
            data["classicModeEnabled"] = True

        if self.bountyHuntingXpSurplus != -1:
            data["bountyHuntingXpSurplus"] = self.bountyHuntingXpSurplus

        return data


    def userDump(self) -> str:
        """Get a string containing key information about the user.

        :return: A string containing the user ID, credits, lifetimeBountyCreditsWon, bountyCooldownEnd, systemsChecked and bountyWins
        :rtype: str
        """
        data = "BasedUser #" + str(self.id) + ": "
        for att in [self.credits, self.lifetimeBountyCreditsWon, self.bountyCooldownEnd, self.systemsChecked, self.bountyWins]:
            data += str(att) + "/"
        return data[:-1]


    def getTotalValue(self) -> int:
        modulesValue = 0
        for module in self.inactiveModules.keys:
            modulesValue += self.inactiveModules.items[module].count * module.getValue()
        turretsValue = 0
        for turret in self.inactiveTurrets.keys:
            turretsValue += self.inactiveTurrets.items[turret].count * turret.getValue()
        weaponsValue = 0
        for weapon in self.inactiveWeapons.keys:
            weaponsValue += self.inactiveWeapons.items[weapon].count * weapon.getValue()
        shipsValue = 0
        for ship in self.inactiveShips.keys:
            shipsValue += self.inactiveShips.items[ship].count * ship.getValue()
        toolsValue = 0
        for tool in self.inactiveTools.keys:
            toolsValue += self.inactiveTools.items[tool].count * tool.getValue()

        return modulesValue + turretsValue + weaponsValue + shipsValue + self.activeShip.getValue() + self.credits


    def getStatByName(self, stat: str) -> Union[int, float]:
        """Get a user attribute by its string name. This method is primarily used in leaderboard generation.

        :param str stat: One of id, credits, lifetimeBountyCreditsWon, bountyCooldownEnd, systemsChecked, bountyWins or value
        :return: The requested user attribute
        :rtype: int or float
        :raise ValueError: When given an invalid stat name
        """
        if stat == "id":
            return self.id
        elif stat == "credits":
            return self.credits
        elif stat == "lifetimeBountyCreditsWon":
            return self.lifetimeBountyCreditsWon
        elif stat == "lifetimeBountyHuntingXP":
            # Casting here because bountyHuntingXP is guaranteed if classic mode is disabled
            return (0 if self.classicModeEnabled else cast(int, self.bountyHuntingXP)) \
                    + self.prestiges * gameMaths.bountyHuntingXPForLevel(cfg.maxTechLevel)
        elif stat == "bountyCooldownEnd":
            return self.bountyCooldownEnd
        elif stat == "systemsChecked":
            return self.systemsChecked
        elif stat == "bountyWins":
            return self.bountyWins
        elif stat == "prestiges":
            return self.prestiges
        elif stat == "value":
            return self.getTotalValue()
        else:
            raise ValueError("Unknown stat name: " + str(stat))


    def getStat(self, stat: LeaderBoardStat) -> Union[int, float]:
        """Get a user attribute. This method is primarily used in leaderboard generation.

        :param str stat: The stat
        :return: The requested user attribute
        :rtype: int or float
        """
        if stat is LeaderBoardStat.credits:
            return self.credits
        elif stat is LeaderBoardStat.lifetimeBountyCreditsWon:
            return self.lifetimeBountyCreditsWon
        elif stat is LeaderBoardStat.lifetimeBountyHuntingXP:
            # Casting here because bountyHuntingXP is guaranteed if classic mode is disabled
            return (0 if self.classicModeEnabled else cast(int, self.bountyHuntingXP)) \
                    + self.prestiges * gameMaths.bountyHuntingXPForLevel(cfg.maxTechLevel)
        elif stat is LeaderBoardStat.systemsChecked:
            return self.systemsChecked
        elif stat is LeaderBoardStat.bountyWins:
            return self.bountyWins
        elif stat is LeaderBoardStat.prestiges:
            return self.prestiges
        elif stat is LeaderBoardStat.totalValue:
            return self.getTotalValue()
        else:
            raise ValueError("Unsupported stat: " + str(stat))


    def getInventory(self, itemType: ItemCategory):
        """Get the all of the user's inactive (hangar) items of the given type.
        The given inventory is mutable, and can alter the contents of the user's inventory.

        :param ItemCategory itemType: The item type whose inventory to get
        :return: A inventory containing all of the user's inactive items of the named type.
        :rtype: inventory
        :raise NotImplementedError: When requesting a valid item type name but one that is not yet implemented (e.g commodity)
        """
        if itemType == ItemCategory.ship:
            return self.inactiveShips
        if itemType == ItemCategory.weapon:
            return self.inactiveWeapons
        if itemType == ItemCategory.module:
            return self.inactiveModules
        if itemType == ItemCategory.turret:
            return self.inactiveTurrets
        if itemType == ItemCategory.tool:
            return self.inactiveTools
        raise NotImplementedError("Unrecognised item type: " + itemType)


    def hasDuelChallengeFor(self, targetBasedUser: BasedUser) -> bool:
        """Decide whether or not this user has an active duel request targetted at the given BasedUser

        :param BasedUser targetBasedUser: The user to check for duel request existence
        :return: True if this user has sent a duel request to the given user, and it is still active. False otherwise
        :rtype: bool
        """
        return targetBasedUser in self.duelRequests


    def addDuelChallenge(self, duelReq: duelRequest.DuelRequest):
        """Store a new duel request from this user to another.
        The duel request must still be active (TODO: Add validation), the source user must be this user,
        the target user must not be this user, and this user must not already have a duel challenge for the target user.

        :param DuelRequest duelReq: The duel request to store
        :raise ValueError: When given a duel request where either: This is not the source user, this is the target user,
                            or a duel request is already stored for the target user (TODO: Move to separate exception types)
        """
        if duelReq.sourceBasedUser is not self:
            raise ValueError("Attempted to add a DuelRequest for a different source user: " + str(duelReq.sourceBasedUser.id))
        if self.hasDuelChallengeFor(duelReq.targetBasedUser):
            raise ValueError("Attempted to add a DuelRequest for an already challenged user: " \
                                + str(duelReq.sourceBasedUser.id))
        if duelReq.targetBasedUser is self:
            raise ValueError("Attempted to add a DuelRequest for self: " + str(duelReq.sourceBasedUser.id))
        self.duelRequests[duelReq.targetBasedUser] = duelReq


    def removeDuelChallengeObj(self, duelReq: duelRequest.DuelRequest):
        """Remove the given duel request object from this user's storage.

        :param DuelRequest duelReq: The DuelRequest to remove
        :raise ValueError: When given a duel request that this user object is unaware of
        """
        if (duelReq.targetBasedUser not in self.duelRequests) or (self.duelRequests[duelReq.targetBasedUser] is not duelReq):
            raise ValueError("Duel request not found: " + str(duelReq.sourceBasedUser.id) + " -> " \
                                + str(duelReq.sourceBasedUser.id))
        del self.duelRequests[duelReq.targetBasedUser]


    def removeDuelChallengeTarget(self, duelTarget: BasedUser):
        """Remove this user's duel request that is targetted at the given user.

        :param BasedUser duelTarget: The target user whose duel request to remove
        """
        self.removeDuelChallengeObj(self.duelRequests[duelTarget])


    async def setAlertByType(self, alertType: Type[userAlerts.UABase], dcGuild: Guild, bbGuild: basedGuild.BasedGuild, dcMember: Member,
            newState: bool) -> bool:
        """Set the state of one of this users's userAlerts, identifying the alert by its class.

        :param type alertType: The class of the alert whose state to set. Must be a subclass of userAlerts.UABase
        :param discord.Guild dcGuild: The discord guild in which to set the alert state
                                        (currently only relevent for role-based alerts)
        :param bbGuild bbGuild: The bbGuild in which to set the alert state (currently only relevent for role-based alerts,
                                as the role must be looked up)
        :param discord.Member dcMember: This user's member object in dcGuild (TODO: Just grab dcMember from dcGuild in here)
        :param bool newState: The new desired of the alert
        """
        await self.userAlerts[alertType].setState(dcGuild, bbGuild, dcMember, newState)
        return newState


    async def setAlertByID(self, alertID: str, dcGuild: Guild, bbGuild: basedGuild.BasedGuild, dcMember: Member,
                            newState) -> bool:
        """Set the state of one of this users's userAlerts, identifying the alert by its ID as given by
        userAlerts.userAlertsIDsTypes.

        :param str alertID: The ID of the user alert type, as given by userAlerts.userAlertsIDsTypes
        :param discord.Guild dcGuild: The discord guild in which to set the alert state
                                        (currently only relevent for role-based alerts)
        :param bbGuild bbGuild: The bbGuild in which to set the alert state (currently only relevent for role-based alerts,
                                as the role must be looked up)
        :param discord.Member dcMember: This user's member object in dcGuild (TODO: Just grab dcMember from dcGuild in here)
        :param bool newState: The new desired of the alert
        """
        return await self.setAlertByType(userAlerts.userAlertsIDsTypes[alertID], dcGuild, bbGuild, dcMember, newState)


    async def toggleAlertType(self, alertType: Type[userAlerts.UABase], dcGuild: Guild, bbGuild: basedGuild.BasedGuild,
            dcMember: Member) -> bool:
        """Toggle the state of one of this users's userAlerts, identifying the alert by its class.

        :param type alertType: The class of the alert whose state to toggle. Must be a subclass of userAlerts.UABase
        :param discord.Guild dcGuild: The discord guild in which to toggle the alert state
                                        (currently only relevent for role-based alerts)
        :param bbGuild bbGuild: The bbGuild in which to toggle the alert state (currently only relevent for role-based
                                alerts, as the role must be looked up)
        :param discord.Member dcMember: This user's member object in dcGuild (TODO: Just grab dcMember from dcGuild in here)
        """
        return await self.userAlerts[alertType].toggle(dcGuild, bbGuild, dcMember)


    async def toggleAlertID(self, alertID: str, dcGuild: Guild, bbGuild: basedGuild.BasedGuild, dcMember: Member) -> bool:
        """Toggle the state of one of this users's userAlerts, identifying the alert by its ID as given by
        userAlerts.userAlertsIDsTypes.

        :param str alertID: The ID of the user alert type, as given by userAlerts.userAlertsIDsTypes
        :param discord.Guild dcGuild: The discord guild in which to toggle the alert state (currently only relevent for
                                        role-based alerts)
        :param bbGuild bbGuild: The bbGuild in which to toggle the alert state (currently only relevent for role-based alerts,
                                as the role must be looked up)
        :param discord.Member dcMember: This user's member object in dcGuild (TODO: Just grab dcMember from dcGuild in here)
        """
        return await self.toggleAlertType(userAlerts.userAlertsIDsTypes[alertID], dcGuild, bbGuild, dcMember)


    def isAlertedForType(self, alertType: Type[userAlerts.UABase], dcGuild: Guild, bbGuild: basedGuild.BasedGuild, dcMember: Member) -> bool:
        """Get the state of one of this users's userAlerts, identifying the alert by its class.

        :param type alertType: The class of the alert whose state to get. Must be a subclass of userAlerts.UABase
        :param discord.Guild dcGuild: The discord guild in which to get the alert state (currently only relevent for
                                        role-based alerts)
        :param bbGuild bbGuild: The bbGuild in which to get the alert state (currently only relevent for role-based alerts,
                                as the role must be looked up)
        :param discord.Member dcMember: This user's member object in dcGuild (TODO: Just grab dcMember from dcGuild in here)
        """
        return self.userAlerts[alertType].getState(dcGuild, bbGuild, dcMember)


    def isAlertedForID(self, alertID: str, dcGuild: Guild, bbGuild: basedGuild.BasedGuild, dcMember: Member) -> bool:
        """Get the state of one of this user's userAlerts, identifying the alert by its ID as given by
        userAlerts.userAlertsIDsTypes.

        :param str alertID: The ID of the user alert type, as given by userAlerts.userAlertsIDsTypes
        :param discord.Guild dcGuild: The discord guild in which to get the alert state (currently only relevent
                                        for role-based alerts)
        :param bbGuild bbGuild: The bbGuild in which to get the alert state (currently only relevent for role-based alerts,
                                as the role must be looked up)
        :param discord.Member dcMember: This user's member object in dcGuild (TODO: Just grab dcMember from dcGuild in here)
        """
        return self.isAlertedForType(userAlerts.userAlertsIDsTypes[alertID], dcGuild, bbGuild, dcMember)


    def isAlertedForStatefulType(self, alertType: Type[userAlerts.StateUserAlert]) -> bool:
        """Get the state of one of this users's userAlerts, identifying the alert by its class.

        :param type alertType: The class of the alert whose state to get. Must be a subclass of userAlerts.UABase
        :param discord.Guild dcGuild: The discord guild in which to get the alert state (currently only relevent for
                                        role-based alerts)
        :param bbGuild bbGuild: The bbGuild in which to get the alert state (currently only relevent for role-based alerts,
                                as the role must be looked up)
        :param discord.Member dcMember: This user's member object in dcGuild (TODO: Just grab dcMember from dcGuild in here)
        """
        alertValue = self.userAlerts[alertType]
        if not isinstance(alertValue, userAlerts.StateUserAlert):
            raise TypeError(f"{alertType.__name__} is not a {userAlerts.StateUserAlert.__name__} subclass")
        return alertValue.state


    def hasHomeGuild(self) -> bool:
        """Decide whether or not this user has a home guild set.

        :return: True if this user has a home guild, False otherwise
        :rtype: bool
        """
        return self.homeGuildID != -1


    def canTransferGuild(self, now: Optional[datetime] = None) -> bool:
        """Decide whether this user is allowed to transfer their homeGuildID.
        This is decided based on the time passed since their last guild transfer.

        :param datetime.datetime now: The current time, if known. This optional parameter is included for increasing
                                        efficiency in the case where the current time has already been calculated.
        :return: True if this user has no home guild, or their guild transfer cooldown has completed, false otherwise
        :rtype: bool
        """
        if now is None:
            now = utcnow()
        return (not self.hasHomeGuild()) or now > self.guildTransferCooldownEnd


    async def transferGuild(self, newGuild: Guild):
        """Transfer the user's homeGuildID to the given guild.
        The user must not be on guild transfer cooldown.

        :param discord.Guild newGuild: The new discord.Guild to set this user's homeGuildID to.
                                        This user must be a member of newGuild.
        :raise ValueError: When this user is still in guild transfer cooldown
        :raise NameError: When this user is not a member of newGuild
        """
        now = utcnow()
        if not self.canTransferGuild(now=now):
            raise ValueError("This user cannot transfer guild again yet (" \
                                + lib.timeUtil.td_format_noYM(now - self.guildTransferCooldownEnd) + " remaining)")
        if not (newGuild.get_member(self.id) or await newGuild.fetch_member(self.id)):
            raise NameError("This user is not a member of the given guild '" + newGuild.name + "#" + str(newGuild.id) + "'")

        self.homeGuildID = newGuild.id
        self.guildTransferCooldownEnd = now + cfg.timeouts.homeGuildTransferCooldown


    def getInventoryForItem(self, item: TItem) -> inventory.Inventory[TItem, SerializedStoredItemUnion]:
        # Lots of casting going on here - I look for an inventory that stores the given type and returns it.
        # The inventory is guaranteed to be of the right type - just check the revealed type of the returned inventory!
        if isinstance(item, shipItem.Ship):
            return cast(inventory.Inventory[TItem, shipBase.SerializedShipUnion], self.inactiveShips)
        elif isinstance(item, primaryWeapon.PrimaryWeapon):
            return cast(inventory.Inventory[TItem, primaryWeapon.SerializedWeaponUnion], self.inactiveWeapons)
        elif isinstance(item, turretWeapon.TurretWeapon):
            return cast(inventory.Inventory[TItem, turretWeapon.SerializedWeaponUnion], self.inactiveTurrets)
        elif isinstance(item, toolItem.ToolItem):
            return cast(inventory.Inventory[TItem, toolItem.SerializedToolItemUnion], self.inactiveTools)
        elif isinstance(item, moduleItem.ModuleItem):
            return cast(inventory.Inventory[TItem, moduleItem.SerializedModuleItemUnion], self.inactiveModules)
        raise ValueError(f"No inventory is stored for item type {type(item).__name__}")


    def hasMenuOfTypeID(self, menuTypeID: OwnedMenuType) -> bool:
        """Decide whether the user owns a menu of the given menu type.
        The menu type is specified as a string type ID, e.g 'help'.

        :param OwnedMenuType menuTypeID: The ID of the menu type to look up
        :return: True if the user has at least one menu with the given type ID, False otherwise
        :rtype: bool
        """
        return (menuTypeID in self.ownedMenus) and len(self.ownedMenus[menuTypeID]) != 0


    def addOwnedMenu(self, menuTypeID: OwnedMenuType, menu: reactionMenu.ReactionMenu):
        """Add the given menu as 'owned' by the user. This does not prevent claiming by other users.
        The menu type is specified as a string type ID, e.g 'help'.

        :param OwnedMenuType menuTypeID: The ID of the menu type to register menu as
        :param reactionMenu.ReactionMenu menu: The menu to register ownership for
        """
        if menuTypeID not in self.ownedMenus:
            self.ownedMenus[menuTypeID] = set()
        self.ownedMenus[menuTypeID].add(menu.msg.id)

    
    def removeAllOwnedMenusOfTypeID(self, menuTypeID: OwnedMenuType) -> int:
        """Remove ownership of all menus of the given type ID.
        The number of menus removed is returned.
        The menu type is specified as an ID.

        :param OwnedMenuType menuTypeID: The ID of the menu type to clear ownership of
        :return: The number of menus removed from this user's ownership, possibly zero
        :rtype: int
        """
        if menuTypeID not in self.ownedMenus:
            return 0
        menusOwned = len(self.ownedMenus[menuTypeID])
        self.ownedMenus[menuTypeID].clear()
        return menusOwned


    def removeOwnedMenu(self, menuTypeID: Union[str, OwnedMenuType], menu: reactionMenu.ReactionMenu):
        """Remove the given menu as 'owned' by the user.
        The menu type is specified as a type ID.

        :param OwnedMenuType menuTypeID: The ID of the menu type to unregister menu as
        :param reactionMenu.ReactionMenu menu: The menu to unregister ownership for
        """
        if isinstance(menuTypeID, str): menuTypeID = OwnedMenuType(menuTypeID)
        if menuTypeID not in self.ownedMenus:
            raise KeyError(f"No menus owned with type ID '{menuTypeID}'")
        if menu.msg.id not in self.ownedMenus[menuTypeID]:
            raise ValueError(f"{type(menu).__name__} #{menu.msg.id} not registered to this user as '{menuTypeID.value}'")
        self.ownedMenus[menuTypeID].remove(menu.msg.id)
        if not self.ownedMenus[menuTypeID]:
            del self.ownedMenus[menuTypeID]


    def enableClassicMode(self):
        """Enable BountyBot's "classic mode" for this user, which aims to emulate the BountyBot beta.

        :raises ValueError: If classic mode is already enabled for this user
        """
        if self.classicModeEnabled:
            raise ValueError(f"Classic mode is already enabled for this user {self}")
        self.bountyHuntingXP = None
        self.classicModeEnabled = True


    def disableClassicMode(self):
        """Disable BountyBot classic mode for this user.

        :raises ValueError: If classic mode is already disabled for this user
        """
        if not self.classicModeEnabled:
            raise ValueError(f"Classic mode is already disabled for this user {self}")
        self.bountyHuntingXP = gameMaths.bountyHuntingXPForLevel(cfg.minTechLevel)
        self.classicModeEnabled = False


    def canDivUp(self) -> bool:
        """Decide whether this user has enough XP to leave their current division.
        Returns false if the user has classic mode enabled, or has no home guild.
        """
        return not self.classicModeEnabled and self.hasHomeGuild() and self.bountyHuntingXpSurplus != -1


    async def individualNotify(self, client: "client.BasedClient",
            content: Optional[str] = None, *,
            tts: bool = False,
            embed: Embed = MISSING,
            file: File = MISSING,
            stickers: Sequence[Union[GuildSticker, StickerItem]] = MISSING,
            delete_after: float = MISSING,
            nonce: Union[str, int] = MISSING,
            allowed_mentions: AllowedMentions = MISSING,
            reference: Union[Message, MessageReference, PartialMessage] = MISSING,
            mention_author: bool = MISSING,
            view: View = MISSING,
            suppress_embeds: bool = False) -> Optional[Message]:
        """Locate this user in a guild, and send them a notification message.
        If the user can't be found, attempt to send them a DM.

        :param client: discord client used to locate the user
        :type client: client.BasedClient
        :returns: The created message, if this operation was successful. None otherwise
        """
        guild = findBUserDCGuild(self, client=client)
        if guild is None:
            sender = client.get_user(self.id)
        else:
            bGuild = client.guildsDB.getGuild(guild.id) 
            sender = bGuild.getPlayChannel() if bGuild.hasPlayChannel() else None
        
        if sender is None: return None

        try:
            message = await sender.send(content=content, tts=tts,
                                        embed=embed,
                                        file=file,
                                        stickers=stickers,
                                        delete_after=delete_after,
                                        nonce=nonce,
                                        allowed_mentions=allowed_mentions,
                                        reference=reference,
                                        mention_author=mention_author,
                                        view=view,
                                        suppress_embeds=suppress_embeds)
        except HTTPException:
            return None

        return message


    def findSharedGuildWithPlayChannel(self, client: "client.BasedClient", other: Union[BasedUser, User, Member, int]) -> Optional[basedGuild.BasedGuild]:
        """Find a BasedGuild containing both this user and `other`, that has a playChannel set.

        :param client: The client used to look up users and guilds
        :type client: client.BasedClient
        :param other: The other user
        :type other: Union[BasedUser, User, Member, int]
        :return: A guild containing both this user and `other` that has a play channel set, if one could be found. None otherwise.
        :rtype: Optional[basedGuild.BasedGuild]
        """
        otherId = other if isinstance(other, int) else other.id

        # Use home guilds first
        if self.hasHomeGuild() and client.guildsDB.idExists(self.homeGuildID):
            bGuild = client.guildsDB.getGuild(self.homeGuildID)
            if bGuild.hasPlayChannel():
                dcGuild = client.get_guild(self.homeGuildID)
                if dcGuild is not None and dcGuild.get_member(otherId) is not None:
                    return bGuild

        if not isinstance(other, BasedUser) and client.usersDB.idExists(otherId):
            other = client.usersDB.getUser(otherId)
        if isinstance(other, BasedUser) and other.hasHomeGuild() and client.guildsDB.idExists(self.homeGuildID):
            bGuild = client.guildsDB.getGuild(other.homeGuildID)
            if bGuild.hasPlayChannel():
                dcGuild = client.get_guild(other.homeGuildID)
                if dcGuild is not None and dcGuild.get_member(self.id) is not None:
                    return bGuild

        # No home guild match - just use mutual guilds
        dcUser = client.get_user(self.id)
        if dcUser is not None and dcUser.mutual_guilds:
            for guild in dcUser.mutual_guilds:
                if guildHasMemberAndPlayChannel(client, guild, otherId):
                    return client.guildsDB.getGuild(guild.id)
        
        return None

    
    async def tryNotifyTwo(self,
            other: Union[BasedUser, User, Member, int],
            client: "client.BasedClient",
            mentionOther: bool = True,
            requireNotifyMe: bool = False,
            content: Optional[str] = None, *,
            tts: bool = False,
            stickers: Optional[Sequence[Union[GuildSticker, StickerItem]]] = None,
            embed: Optional[Embed] = None,
            file: Optional[File] = None,
            delete_after: Optional[float] = None,
            nonce: Optional[Union[str, int]] = None,
            allowed_mentions: Optional[AllowedMentions] = None,
            reference: Optional[Union[Message, MessageReference, PartialMessage]] = None,
            mention_author: Optional[bool] = None,
            view: Optional[View] = None,
            suppress_embeds: bool = False) -> Tuple[bool, Optional[Message], Optional[Message]]:
        """Locate this user and `other` in guilds, and send them a notification message.
        If a user can't be found, attempt to send them a DM.
        This method exists to avoid sending the same notification message twice, if two users are in the same server.
        `content` should include `{meMention}` and `{otherMention}` templates.

        :param client: discord client used to locate the user
        :type client: client.BasedClient
        :param other: The other user to notify, or their ID
        :type other: Union[BasedUser, User, Member, int]
        :returns: This user's created message followed by `other`'s message. Either can be None if their send failed
        """
        async def send(sendChannel, sendContent) -> Optional[Message]:
            try:
                return await sendChannel.send(content=sendContent, tts=tts,
                                                embed=embed,
                                                file=file,
                                                stickers=stickers,
                                                delete_after=delete_after,
                                                nonce=nonce,
                                                allowed_mentions=allowed_mentions,
                                                reference=reference,
                                                mention_author=mention_author,
                                                view=view,
                                                suppress_embeds=suppress_embeds)
            except HTTPException:
                return None
        
        otherId = other if isinstance(other, int) else other.id

        # If the users share a guild that has a playChannel, just send a single message there
        sharedGuild = self.findSharedGuildWithPlayChannel(client, other)
        if sharedGuild is not None:
            sendContent = None if content is None else content.format(meMention=f"<@{self.id}>", otherMention=f"<@{otherId}>" if mentionOther else userNameIn(client, otherId, client.get_guild(otherId)))
            created = await send(sharedGuild.getPlayChannel(), sendContent)
            return True, created, None


        async def guildSend(guild: Guild, meMention: str, otherMention: str) -> Optional[Message]:
            if client.guildsDB.idExists(guild.id):
                bGuild = client.guildsDB.getGuild(guild.id)
                if bGuild.hasPlayChannel():
                    sendContent = None if content is None else content.format(meMention=meMention, otherMention=otherMention)
                    return await send(bGuild.getPlayChannel(), sendContent)


        async def mutualGuildOrDmSend(user: User, meMention: Callable[[Optional[Guild]], str], otherMention: Callable[[Optional[Guild]], str]) -> Optional[Message]:
            # Try sending to any mutual guild
            for guild in user.mutual_guilds:
                newMessage = await guildSend(guild, meMention(guild), otherMention(guild))
                if newMessage is not None: break

            # Otherwise attempt to DM each user
            sendContent = None if content is None else content.format(meMention=meMention(None), otherMention=otherMention(None))
            return await send(user, sendContent)


        # If each user is in a guild that has a playChannel, send individual messages
        meMessage: Optional[Message] = None
        # Try home guilds first
        if self.hasHomeGuild():
            guild = client.get_guild(self.homeGuildID)
            if guild is not None:
                meMessage = await guildSend(guild, f"<@{self.id}>", userNameIn(client, otherId, guild))
        if meMessage is None:
            user = client.get_user(self.id)
            if user is not None:
                meMention = lambda g: f"<@{self.id}>"
                otherMention = lambda g: userNameIn(client, otherId, g)
                # Otherwise try sending to any mutual guild, or fall back on DM
                meMessage = await mutualGuildOrDmSend(user, meMention, otherMention)

        if meMessage is None and requireNotifyMe:
            raise IndexError("Unable to notify this user")

        # If each user is in a guild that has a playChannel, send individual messages
        otherMessage: Optional[Message] = None
        if not isinstance(other, BasedUser) and client.usersDB.idExists(otherId):
            other = client.usersDB.getUser(otherId)
        # Try home guilds first
        if isinstance(other, BasedUser) and other.hasHomeGuild():
            guild = client.get_guild(other.homeGuildID)
            if guild is not None:
                otherMessage = await guildSend(guild, userNameIn(client, self.id, guild), f"<@{otherId}>" if mentionOther else userNameIn(client, otherId, guild))
        if otherMessage is None:
            user = client.get_user(otherId)
            if user is not None:
                meMention = lambda g: userNameIn(client, self.id, g)
                otherMention = lambda g: f"<@{otherId}>" if mentionOther else userNameIn(client, otherId, guild)
                # Otherwise try sending to any mutual guild, or fall back on DM
                meMessage = await mutualGuildOrDmSend(user, meMention, otherMention)
        
        return False, meMessage, otherMessage


    def __str__(self) -> str:
        """Get a short string summary of this BasedUser. Currently only contains the user ID and home guild ID.

        :return: A string summar of the user, containing the user ID and home guild ID.
        :rtype: str
        """
        return "<BasedUser #" + str(self.id) + ((" @" + str(self.homeGuildID)) if self.hasHomeGuild() else "") + ">"


    @classmethod
    def deserialize(cls, userDict: SerializedBasedUser, **kwargs) -> BasedUser:
        """Construct a new BasedUser object from the given ID and the information in the
        given dictionary - The opposite of BasedUser.serialize

        :param int id: The discord ID of the user
        :param dict userDict: A dictionary containing all information necessary to construct
                                the BasedUser object, other than their ID.
        :return: A BasedUser object as described in userDict
        :rtype: BasedUser
        """
        if "id" not in kwargs:
            raise NameError("Required kwarg not given: id")
        userID = kwargs["id"]

        # Casting here because pyright doesn't know the structure of a serialized baseduser
        activeShip = shipItem.Ship.deserialize(userDict["activeShip"])

        inactiveShips = inventory.Inventory(shipItem.Ship)
        inactiveWeapons = inventory.Inventory(primaryWeapon.PrimaryWeapon)
        inactiveModules = inventory.Inventory(moduleItem.ModuleItem)
        inactiveTurrets = inventory.Inventory(turretWeapon.TurretWeapon)
        inactiveTools = userInventory.UserToolInventory(userInventory.USER_PLACEHOLDER)

        for key, stock, deserializer in ((itemCategoryUserKeys[ItemCategory.ship], inactiveShips, shipItem.Ship),
                                        (itemCategoryUserKeys[ItemCategory.weapon], inactiveWeapons, primaryWeapon.PrimaryWeapon),
                                        (itemCategoryUserKeys[ItemCategory.module], inactiveModules, moduleItemFactory.ModuleItemFactory),
                                        (itemCategoryUserKeys[ItemCategory.turret], inactiveTurrets, turretWeapon.TurretWeapon),
                                        (itemCategoryUserKeys[ItemCategory.tool], inactiveTools, toolItemFactory.ToolItemFactory)):
            if key in userDict:
                # Casting here because pyright doesn't know the structure of a serialized baseduser
                for listingDict in cast(List[dict], userDict[key]):
                # Casting here because I can't convince pyright that the types in the for loop args tuple match up
                    stock.addItem(deserializer.deserialize(listingDict["item"]), # type: ignore[reportGeneralTypeIssues]
                                    quantity=listingDict["count"])

        # Casting here because pyright doesn't know the structure of a serialized baseduser
        lifetimeBountyCreditsWon = cast(int, userDict.get("lifetimeBountyCreditsWon", userDict.get("lifetimeCredits", 0)))

        if "bountyHuntingXP" in userDict:
            bountyHuntingXP = userDict["bountyHuntingXP"]
        else:
            # Roughly predict bounty hunter XP from pre-bountyShips savedata directly from total credits earned from bounties
            if lifetimeBountyCreditsWon == 0:
                bountyHuntingXP = gameMaths.bountyHuntingXPForLevel(1)
            else:
                bountyHuntingXP = int(lifetimeBountyCreditsWon * cfg.bountyRewardToXPGainMult)

        kaamo = kaamoShop.KaamoShop.deserialize(userDict["kaamo"]) if "kaamo" in userDict else None
        loma = lomaShop.LomaShop.deserialize(userDict["loma"]) if "loma" in userDict else None

        # Casting here because pyright doesn't know the structure of a serialized baseduser
        serializedOwnedMenus = userDict.get("ownedMenus", {})
        ownedMenus = {}
        for _menuType in serializedOwnedMenus:
            if OwnedMenuType.hasValue(_menuType):
                menuType = OwnedMenuType(_menuType)
                ownedMenus[menuType] = [menuID for menuID in serializedOwnedMenus[_menuType]]
            else:
                print(f"WARN: Skipping unrecognised owned menu type ID '{_menuType}' for user {userID}")
        
        medals = set()
        if "medals" in userDict and userDict["medals"]:
            # Casting here because pyright doesn't know the structure of a serialized baseduser
            for name in cast(List[str], userDict["medals"]):
                if name in bbData.medalObjs:
                    medals.add(bbData.medalObjs[name])

        kwargIgnores = ("lifetimeBountyCreditsWon", "lifetimeCredits", "pollOwned",
                        "bountyWinsToday", "dailyBountyWinsReset", "lastSeenGuildId")
                        
        # Casting here because pyright doesn't know the structure of a serialized baseduser
        guildTransferCooldownEnd = utcfromtimestamp(cast(int, userDict["guildTransferCooldownEnd"])) \
                                    if "guildTransferCooldownEnd" in userDict else None

        newUser = BasedUser(**cls._makeDefaults(userDict, kwargIgnores,
                                                userID=userID, activeShip=activeShip, inactiveShips=inactiveShips,
                                                inactiveModules=inactiveModules, inactiveWeapons=inactiveWeapons,
                                                inactiveTurrets=inactiveTurrets, inactiveTools=inactiveTools,
                                                bountyHuntingXP=bountyHuntingXP, kaamo=kaamo, loma=loma,
                                                ownedMenus=ownedMenus, lifetimeBountyCreditsWon=lifetimeBountyCreditsWon,
                                                medals=medals, guildTransferCooldownEnd=guildTransferCooldownEnd,
                                                prestiges=userDict.get("prestiges", 0) or 0))

        newUser.inactiveTools.owningBUser = newUser
        return newUser
