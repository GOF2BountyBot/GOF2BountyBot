from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from .items.ships import shipItem, shipBase
if TYPE_CHECKING:
    from ..users import basedUser

from . import guildShop
from bot.cfg import cfg
from .items import gameItem
from .items.weapons import primaryWeapon, turretWeapon
from .items.modules import moduleItem
from .items.tools import toolItem
from .inventories import inventory
from .inventories.inventoryListing import InventoryListing, SerializedInventoryListing


class KaamoShop(guildShop.ShopBase[inventory.SerializedInventory[SerializedInventoryListing], InventoryListing]):
    """A "shop" where all transactions are free, essentially operating an item storage service.
    KaamoShops have a maximum capacity defined in cfg. Items equipped onto ships count towards this cap.
    """

    def __init__(self, shipsStock: Optional[inventory.Inventory[shipItem.Ship, shipBase.SerializedShipUnion]] = None,
            weaponsStock: Optional[inventory.Inventory[primaryWeapon.PrimaryWeapon, primaryWeapon.SerializedWeaponUnion]] = None,
            modulesStock: Optional[inventory.Inventory[moduleItem.ModuleItem, moduleItem.SerializedModuleItemUnion]] = None,
            turretsStock: Optional[inventory.Inventory[turretWeapon.TurretWeapon, turretWeapon.SerializedWeaponUnion]] = None,
            toolsStock: Optional[inventory.Inventory[toolItem.ToolItem, toolItem.SerializedToolItemUnion]] = None):
        """
        :param Inventory shipsStock: The shop's current stock of ships (Default empty Inventory)
        :param Inventory weaponsStock: The shop's current stock of weapons (Default empty Inventory)
        :param Inventory modulesStock: The shop's current stock of modules (Default empty Inventory)
        :param Inventory turretsStock: The shop's current stock of turrets (Default empty Inventory)
        :param Inventory toolsStock: The shop's current stock of tools (Default empty Inventory)
        """

        super().__init__(shipsStock=shipsStock or inventory.Inventory(shipItem.Ship),
                            weaponsStock=weaponsStock or inventory.Inventory(primaryWeapon.PrimaryWeapon),
                            modulesStock=modulesStock or inventory.Inventory(moduleItem.ModuleItem),
                            turretsStock=turretsStock or inventory.Inventory(turretWeapon.TurretWeapon),
                            toolsStock=toolsStock or inventory.Inventory(toolItem.ToolItem))
        self.totalItems = self.weaponsStock.totalItems + self.modulesStock.totalItems + self.turretsStock.totalItems \
                            + self.toolsStock.totalItems
        for ship in self.shipsStock.items:
            self.totalItems += 1 + len(ship.weapons) + len(ship.modules) + len(ship.turrets)


    def isFull(self) -> bool:
        """Decide if this KaamoShop is at capacity.

        :return: True if the items stock is full, False otherwise
        """
        return self.totalItems >= cfg.kaamoMaxCapacity


    def userCanAffordItemObj(self, user: basedUser.BasedUser, item: gameItem.GameItem) -> bool:
        """No costs are incurred when transferring items to or from a KaamoShop.
        """
        raise NotImplementedError("Item affordability is not applicable to KaamoShops.")

#region ships

    def userCanAffordShipIndex(self, user: basedUser.BasedUser, index: int) -> bool:
        """No costs are incurred when transferring items to or from a KaamoShop.
        """
        raise NotImplementedError("Item affordability is not applicable to KaamoShops.")


    def amountCanAffordShipObj(self, amount: int, ship: shipItem.Ship) -> bool:
        """No costs are incurred when transferring items to or from a KaamoShop.
        """
        raise NotImplementedError("Item affordability is not applicable to KaamoShops.")


    def amountCanAffordShipIndex(self, amount: int, index: int) -> bool:
        """No costs are incurred when transferring items to or from a KaamoShop.
        """
        raise NotImplementedError("Item affordability is not applicable to KaamoShops.")


    def userBuyShipIndex(self, user: basedUser.BasedUser, index: int):
        """Moves the ship at the given index in the user's inventory to the shop's inventory.
        :param BasedUser user: The user attempting to buy the ship
        :param int index: The index of the requested ship in the shop's ships Inventory's array of keys
        """
        self.userBuyShipObj(user, self.shipsStock.itemAtIndex(index))


    def userBuyShipObj(self, user: basedUser.BasedUser, requestedShip: shipItem.Ship):
        """Moves the given ship from the shop's inventory to the user's.
        :param BasedUser user: The user attempting to buy the ship
        :param bbShip requestedWeapon: The ship to sell to user
        """
        self.totalItems -= 1
        self.totalItems -= len(requestedShip.weapons)
        self.totalItems -= len(requestedShip.modules)
        self.totalItems -= len(requestedShip.turrets)
        self.shipsStock.removeItem(requestedShip)
        user.inactiveShips.addItem(requestedShip)


    def userSellShipObj(self, user: basedUser.BasedUser, ship: shipItem.Ship):
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


    def userSellShipIndex(self, user: basedUser.BasedUser, index: int):
        """Moves the ship at the given index in the user's inventory to the shop's inventory.
        :param BasedUser user: The user to buy ship from
        :param int index: The index of the weapon to buy from user, in the user's ships Inventory's array of keys
        """
        self.userSellShipObj(user, user.inactiveShips.itemAtIndex(index))

#endregion
#region weapons

    def userCanAffordWeaponIndex(self, user: basedUser.BasedUser, index: int) -> bool:
        """No costs are incurred when transferring items to or from a KaamoShop.
        """
        raise NotImplementedError("Item affordability is not applicable to KaamoShops.")


    def userBuyWeaponIndex(self, user: basedUser.BasedUser, index: int):
        """Moves the weapon at the given index in the shop's inventory to the user's inventory.
        :param BasedUser user: The user to sell weapon to
        :param int index: The index of the weapon to sell to user, in the shop's weapon Inventory's array of keys
        """
        self.userBuyWeaponObj(user, self.weaponsStock.itemAtIndex(index))


    def userBuyWeaponObj(self, user: basedUser.BasedUser, requestedWeapon: primaryWeapon.PrimaryWeapon):
        """Moves the given weapon from the shop's inventory to the user's.
        :param BasedUser user: The user attempting to buy the weapon
        :param bbWeapon requestedWeapon: The weapon to sell to user
        """
        self.totalItems -= 1
        self.weaponsStock.removeItem(requestedWeapon)
        user.inactiveWeapons.addItem(requestedWeapon)


    def userSellWeaponObj(self, user: basedUser.BasedUser, weapon: primaryWeapon.PrimaryWeapon):
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


    def userSellWeaponIndex(self, user: basedUser.BasedUser, index: int):
        """Moves the weapon at the given index in the user's inventory to the shop's inventory.
        :param BasedUser user: The user to buy weapon from
        :param int index: The index of the weapon to buy from user, in the user's weapons Inventory's array of keys
        """
        self.userSellWeaponObj(user, user.inactiveWeapons.itemAtIndex(index))

#endregion
#region modules

    def userCanAffordModuleIndex(self, user: basedUser.BasedUser, index: int) -> bool:
        """No costs are incurred when transferring items to or from a KaamoShop.
        """
        raise NotImplementedError("Item affordability is not applicable to KaamoShops.")


    def userBuyModuleIndex(self, user: basedUser.BasedUser, index: int):
        """Moves the module at the given index in the shop's inventory to the user's inventory.
        :param BasedUser user: The user attempting to buy the module
        :param int index: The index of the requested module in the shop's modules Inventory's array of keys
        """
        self.userBuyModuleObj(user, self.modulesStock.itemAtIndex(index))


    def userBuyModuleObj(self, user: basedUser.BasedUser, requestedModule: moduleItem.ModuleItem):
        """Moves the given module from the shop's inventory to the user's.
        :param BasedUser user: The user attempting to buy the module
        :param bbModule requestedModule: The module to sell to user
        """
        self.totalItems -= 1
        self.modulesStock.removeItem(requestedModule)
        user.inactiveModules.addItem(requestedModule)


    def userSellModuleObj(self, user: basedUser.BasedUser, module: moduleItem.ModuleItem):
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


    def userSellModuleIndex(self, user: basedUser.BasedUser, index: int):
        """Moves the module at the given index in the user's inventory to the shop's inventory.
        :param BasedUser user: The user to buy module from
        :param int index: The index of the module to buy from user, in the user's modules Inventory's array of keys
        """
        self.userSellModuleObj(user, user.inactiveModules.itemAtIndex(index))

#endregion
#region turrets

    def userCanAffordTurretIndex(self, user: basedUser.BasedUser, index: int) -> bool:
        """No costs are incurred when transferring items to or from a KaamoShop.
        """
        raise NotImplementedError("Item affordability is not applicable to KaamoShops.")


    def userBuyTurretIndex(self, user: basedUser.BasedUser, index: int):
        """Moves the turret at the given index in the shop's inventory to the user's inventory.
        :param BasedUser user: The user attempting to buy the turret
        :param int index: The index of the requested turret in the shop's turrets Inventory's array of keys
        """
        self.userBuyTurretObj(user, self.turretsStock.itemAtIndex(index))


    def userBuyTurretObj(self, user: basedUser.BasedUser, requestedTurret: turretWeapon.TurretWeapon):
        """Moves the given turret from the shop's inventory to the user's.
        :param BasedUser user: The user attempting to buy the turret
        :param bbTurret requestedTurret: The turret to sell to user
        """
        self.totalItems -= 1
        self.turretsStock.removeItem(requestedTurret)
        user.inactiveTurrets.addItem(requestedTurret)


    def userSellTurretObj(self, user: basedUser.BasedUser, turret: turretWeapon.TurretWeapon):
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


    def userSellTurretIndex(self, user: basedUser.BasedUser, index: int):
        """Moves the turret at the given index in the user's inventory to the shop's inventory.
        :param BasedUser user: The user to buy turret from
        :param int index: The index of the turret to buy from user, in the user's turrets Inventory's array of keys
        """
        self.userSellTurretObj(user, user.inactiveTurrets.itemAtIndex(index))

#endregion
#region tools

    def userCanAffordToolIndex(self, user: basedUser.BasedUser, index: int) -> bool:
        """No costs are incurred when transferring items to or from a KaamoShop.
        """
        raise NotImplementedError("Item affordability is not applicable to KaamoShops.")


    def userBuyToolIndex(self, user: basedUser.BasedUser, index: int):
        """Moves the tool at the given index in the shop's inventory to the user's inventory.
        :param BasedUser user: The user attempting to buy the tool
        :param int index: The index of the requested tool in the shop's tools Inventory's array of keys
        """
        self.userBuyToolObj(user, self.toolsStock.itemAtIndex(index))


    def userBuyToolObj(self, user: basedUser.BasedUser, requestedTool: toolItem.ToolItem):
        """Moves the given tool from the shop's inventory to the user's.
        :param BasedUser user: The user attempting to buy the tool
        :param bbToolItem requestedTool: The tool to sell to user
        """
        self.totalItems -= 1
        self.toolsStock.removeItem(requestedTool)
        user.inactiveTools.addItem(requestedTool)


    def userSellToolObj(self, user: basedUser.BasedUser, tool: toolItem.ToolItem):
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


    def userSellToolIndex(self, user: basedUser.BasedUser, index: int):
        """Moves the tool at the given index in the user's inventory to the shop's inventory.
        :param BasedUser user: The user to buy tool from
        :param int index: The index of the tool to buy from user, in the user's tools Inventory's array of keys
        """
        self.userSellToolObj(user, user.inactiveTools.itemAtIndex(index))

#endregion

    @classmethod
    def deserialize(cls, shopDict: guildShop.SerializedShopBase, **kwargs) -> KaamoShop:
        """Recreate a bbShop instance from its dictionary-serialized representation - the opposite of bbShop.serialize
        
        :param dict shopDict: A dictionary containing all information needed to construct the shop
        :return: A new bbShop object as described by shopDict
        :rtype: bbShop
        """
        return super().deserialize(shopDict)
                                