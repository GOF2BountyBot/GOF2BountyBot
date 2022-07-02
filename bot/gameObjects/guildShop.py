# Typing imports
from __future__ import annotations
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Type, TypeVar, Union, cast
if TYPE_CHECKING:
    from ..users import basedUser

from ..cfg import bbData, cfg
from .items.shipItem import Ship
from .items.weapons.primaryWeapon import PrimaryWeapon
from .items.weapons.turretWeapon import TurretWeapon
from .items import moduleItemFactory, gameItem
from .items.modules import moduleItem
from .items.tools import toolItem, toolItemFactory
from .inventories.inventory import Inventory, _InventoryBase, TListingType
import random
from .. import botState
from ..lib import gameMaths
from ..logging import LogCategory
from ..baseClasses.serializable import Serializable

StoredItemType = Union[Ship, PrimaryWeapon, moduleItem.ModuleItem, TurretWeapon, toolItem.ToolItem]

class GuildShop(Serializable):
    """A shop containing a selection of items which players can buy.
    Items can be sold to the shop to the shop's inventory and listed for sale.

    :var shipsStock: A inventory containing the shop's stock of ships
    :vartype shipsStock: inventory
    :var weaponsStock: A inventory containing the shop's stock of weapons
    :vartype weaponsStock: inventory
    :var modulesStock: A inventory containing the shop's stock of modules
    :vartype modulesStock: inventory
    :var turretsStock: A inventory containing the shop's stock of turrets
    :vartype turretsStock: inventory
    :var toolsStock: A inventory containing the shop's stock of tools
    :vartype toolsStock: inventory
    """

    def __init__(self, shipsStock: Optional[_InventoryBase[TListingType, Ship]] = None,
                    weaponsStock: Optional[_InventoryBase[TListingType, PrimaryWeapon]] = None,
                    modulesStock: Optional[_InventoryBase[TListingType, moduleItem.ModuleItem]] = None,
                    turretsStock: Optional[_InventoryBase[TListingType, TurretWeapon]] = None,
                    toolsStock: Optional[_InventoryBase[TListingType, toolItem.ToolItem]] = None):
        """
        :param Inventory shipsStock: The shop's current stock of ships (Default empty Inventory)
        :param Inventory weaponsStock: The shop's current stock of weapons (Default empty Inventory)
        :param Inventory modulesStock: The shop's current stock of modules (Default empty Inventory)
        :param Inventory turretsStock: The shop's current stock of turrets (Default empty Inventory)
        :param Inventory toolsStock: The shop's current stock of tools (Default empty Inventory)
        """
        self.shipsStock = shipsStock or Inventory(Ship)
        self.weaponsStock = weaponsStock or Inventory(PrimaryWeapon)
        self.modulesStock = modulesStock or Inventory(moduleItem.ModuleItem)
        self.turretsStock = turretsStock or Inventory(TurretWeapon)
        self.toolsStock = toolsStock or Inventory(toolItem.ToolItem)


    def isEmpty(self) -> bool:
        """Check if all of the shop's inventories are empty.

        :return: True if the shop has no items, False if it has at least one
        """
        return all(stock.isEmpty() for stock in \
            (self.shipsStock, self.weaponsStock, self.modulesStock, self.turretsStock, self.toolsStock))


    def getStockByType(self, itemType: Type[StoredItemType]) -> _InventoryBase:
        """Get the inventory containing all current stock of the given type.
        This object is mutable and can alter the stock of the shop.

        :param type itemType: The class of items to fetch
        :return: The inventory used by the shop to store all stock of the requested type
        :rtype: inventory
        :raise KeyError: When requesting an unknown item type
        """
        if itemType == Ship:
            return self.shipsStock
        elif itemType == PrimaryWeapon:
            return self.weaponsStock
        elif itemType == moduleItem.ModuleItem:
            return self.modulesStock
        elif itemType == TurretWeapon:
            return self.turretsStock
        elif itemType == toolItem.ToolItem:
            return self.toolsStock
        else:
            raise KeyError(f"Unknown item type: {itemType.__name__}")


    def getStockByName(self, item: str) -> _InventoryBase:
        """Get the inventory containing all current stock of the named type.
        This object is mutable and can alter the stock of the shop.

        :param str item: The name of the item type to fetch. Must be one of ship, weapon, module or turret
        :return: The inventory used by the shop to store all stock of the requested type
        :rtype: inventory
        :raise ValueError: When requesting an unknown item type
        :raise NotImplementedError: When requesting a valid item type, but one that is not implemented yet (e.g commodity)
        """
        if item == "all" or item not in cfg.validItemNames:
            raise ValueError("Invalid item type: " + item)
        if item == "ship":
            return self.shipsStock
        if item == "weapon":
            return self.weaponsStock
        if item == "module":
            return self.modulesStock
        if item == "turret":
            return self.turretsStock
        if item == "tool":
            return self.toolsStock
        else:
            raise NotImplementedError("Valid, but unrecognised item type: " + item)


    def userCanAffordItemObj(self, user: basedUser.BasedUser, item: gameItem.GameItem) -> bool:
        """Decide whether a user has enough credits to buy an item

        :param basedUser user: The user whose credits balance to check
        :param gameItem item: The item whose value to check
        :return: True if user's credits balance is greater than or equal to item's value. False otherwise
        :rtype: bool
        """
        return user.credits >= item.getValue()


    ##### SHIP MANAGEMENT #####


    def userCanAffordShipIndex(self, user: basedUser.BasedUser, index: int) -> bool:
        """Decide whether a user can afford to buy a ship from the shop's stock

        :param basedUser user: The user whose credits balance to check
        :param int index: The index of the ship whose value to check, in the shop's ship inventory's array of keys
        :return: True if user can afford to buy ship number index from the shop's stock, false otherwise
        :rtype: bool
        """
        return self.userCanAffordItemObj(user, self.shipsStock[index].item)


    def amountCanAffordShipObj(self, amount: int, ship: Ship) -> bool:
        """Decide whether amount of credits is enough to buy a ship from the shop's stock.
        This is used for checking whether a user would be able to afford a ship, if they sold their active one.

        :param int amount: The amount of credits to check against the ship's value
        :param Ship ship: ship object whose value to check against credits
        :return: True if amount is at least as much as ship's value, false otherwise
        :rtype: bool
        """
        return amount >= ship.getValue()


    def amountCanAffordShipIndex(self, amount: int, index: int) -> bool:
        """Decide whether amount of credits is enough to buy the ship at the given index in the shop's stock.
        This is used for checking whether a user would be able to afford a ship, if they sold their active one.

        :param int amount: The amount of credits to check against the ship's value
        :param int index: The index of the ship whose value to check, in the shop's ship inventory's array of keys
        :return: True if amount is at least as much as the ship's value, false otherwise
        :rtype: bool
        """
        return self.amountCanAffordShipObj(amount, self.shipsStock.itemAtIndex(index))


    def userBuyShipIndex(self, user: basedUser.BasedUser, index: int):
        """Sell the ship at the requested index to the given user,
        removing the appropriate balance of credits and adding the item into the user's inventory.

        :param basedUser user: The user attempting to buy the ship
        :param int index: The index of the requested ship in the shop's ships inventory's array of keys
        """
        self.userBuyShipObj(user, self.shipsStock.itemAtIndex(index))


    def userBuyShipObj(self, user: basedUser.BasedUser, requestedShip: Ship):
        """Sell the given ship to the given user,
        removing the appropriate balance of credits fromt the user and adding the item into the user's inventory.

        :param basedUser user: The user attempting to buy the ship
        :param Ship requestedWeapon: The ship to sell to user
        :raise RuntimeError: If user cannot afford to buy requestedWeapon
        """
        if self.userCanAffordItemObj(user, requestedShip):
            self.shipsStock.removeItem(requestedShip)
            user.credits -= requestedShip.getValue()
            user.inactiveShips.addItem(requestedShip)
        else:
            raise RuntimeError("user " + str(user.id) + " attempted to buy ship " + requestedShip.name \
                                + " but can't afford it: " + str(user.credits) + " < " + str(requestedShip.getValue()))


    def userSellShipObj(self, user: basedUser.BasedUser, ship: Ship):
        """Buy the given ship from the given user,
        adding the appropriate credits to their balance and adding the ship to the shop stock.

        :param basedUser user: The user to buy ship from
        :param Ship weapon: The ship to buy from user
        """
        user.credits += ship.getValue()
        self.shipsStock.addItem(ship)
        user.inactiveShips.removeItem(ship)


    def userSellShipIndex(self, user: basedUser.BasedUser, index: int):
        """Buy the weapon at the given index in the given user's ships inventory,
        adding the appropriate credits to their balance and adding the ship to the shop stock.

        :param basedUser user: The user to buy ship from
        :param int index: The index of the weapon to buy from user, in the user's ships inventory's array of keys
        """
        self.userSellShipObj(user, user.inactiveShips.itemAtIndex(index))


    ##### WEAPON MANAGEMENT #####


    def userCanAffordWeaponIndex(self, user: basedUser.BasedUser, index: int) -> bool:
        """Decide whether a user can afford to buy a weapon from the shop's stock

        :param basedUser user: The user whose credits balance to check
        :param int index: The index of the weapon whose value to check, in the shop's weapon inventory's array of keys
        :return: True if user can afford to buy weapon number index from the shop's stock, false otherwise
        :rtype: bool
        """
        return self.userCanAffordItemObj(user, self.weaponsStock.itemAtIndex(index))


    def userBuyWeaponIndex(self, user: basedUser.BasedUser, index: int):
        """Sell the weapon at the requested index to the given user,
        removing the appropriate balance of credits and adding the item into the user's inventory.

        :param basedUser user: The user attempting to buy the weapon
        :param int index: The index of the requested weapon in the shop's weapons inventory's array of keys
        """
        self.userBuyWeaponObj(user, self.weaponsStock.itemAtIndex(index))


    def userBuyWeaponObj(self, user: basedUser.BasedUser, requestedWeapon: PrimaryWeapon):
        """Sell the given weapon to the given user,
        removing the appropriate balance of credits fromt the user and adding the item into the user's inventory.

        :param basedUser user: The user attempting to buy the weapon
        :param PrimaryWeapon requestedWeapon: The weapon to sell to user
        :raise RuntimeError: If user cannot afford to buy requestedWeapon
        """
        if self.userCanAffordItemObj(user, requestedWeapon):
            self.weaponsStock.removeItem(requestedWeapon)
            user.credits -= requestedWeapon.getValue()
            user.inactiveWeapons.addItem(requestedWeapon)
        else:
            raise RuntimeError(f"user {user.id} attempted to buy weapon {requestedWeapon.name}"
                                f" but can't afford it: {user.credits} < {requestedWeapon.getValue()}")


    def userSellWeaponObj(self, user: basedUser.BasedUser, weapon: PrimaryWeapon):
        """Buy the given weapon from the given user,
        adding the appropriate credits to their balance and adding the weapon to the shop stock.

        :param basedUser user: The user to buy weapon from
        :param PrimaryWeapon weapon: The weapon to buy from user
        """
        user.credits += weapon.getValue()
        self.weaponsStock.addItem(weapon)
        user.inactiveWeapons.removeItem(weapon)


    def userSellWeaponIndex(self, user: basedUser.BasedUser, index: int):
        """Buy the weapon at the given index in the given user's weapons inventory,
        adding the appropriate credits to their balance and adding the weapon to the shop stock.

        :param basedUser user: The user to buy weapon from
        :param int index: The index of the weapon to buy from user, in the user's weapons inventory's array of keys
        """
        self.userSellWeaponObj(user, user.inactiveWeapons.itemAtIndex(index))


    ##### MODULE MANAGEMENT #####


    def userCanAffordModuleIndex(self, user: basedUser.BasedUser, index: int) -> bool:
        """Decide whether a user can afford to buy a module from the shop's stock

        :param basedUser user: The user whose credits balance to check
        :param int index: The index of the module whose value to check, in the shop's module inventory's array of keys
        :return: True if user can afford to buy module number index from the shop's stock, false otherwise
        :rtype: bool
        """
        return self.userCanAffordItemObj(user, self.modulesStock.itemAtIndex(index))


    def userBuyModuleIndex(self, user: basedUser.BasedUser, index: int):
        """Sell the module at the requested index to the given user,
        removing the appropriate balance of credits and adding the item into the user's inventory.

        :param basedUser user: The user attempting to buy the module
        :param int index: The index of the requested module in the shop's modules inventory's array of keys
        """
        self.userBuyModuleObj(user, self.modulesStock.itemAtIndex(index))


    def userBuyModuleObj(self, user: basedUser.BasedUser, requestedModule: moduleItem.ModuleItem):
        """Sell the given module to the given user,
        removing the appropriate balance of credits fromt the user and adding the item into the user's inventory.

        :param basedUser user: The user attempting to buy the module
        :param moduleItem requestedModule: The module to sell to user
        :raise RuntimeError: If user cannot afford to buy requestedModule
        """
        if self.userCanAffordItemObj(user, requestedModule):
            self.modulesStock.removeItem(requestedModule)
            user.credits -= requestedModule.getValue()
            user.inactiveModules.addItem(requestedModule)
        else:
            raise RuntimeError(f"user {user.id} attempted to buy module {requestedModule.name}"
                                + f" but can't afford it: {user.credits} <{requestedModule.getValue()}")


    def userSellModuleObj(self, user: basedUser.BasedUser, module: moduleItem.ModuleItem):
        """Buy the given module from the given user,
        adding the appropriate credits to their balance and adding the module to the shop stock.

        :param basedUser user: The user to buy module from
        :param moduleItem module: The module to buy from user
        """
        user.credits += module.getValue()
        self.modulesStock.addItem(module)
        user.inactiveModules.removeItem(module)


    def userSellModuleIndex(self, user: basedUser.BasedUser, index: int):
        """Buy the module at the given index in the given user's modules inventory,
        adding the appropriate credits to their balance and adding the module to the shop stock.

        :param basedUser user: The user to buy module from
        :param int index: The index of the module to buy from user, in the user's modules inventory's array of keys
        """
        self.userSellModuleObj(user, user.inactiveModules.itemAtIndex(index))


    ##### TURRET MANAGEMENT #####


    def userCanAffordTurretIndex(self, user: basedUser.BasedUser, index: int) -> bool:
        """Decide whether a user can afford to buy a turret from the shop's stock

        :param basedUser user: The user whose credits balance to check
        :param int index: The index of the turret whose value to check, in the shop's turret inventory's array of keys
        :return: True if user can afford to buy turret number index from the shop's stock, false otherwise
        :rtype: bool
        """
        return self.userCanAffordItemObj(user, self.turretsStock.itemAtIndex(index))


    def userBuyTurretIndex(self, user: basedUser.BasedUser, index: int):
        """Sell the turret at the requested index to the given user,
        removing the appropriate balance of credits and adding the item into the user's inventory.

        :param basedUser user: The user attempting to buy the turret
        :param int index: The index of the requested turret in the shop's turrets inventory's array of keys
        """
        self.userBuyTurretObj(user, self.turretsStock.itemAtIndex(index))


    def userBuyTurretObj(self, user: basedUser.BasedUser, requestedTurret: TurretWeapon):
        """Sell the given turret to the given user,
        removing the appropriate balance of credits fromt the user and adding the item into the user's inventory.

        :param basedUser user: The user attempting to buy the turret
        :param TurretWeapon requestedTurret: The turret to sell to user
        :raise RuntimeError: If user cannot afford to buy requestedTurret
        """
        if self.userCanAffordItemObj(user, requestedTurret):
            self.turretsStock.removeItem(requestedTurret)
            user.credits -= requestedTurret.getValue()
            user.inactiveTurrets.addItem(requestedTurret)
        else:
            raise RuntimeError("user " + str(user.id) + " attempted to buy turret " + requestedTurret.name \
                                + " but can't afford it: " + str(user.credits) + " < " + str(requestedTurret.getValue()))


    def userSellTurretObj(self, user: basedUser.BasedUser, turret: TurretWeapon):
        """Buy the given turret from the given user,
        adding the appropriate credits to their balance and adding the turret to the shop stock.

        :param basedUser user: The user to buy turret from
        :param TurretWeapon turret: The turret to buy from user
        """
        user.credits += turret.getValue()
        self.turretsStock.addItem(turret)
        user.inactiveTurrets.removeItem(turret)


    def userSellTurretIndex(self, user: basedUser.BasedUser, index: int):
        """Buy the turret at the given index in the given user's turrets inventory,
        adding the appropriate credits to their balance and adding the turret to the shop stock.

        :param basedUser user: The user to buy turret from
        :param int index: The index of the turret to buy from user, in the user's turrets inventory's array of keys
        """
        self.userSellTurretObj(user, user.inactiveTurrets.itemAtIndex(index))


    ##### TOOL MANAGEMENT #####


    def userCanAffordToolIndex(self, user: basedUser.BasedUser, index: int) -> bool:
        """Decide whether a user can afford to buy a tool from the shop's stock
        :param BasedUser user: The user whose credits balance to check
        :param int index: The index of the tool whose value to check, in the shop's tool Inventory's array of keys
        :return: True if user can afford to buy tool number index from the shop's stock, false otherwise
        :rtype: bool
        """
        return self.userCanAffordItemObj(user, self.toolsStock[index].item)


    def userBuyToolIndex(self, user: basedUser.BasedUser, index: int):
        """Sell the tool at the requested index to the given user,
        removing the appropriate balance of credits and adding the item into the user's inventory.
        :param BasedUser user: The user attempting to buy the tool
        :param int index: The index of the requested tool in the shop's tools Inventory's array of keys
        """
        self.userBuyToolObj(user, self.toolsStock.itemAtIndex(index))


    def userBuyToolObj(self, user: basedUser.BasedUser, requestedTool: toolItem.ToolItem):
        """Sell the given tool to the given user,
        removing the appropriate balance of credits fromt the user and adding the item into the user's inventory.
        :param BasedUser user: The user attempting to buy the tool
        :param ToolItem requestedTool: The tool to sell to user
        :raise RuntimeError: If user cannot afford to buy requestedTool
        """
        if self.userCanAffordItemObj(user, requestedTool):
            self.toolsStock.removeItem(requestedTool)
            user.credits -= requestedTool.getValue()
            user.inactiveTools.addItem(requestedTool)
        else:
            raise RuntimeError("user " + str(user.id) + " attempted to buy tool " + requestedTool.name \
                                + " but can't afford it: " + str(user.credits) + " < " + str(requestedTool.getValue()))


    def userSellToolObj(self, user: basedUser.BasedUser, tool: toolItem.ToolItem):
        """Buy the given tool from the given user,
        adding the appropriate credits to their balance and adding the tool to the shop stock.
        :param BasedUser user: The user to buy tool from
        :param bbTool tool: The tool to buy from user
        """
        user.credits += tool.getValue()
        self.toolsStock.addItem(tool)
        user.inactiveTools.removeItem(tool)


    def userSellToolIndex(self, user: basedUser.BasedUser, index: int):
        """Buy the tool at the given index in the given user's tools Inventory,
        adding the appropriate credits to their balance and adding the tool to the shop stock.
        :param BasedUser user: The user to buy tool from
        :param int index: The index of the tool to buy from user, in the user's tools Inventory's array of keys
        """
        self.userSellToolObj(user, user.inactiveTools.itemAtIndex(index))


    ##### SERIALIZING #####


    def serialize(self, **kwargs) -> dict:
        """Get a dictionary containing all information needed to reconstruct this shop instance.
        This includes maximum item counts, and current stocks.

        :return: A dictionary containing all information needed to reconstruct this shop object
        :rtype: dict
        """
        if not kwargs.get("saveType", False):
            kwargs["saveType"] = True

        data = {}
        for invType in ["ship", "weapon", "module", "turret", "tool"]:
            stockDict = []
            currentStock = self.getStockByName(invType)

            for currentItem in currentStock.keys:
                if currentItem in currentStock.items:
                    stockDict.append(currentStock.items[currentItem].serialize(**kwargs))
                else:
                    botState.client.logger.log("bbShp", "serialize",
                                "Failed to save invalid " + invType + " key '" + str(currentItem) \
                                    + "' - not found in items dict",
                                category=LogCategory.shop, eventType="UNKWN_KEY")

            data[invType + "sStock"] = stockDict

        return data


    @classmethod
    def deserialize(cls, shopDict: dict, **kwargs) -> GuildShop:
        """Recreate a guildShop instance from its dictionary-serialized representation - the opposite of guildShop.serialize

        :param dict shopDict: A dictionary containing all information needed to construct the shop
        :return: A new guildShop object as described by shopDict
        :rtype: guildShop
        """
        shipsStock = Inventory(Ship)
        weaponsStock = Inventory(PrimaryWeapon)
        modulesStock = Inventory(moduleItem.ModuleItem)
        turretsStock = Inventory(TurretWeapon)
        toolsStock = Inventory(toolItem.ToolItem)

        for key, stock, deserializer in (("shipsStock", shipsStock, Ship),
                                        ("weaponsStock", weaponsStock, PrimaryWeapon),
                                        ("modulesStock", modulesStock, moduleItemFactory.ModuleItemFactory),
                                        ("turretsStock", turretsStock, TurretWeapon),
                                        ("toolsStock", toolsStock, toolItemFactory.ToolItemFactory)):
            if key in shopDict:
                for listingDict in shopDict[key]:
                    # I can't find a way to convince pyright that each tuple in the the params only contains matching types,
                    # Even if I cast the items in the tuple!
                    stock.addItem(deserializer.deserialize(listingDict["item"]), # type: ignore[reportGeneralTypeIssues]
                                    quantity=listingDict["count"])

        return GuildShop(shipsStock=shipsStock, weaponsStock=weaponsStock, modulesStock=modulesStock,
                            turretsStock=turretsStock, toolsStock=toolsStock)


class TechLeveledShop(GuildShop):
    """A shop containing a random selection of items which players can buy.
    Items can be sold to the shop to the shop's inventory and listed for sale.
    Shops are assigned a random tech level, which influences ths stock generated.
    
    :var currentTechLevel: The current tech level of the shop, influencing the tech levels of the stock generated upon refresh
    :vartype currentTechLevel: int
    :var minLevel: The minimum tech level that the shop can take
    :vartype minLevel: int
    :var maxLevel: The maximum tech level that the shop can take
    :vartype maxLevel: int
    """

    def __init__(self, minLevel: int, maxLevel: int, shipsStock: Optional[Inventory] = None, weaponsStock: Optional[Inventory] = None,
                    modulesStock: Optional[Inventory] = None, turretsStock: Optional[Inventory] = None, toolsStock: Optional[Inventory] = None,
                    currentTechLevel: Optional[int] = None, noRefresh: bool = False):
        """
        :param int currentTechLevel: The current tech level of the shop, influencing the tech levels of the stock generated
                                        upon refresh. (Default empty inventory)
        :param int minLevel: The minimum tech level that the shop can take
        :param int maxLevel: The maximum tech level that the shop can take
        :param inventory shipsStock: The shop's current stock of ships (Default empty inventory)
        :param inventory weaponsStock: The shop's current stock of weapons (Default empty inventory)
        :param inventory modulesStock: The shop's current stock of modules (Default empty inventory)
        :param inventory turretsStock: The shop's current stock of turrets (Default empty inventory)
        :param inventory toolsStock: The shop's current stock of tools (Default empty inventory)
        :param bool noRefresh: If the shop is empty on creation, it will be restocked unless noRefresh is True (Default False)
        """
        super().__init__(shipsStock=shipsStock, weaponsStock=weaponsStock, modulesStock=modulesStock,
                            turretsStock=turretsStock, toolsStock=toolsStock)

        if maxLevel > cfg.maxTechLevel:
            raise ValueError(f"Attempted to create a shop with a max tech level above cfg.maxTechLevel: {maxLevel}")
        if minLevel < cfg.minTechLevel:
            raise ValueError(f"Attempted to create a shop with a min tech level below cfg.minTechLevel: {minLevel}")
        if maxLevel < minLevel:
            raise ValueError(f"Attempted to create a shop with a max level ({maxLevel}) higher than the min level ({minLevel})")
            
        self.minLevel = minLevel
        self.maxLevel = maxLevel
        self.currentTechLevel = currentTechLevel if currentTechLevel is not None else self.pickNewTL(guaranteeNew=False)
        if not noRefresh and self.isEmpty():
            self.refreshStock()


    def pickNewTL(self, guaranteeNew: bool = True) -> int:
        """Generate a new tech level for the shop.
        This will be between self.minLevel and self.maxLevel.

        :param bool guaranteeNew: When True, the new level cannot be the same as the current one, unless
                                    self.minLevel and self.maxLevel are the same. (Default True)
        """
        # return gameMaths.pickRandomShopTL()

        if self.minLevel == self.maxLevel:
            return self.minLevel
        else:
            newTL = random.randint(self.minLevel, self.maxLevel)
            if guaranteeNew:
                while newTL == self.currentTechLevel:
                    newTL = random.randint(self.minLevel, self.maxLevel)
            return newTL


    def refreshStock(self, level: int = -1):
        """Refresh the stock of the shop by picking random items according to the given tech level. All previous stock is deleted.
        If level = -1 is given, a new shop tech level is generated at random.

        :param int level: The new tech level of the shop. Give -1 to pick a level at random according to cfg.pickRandomShopTL()
        :raise ValueError: When given a tech level that is out of range
        """
        # Clear out all existing stocks
        self.shipsStock.clear()
        self.weaponsStock.clear()
        self.modulesStock.clear()
        self.turretsStock.clear()
        self.toolsStock.clear()

        # Pick a new tech level if not supplied with one
        if level == -1:
            self.currentTechLevel = self.pickNewTL()
        else:
            # If given a tech level, make sure its valid
            if level not in range(cfg.minTechLevel, cfg.maxTechLevel + 1):
                raise ValueError(f"Attempted to refresh a shop at tech level {level}. Must be within the range " \
                                + f"{cfg.minTechLevel} to {cfg.maxTechLevel}")
            self.currentTechLevel = level

        # Item spawning minimums are given in cfg by their class names. Convert these into actual classes.
        moduleTypeMins = {gameItem.spawnableItemClassFromName(k): v for k, v in cfg.minModuleTypeShopSpawns.items() if v}
        weaponTypeMins = {gameItem.spawnableItemClassFromName(k): v for k, v in cfg.minWeaponTypeShopSpawns.items() if v}
        turretTypeMins = {gameItem.spawnableItemClassFromName(k): v for k, v in cfg.minTurretTypeShopSpawns.items() if v}

        # Iterate over all item types in the shop - weapons, modules and turrets. Ships are handled separately.
        for typeMins, maxCount, stock, keys in \
                (
                    (moduleTypeMins, cfg.shopDefaultModulesNum, self.modulesStock, bbData.moduleObjsByTL),
                    (weaponTypeMins, cfg.shopDefaultWeaponsNum, self.weaponsStock, bbData.weaponObjsByTL),
                    (turretTypeMins, cfg.shopDefaultTurretsNum, self.turretsStock, bbData.turretObjsByTL)
                ):

            if typeMins:
                # Iterate over all item types
                for itemType, minCount in typeMins.items():
                    # Find the items of the required type that could spawn at the shop's current level

                    possibleItems: Dict[int, List[gameItem.GameItem]] = {tl: i for tl, i in {
                        tl: [i for i in (keys[tl - 1] if tl >= len(keys) else []) if isinstance(i, itemType)]
                            for tl in gameMaths.possibleItemTLs(self.currentTechLevel)
                    }.items() if i}

                    if possibleItems:
                        # Add a random selection of minCount items from possibleItems
                        for _ in range(minCount):
                            # Pick the tech level of this new item
                            itemTL = gameMaths.pickRandomItemTL(self.currentTechLevel)
                            tries = 5
                            while itemTL not in possibleItems and tries > 0:
                                # Make sure the picked techLevel corresponds to a level that has an item of the type we want
                                itemTL = gameMaths.pickRandomItemTL(self.currentTechLevel)
                                # Limit this loop just in case there's an error elsewhere. Don't want to deadlock the bot
                                tries -= 1
                            
                            # If the loop ran out of tries, just pick the lowest valid TL
                            if itemTL not in possibleItems:
                                itemTL = list(possibleItems)[0]
                            
                            # Pick an item at the selected tech level with equal likelihood
                            # I can't find a way to show pyright that the types from the for loop params tuple match
                            stock.addItem(random.choice(possibleItems[itemTL])) # type: ignore[reportGeneralTypeIssues]
                
                # Take off the number of items spawned from the number of non-essential items to spawn
                maxCount -= stock.totalItems
            
            # Try to spawn maxCount items. Might not get that many.
            for _ in range(maxCount):
                # Pick the tech level of this new item
                itemTL = gameMaths.pickRandomItemTL(self.currentTechLevel)
                # Pick an item at this tech level with equal likelihood. If there aren't any items at this level, then ignore.
                if len(keys[itemTL - 1]) != 0:
                    # I can't find a way to show pyright that the types from the for loop params tuple match
                    stock.addItem(random.choice(keys[itemTL - 1])) # type: ignore[reportGeneralTypeIssues]

        # Do the same as above for ships.
        # This is handled separately because ships are added to the shop by their serialized data, not by existing instances.
        for _ in range(cfg.shopDefaultShipsNum):
            itemTL = gameMaths.pickRandomItemTL(self.currentTechLevel)
            if len(bbData.shipKeysByTL[itemTL - 1]) != 0:
                newShip = Ship.deserialize(bbData.builtInShipData[random.choice(bbData.shipKeysByTL[itemTL - 1])])
                self.shipsStock.addItem(newShip)


    def serialize(self, **kwargs) -> dict:
        """Get a dictionary containing all information needed to reconstruct this shop instance.
        This includes maximum item counts, current tech level, and current stocks.

        :return: A dictionary containing all information needed to reconstruct this shop object
        :rtype: dict
        """
        data = super().serialize(**kwargs)
        data["minLevel"] = self.minLevel
        data["maxLevel"] = self.maxLevel
        data["currentTechLevel"] = self.currentTechLevel
        return data


    @classmethod
    def deserialize(cls, shopDict: dict, **kwargs) -> TechLeveledShop:
        """Recreate a TechLeveledShop instance from its dictionary-serialized representation - the opposite of TechLeveledShop.serialize
        
        :param dict shopDict: A dictionary containing all information needed to construct the shop
        :return: A new TechLeveledShop object as described by shopDict
        :rtype: TechLeveledShop
        """
        shipsStock = Inventory(Ship)
        weaponsStock = Inventory(PrimaryWeapon)
        modulesStock = Inventory(moduleItem.ModuleItem)
        turretsStock = Inventory(TurretWeapon)
        toolsStock = Inventory(toolItem.ToolItem)

        for key, stock, deserializer in (("shipsStock", shipsStock, Ship),
                                        ("weaponsStock", weaponsStock, PrimaryWeapon),
                                        ("modulesStock", modulesStock, moduleItemFactory.ModuleItemFactory),
                                        ("turretsStock", turretsStock, TurretWeapon),
                                        ("toolsStock", toolsStock, toolItemFactory.ToolItemFactory)):
            if key in shopDict:
                for listingDict in shopDict[key]:
                    # I can't find a way to show pyright that the types from the for loop params tuple match
                    stock.addItem(deserializer.deserialize(listingDict["item"]), # type: ignore[reportGeneralTypeIssues]
                                    quantity=listingDict["count"])

        return TechLeveledShop(minLevel=shopDict["minLevel"], maxLevel=shopDict["maxLevel"],
                                currentTechLevel=shopDict.get("currentTechLevel", 1),
                                shipsStock=shipsStock, weaponsStock=weaponsStock, modulesStock=modulesStock,
                                turretsStock=turretsStock, toolsStock=toolsStock)
