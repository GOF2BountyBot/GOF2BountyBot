from __future__ import annotations
from typing import TYPE_CHECKING, cast
if TYPE_CHECKING:
    from ..users import basedUser

from . import guildShop
from ..cfg import cfg
from .items import gameItem, shipItem, moduleItemFactory
from .items.weapons import primaryWeapon, turretWeapon
from .items.modules import moduleItem
from .items.tools import toolItem, toolItemFactory
from .. import botState
from .inventories import inventory
from .inventories import inventoryListing


class KaamoShop(guildShop.GuildShop):
    """A "shop" where all transactions are free, essentially operating an item storage service.
    KaamoShops have a maximum capacity defined in cfg. Items equipped onto ships count towards this cap.
    """

    def __init__(self, shipsStock : inventory.KaamoTypeRestrictedInventory = None,
            weaponsStock : inventory.KaamoTypeRestrictedInventory = None,
            modulesStock : inventory.KaamoTypeRestrictedInventory = None,
            turretsStock : inventory.KaamoTypeRestrictedInventory = None,
            toolsStock : inventory.KaamoTypeRestrictedInventory = None):
        """
        :param shipsStock: The shop's current stock of ships (Default empty Inventory)
        :type shipsStock: inventory.KaamoTypeRestrictedInventory
        :param weaponsStock: The shop's current stock of weapons (Default empty Inventory)
        :type weaponsStock: inventory.KaamoTypeRestrictedInventory
        :param modulesStock: The shop's current stock of modules (Default empty Inventory)
        :type modulesStock: inventory.KaamoTypeRestrictedInventory
        :param turretsStock: The shop's current stock of turrets (Default empty Inventory)
        :type turretsStock: inventory.KaamoTypeRestrictedInventory
        :param toolsStock: The shop's current stock of tools (Default empty Inventory)
        :type toolsStock: inventory.KaamoTypeRestrictedInventory
        """

        super().__init__(shipsStock=shipsStock, weaponsStock=weaponsStock, modulesStock=modulesStock,
                            turretsStock=turretsStock, toolsStock=toolsStock)
        self.totalItems = self.weaponsStock.totalItems + self.modulesStock.totalItems + self.turretsStock.totalItems \
                            + self.toolsStock.totalItems
        for ship in self.shipsStock.items:
            self.totalItems += 1 + len(ship.weapons) + len(ship.modules) + len(ship.turrets)


    def isFull(self) -> bool:
        """Decide if this KaamoShop is at capacity.

        :return: True if the items stock is full, False otherwise
        """
        return self.totalItems >= cfg.kaamoMaxCapacity


    def userCanAffordItemObj(self, user : basedUser.BasedUser, item : gameItem.GameItem) -> bool:
        listing = cast(inventoryListing.KaamoItemListing, self.getStockByType(type(item)).getListing(item))
        return self._userCanAffordListingObj(user, listing)


    def _userCanAffordListingObj(self, user: basedUser.BasedUser, itemListing: inventoryListing.KaamoItemListing) -> bool:
        return not itemListing.userPrestiged or \
            user.credits >= int(cast(gameItem.GameItem, itemListing.item).getValue() * cfg.postPrestigeKaamoDiscountMult)


    def userBuyShipObj(self, user : basedUser.BasedUser, requestedShip : shipItem.Ship):
        """Moves the given ship from the shop's inventory to the user's.
        :param BasedUser user: The user attempting to buy the ship
        :param bbShip requestedWeapon: The ship to sell to user
        """
        super().userBuyShipObj(user, requestedShip)
        self.totalItems -= 1
        self.totalItems -= len(requestedShip.weapons)
        self.totalItems -= len(requestedShip.modules)
        self.totalItems -= len(requestedShip.turrets)


    def userSellShipObj(self, user : basedUser.BasedUser, ship : shipItem.Ship):
        """Moves the given ship from the user's inventory to the shop's.
        :param BasedUser user: The user to buy ship from
        :param bbShip weapon: The ship to buy from user
        :raise OverflowError: When attempting to fill the shop beyond max capacity
        """
        numShipItems = 1 + len(ship.weapons) + len(ship.modules) + len(ship.turrets)
        if self.totalItems + numShipItems > cfg.kaamoMaxCapacity:
            raise OverflowError("Attempted to fill the shop beyond capacity.")
        self.totalItems += numShipItems
        self.shipsStock.addItem(ship)
        user.inactiveShips.removeItem(ship)



    # WEAPON MANAGEMENT
    def userBuyWeaponObj(self, user : basedUser.BasedUser, requestedWeapon : primaryWeapon.PrimaryWeapon):
        """Moves the given weapon from the shop's inventory to the user's.
        :param BasedUser user: The user attempting to buy the weapon
        :param bbWeapon requestedWeapon: The weapon to sell to user
        """
        super().userBuyWeaponObj(user, requestedWeapon)
        self.totalItems -= 1


    def userSellWeaponObj(self, user : basedUser.BasedUser, weapon : primaryWeapon.PrimaryWeapon):
        """Moves the given weapon from the user's inventory to the shop's.
        :param BasedUser user: The user to buy weapon from
        :param bbWeapon weapon: The weapon to buy from user
        :raise OverflowError: When attempting to fill the shop beyond max capacity
        """
        if self.totalItems == cfg.kaamoMaxCapacity:
            raise OverflowError("Attempted to fill the shop beyond capacity.")
        self.totalItems += 1
        self.weaponsStock.addItem(weapon)
        user.inactiveWeapons.removeItem(weapon)



    # MODULE MANAGEMENT
    def userBuyModuleObj(self, user : basedUser.BasedUser, requestedModule : moduleItem.ModuleItem):
        """Moves the given module from the shop's inventory to the user's.
        :param BasedUser user: The user attempting to buy the module
        :param bbModule requestedModule: The module to sell to user
        """
        super().userBuyModuleObj(user, requestedModule)
        self.totalItems -= 1


    def userSellModuleObj(self, user : basedUser.BasedUser, module : moduleItem.ModuleItem):
        """Moves the given module from the user's inventory to the shop's.
        :param BasedUser user: The user to buy module from
        :param bbModule module: The module to buy from user
        :raise OverflowError: When attempting to fill the shop beyond max capacity
        """
        if self.totalItems == cfg.kaamoMaxCapacity:
            raise OverflowError("Attempted to fill the shop beyond capacity.")
        self.totalItems += 1
        self.modulesStock.addItem(module)
        user.inactiveModules.removeItem(module)



    # TURRET MANAGEMENT
    def userBuyTurretObj(self, user : basedUser.BasedUser, requestedTurret : turretWeapon.TurretWeapon):
        """Moves the given turret from the shop's inventory to the user's.
        :param BasedUser user: The user attempting to buy the turret
        :param bbTurret requestedTurret: The turret to sell to user
        """
        super().userBuyTurretObj(user, requestedTurret)
        self.totalItems -= 1


    def userSellTurretObj(self, user : basedUser.BasedUser, turret : turretWeapon.TurretWeapon):
        """Moves the given turret from the user's inventory to the shop's.
        :param BasedUser user: The user to buy turret from
        :param bbTurret turret: The turret to buy from user
        :raise OverflowError: When attempting to fill the shop beyond max capacity
        """
        if self.totalItems == cfg.kaamoMaxCapacity:
            raise OverflowError("Attempted to fill the shop beyond capacity.")
        self.totalItems += 1
        self.turretsStock.addItem(turret)
        user.inactiveTurrets.removeItem(turret)



    # TOOL MANAGEMENT
    def userBuyToolObj(self, user : basedUser.BasedUser, requestedTool : toolItem.ToolItem):
        """Moves the given tool from the shop's inventory to the user's.
        :param BasedUser user: The user attempting to buy the tool
        :param bbToolItem requestedTool: The tool to sell to user
        """
        super().userBuyToolObj(user, requestedTool)
        self.totalItems -= 1


    def userSellToolObj(self, user : basedUser.BasedUser, tool : toolItem.ToolItem):
        """Moves the given tool from the user's inventory to the shop's.
        :param BasedUser user: The user to buy tool from
        :param bbTool tool: The tool to buy from user
        :raise OverflowError: When attempting to fill the shop beyond max capacity
        """
        if self.totalItems == cfg.kaamoMaxCapacity:
            raise OverflowError("Attempted to fill the shop beyond capacity.")
        self.totalItems += 1
        self.toolsStock.addItem(tool)
        user.inactiveTools.removeItem(tool)



    def toDict(self, **kwargs) -> dict:
        """Get a dictionary containing all information needed to reconstruct this shop instance.
        This includes maximum item counts and current stocks.
        :return: A dictionary containing all information needed to reconstruct this shop object
        :rtype: dict
        """
        kwargs.update({"saveType": True})

        data = {}
        for invType in ["ship", "weapon", "module", "turret", "tool"]:
            stockDict = []
            currentStock = self.getStockByName(invType)

            for currentItem in currentStock.keys:
                if currentItem in currentStock.items:
                    stockDict.append(currentStock.items[currentItem].toDict(**kwargs))
                else:
                    botState.logger.log("kaamoShop", "toDict",
                                        f"Failed to save invalid {invType} key '{currentItem}' - not found in items dict",
                                        category="shop", eventType="UNKWN_KEY")

            data[invType + "sStock"] = stockDict

        return data


    @classmethod
    def fromDict(cls, shopDict : dict, **kwargs) -> KaamoShop:
        """Recreate a bbShop instance from its dictionary-serialized representation - the opposite of bbShop.toDict
        
        :param dict shopDict: A dictionary containing all information needed to construct the shop
        :return: A new bbShop object as described by shopDict
        :rtype: bbShop
        """
        shipsStock = inventory.KaamoTypeRestrictedInventory(shipItem.Ship)
        weaponsStock = inventory.KaamoTypeRestrictedInventory(primaryWeapon.PrimaryWeapon)
        modulesStock = inventory.KaamoTypeRestrictedInventory(moduleItem.ModuleItem)
        turretsStock = inventory.KaamoTypeRestrictedInventory(turretWeapon.TurretWeapon)
        toolsStock = inventory.KaamoTypeRestrictedInventory(toolItem.ToolItem)

        for key, stock, deserializer in (("shipsStock", shipsStock, shipItem.Ship.fromDict),
                                        ("weaponsStock", weaponsStock, primaryWeapon.PrimaryWeapon.fromDict),
                                        ("modulesStock", modulesStock, moduleItemFactory.fromDict),
                                        ("turretsStock", turretsStock, turretWeapon.TurretWeapon.fromDict),
                                        ("toolsStock", toolsStock, toolItemFactory.fromDict)):
            if key in shopDict:
                for listingDict in shopDict[key]:
                    newItem = deserializer(listingDict["item"])
                    stock.addItem(newItem, quantity=listingDict["count"])
                    if listingDict.get("userPrestiged", False):
                        stock.getListing(newItem).userPrestiged = True

        return KaamoShop(shipsStock=shipsStock, weaponsStock=weaponsStock, modulesStock=modulesStock,
                                turretsStock=turretsStock, toolsStock=toolsStock)
                                