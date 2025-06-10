# Typing imports
from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional, cast
from typing_extensions import TypedDict

from .items.ships import shipItem,shipBase
if TYPE_CHECKING:
    from ..users import basedUser

from .items import moduleItemFactory
from .items.weapons import primaryWeapon, turretWeapon, weapon
from .items.modules import moduleItem
from .inventories import inventory, inventoryListing
from .items.tools import toolItem, toolItemFactory
from . import guildShop, itemDiscount
from .inventories.inventoryListing import DiscountableItemListing, SerializedDiscountableItemListing
from bot.cfg.bbData import ItemCategory
from .items.gameItem import SerializedGameItemUnion

class SerializedLomaShop(TypedDict): # ideally this would inherit from guildShop.SerializedShopBase...
    shipsStock: List[inventoryListing.SerializedDiscountableItemListing[shipBase.SerializedShipUnion]]
    weaponsStock: List[inventoryListing.SerializedDiscountableItemListing[weapon.SerializedWeaponUnion]]
    modulesStock: List[inventoryListing.SerializedDiscountableItemListing[moduleItem.SerializedModuleItemUnion]]
    turretsStock: List[inventoryListing.SerializedDiscountableItemListing[weapon.SerializedWeaponUnion]]
    toolsStock: List[inventoryListing.SerializedDiscountableItemListing[toolItem.SerializedToolItemUnion]]
    

ShipInventoryType = inventory.DiscountableInventory[shipItem.Ship, shipBase.SerializedShipUnion]    
WeaponInventoryType = inventory.DiscountableInventory[primaryWeapon.PrimaryWeapon, primaryWeapon.SerializedWeaponUnion]
ModuleInventoryType = inventory.DiscountableInventory[moduleItem.ModuleItem, moduleItem.SerializedModuleItemUnion]
TurretInventoryType = inventory.DiscountableInventory[turretWeapon.TurretWeapon, turretWeapon.SerializedWeaponUnion]
ToolInventoryType = inventory.DiscountableInventory[toolItem.ToolItem, toolItem.SerializedToolItemUnion]


class LomaShop(guildShop.ShopBase[inventory.SerializedInventory[SerializedDiscountableItemListing], DiscountableItemListing]):
    """A private shop unique to each player, for purchasing special items intended only for that player.
    Items cannot be sold to Loma.
    """

    def __init__(self, shipsStock: Optional[ShipInventoryType] = None,
                    weaponsStock: Optional[WeaponInventoryType] = None,
                    modulesStock: Optional[ModuleInventoryType] = None,
                    turretsStock: Optional[TurretInventoryType] = None,
                    toolsStock: Optional[ToolInventoryType] = None):
        """
        :param shipsStock: The shop's current stock of ships (Default empty inventory.DiscountableInventory)
        :type shipsStock: inventory.DiscountableInventory
        :param weaponsStock: The shop's current stock of weapons (Default empty inventory.DiscountableInventory)
        :type weaponsStock: inventory.DiscountableInventory
        :param modulesStock: The shop's current stock of modules (Default empty inventory.DiscountableInventory)
        :type modulesStock: inventory.DiscountableInventory
        :param turretsStock: The shop's current stock of turrets (Default empty inventory.DiscountableInventory)
        :type turretsStock: inventory.DiscountableInventory
        :param toolsStock: The shop's current stock of tools (Default empty inventory.DiscountableInventory)
        :type toolsStock: inventory.DiscountableInventory
        """
        shipsStock = shipsStock or inventory.DiscountableInventory(shipItem.Ship)
        weaponsStock = weaponsStock or inventory.DiscountableInventory(primaryWeapon.PrimaryWeapon)
        modulesStock = modulesStock or inventory.DiscountableInventory(moduleItem.ModuleItem)
        turretsStock = turretsStock or inventory.DiscountableInventory(turretWeapon.TurretWeapon)
        toolsStock = toolsStock or inventory.DiscountableInventory(toolItem.ToolItem)

        super().__init__(shipsStock=shipsStock, weaponsStock=weaponsStock, modulesStock=modulesStock,
                            turretsStock=turretsStock, toolsStock=toolsStock)
        
#region inventories
    @property
    def shipsStock(self): return cast(ShipInventoryType, self._shipsStock)
    @property
    def weaponsStock(self): return cast(WeaponInventoryType, self._weaponsStock)
    @property
    def modulesStock(self): return cast(ModuleInventoryType, self._modulesStock)
    @property
    def turretsStock(self): return cast(TurretInventoryType, self._turretsStock)
    @property
    def toolsStock(self): return cast(ToolInventoryType, self._toolsStock)

    def userCanAffordItemObj(self, user: basedUser.BasedUser, item: guildShop.StoredItemType) -> bool:
        """Decide whether a user has enough credits to buy an item, taking into account any available discounts

        :param basedUser user: The user whose credits balance to check
        :param gameItem item: The item whose value to check
        :return: True if user's credits balance is greater than or equal to item's discounted value. False otherwise
        :rtype: bool
        """
        listing = self.getStockByType(type(item)).getListing(item)
        itemValue = int(item.value * listing.discounts[0].mult) if listing.discounts else item.value
        return user.credits >= itemValue
    
    
    def getStock(self, item: ItemCategory) -> inventory.DiscountableInventory[guildShop.StoredItemType, SerializedGameItemUnion]:
        """Get the inventory containing all current stock of the named type.
        This object is mutable and can alter the stock of the shop.
        This method is only on LomaShop to correct the typing of the Inventory returned.

        :param str item: The name of the item type to fetch. Must be one of ship, weapon, module or turret
        :return: The inventory used by the shop to store all stock of the requested type
        :rtype: inventory
        :raise ValueError: When requesting an unknown item type
        """
        return cast(inventory.DiscountableInventory, super().getStock(item))

#region selling

    def userSellShipObj(self, user: basedUser.BasedUser, ship: shipItem.Ship):
        """Selling items to Loma is not allowed."""
        raise NotImplementedError("Attempted to sell an item to a Loma shop")


    def userSellShipIndex(self, user: basedUser.BasedUser, index: int):
        """Selling items to Loma is not allowed."""
        raise NotImplementedError("Attempted to sell an item to a Loma shop")



    def userSellWeaponObj(self, user: basedUser.BasedUser, weapon: primaryWeapon.PrimaryWeapon):
        """Selling items to Loma is not allowed."""
        raise NotImplementedError("Attempted to sell an item to a Loma shop")


    def userSellWeaponIndex(self, user: basedUser.BasedUser, index: int):
        """Selling items to Loma is not allowed."""
        raise NotImplementedError("Attempted to sell an item to a Loma shop")



    def userSellModuleObj(self, user: basedUser.BasedUser, module: moduleItem.ModuleItem):
        """Selling items to Loma is not allowed."""
        raise NotImplementedError("Attempted to sell an item to a Loma shop")


    def userSellModuleIndex(self, user: basedUser.BasedUser, index: int):
        """Selling items to Loma is not allowed."""
        raise NotImplementedError("Attempted to sell an item to a Loma shop")



    def userSellTurretObj(self, user: basedUser.BasedUser, turret: turretWeapon.TurretWeapon):
        """Selling items to Loma is not allowed."""
        raise NotImplementedError("Attempted to sell an item to a Loma shop")


    def userSellTurretIndex(self, user: basedUser.BasedUser, index: int):
        """Selling items to Loma is not allowed."""
        raise NotImplementedError("Attempted to sell an item to a Loma shop")



    def userSellToolObj(self, user: basedUser.BasedUser, tool: toolItem.ToolItem):
        """Selling items to Loma is not allowed."""
        raise NotImplementedError("Attempted to sell an item to a Loma shop")


    def userSellToolIndex(self, user: basedUser.BasedUser, index: int):
        """Selling items to Loma is not allowed."""
        raise NotImplementedError("Attempted to sell an item to a Loma shop")

#endregion
#region buying

    def userBuyWeaponObj(self, user: basedUser.BasedUser, requestedWeapon: primaryWeapon.PrimaryWeapon):
        if not self.userCanAffordItemObj(user, requestedWeapon):
            raise RuntimeError(f"user {user.id} attempted to buy weapon {requestedWeapon.name}"
                                f" but can't afford it: {user.credits} < {requestedWeapon.getValue()}")
        _, valueDiscount = self.weaponsStock.removeItemAndDiscount(requestedWeapon)
        user.credits -= int(requestedWeapon.value * valueDiscount)
        user.inactiveWeapons.addItem(requestedWeapon)
        user.credits -= requestedWeapon.getValue()


    def userBuyModuleObj(self, user: basedUser.BasedUser, item: moduleItem.ModuleItem):
        if not self.userCanAffordItemObj(user, item):
            raise RuntimeError(f"user {user.id} attempted to buy module {item.name}"
                                f" but can't afford it: {user.credits} < {item.getValue()}")
        _, valueDiscount = self.modulesStock.removeItemAndDiscount(item)
        user.credits -= int(item.value * valueDiscount)
        user.inactiveModules.addItem(item)
        user.credits -= item.getValue()
        
        
    def userBuyTurretObj(self, user: basedUser.BasedUser, item: turretWeapon.TurretWeapon):
        if not self.userCanAffordItemObj(user, item):
            raise RuntimeError(f"user {user.id} attempted to buy Turret {item.name}"
                                f" but can't afford it: {user.credits} < {item.getValue()}")
        _, valueDiscount = self.turretsStock.removeItemAndDiscount(item)
        user.credits -= int(item.value * valueDiscount)
        user.inactiveTurrets.addItem(item)
        user.credits -= item.getValue()
        
        
    def userBuyToolObj(self, user: basedUser.BasedUser, item: toolItem.ToolItem):
        if not self.userCanAffordItemObj(user, item):
            raise RuntimeError(f"user {user.id} attempted to buy tool {item.name}"
                                f" but can't afford it: {user.credits} < {item.getValue()}")
        _, valueDiscount = self.toolsStock.removeItemAndDiscount(item)
        user.credits -= int(item.value * valueDiscount)
        user.inactiveTools.addItem(item)
        user.credits -= item.getValue()

#endregion buying

    @classmethod
    def deserialize(cls, shopDict: SerializedLomaShop, **kwargs) -> LomaShop:
        """Recreate a LomaShop instance from its dictionary-serialized representation - the opposite of LomaShop.serialize
        
        :param dict shopDict: A dictionary containing all information needed to construct the shop
        :return: A new LomaShop object as described by shopDict
        :rtype: LomaShop
        """
        shipsStock = inventory.DiscountableInventory(shipItem.Ship)
        weaponsStock = inventory.DiscountableInventory(primaryWeapon.PrimaryWeapon)
        modulesStock = inventory.DiscountableInventory(moduleItem.ModuleItem)
        turretsStock = inventory.DiscountableInventory(turretWeapon.TurretWeapon)
        toolsStock = inventory.DiscountableInventory(toolItem.ToolItem)

        for key, stock, deserializer in (("shipsStock", shipsStock, shipItem.Ship),
                                        ("weaponsStock", weaponsStock, primaryWeapon.PrimaryWeapon),
                                        ("modulesStock", modulesStock, moduleItemFactory.ModuleItemFactory),
                                        ("turretsStock", turretsStock, turretWeapon.TurretWeapon),
                                        ("toolsStock", toolsStock, toolItemFactory.ToolItemFactory)):
            if key in shopDict:
                for listingDict in shopDict[key]:
                    # I can't find a way to show pyright that the types from the for loop params tuple match
                    newItem = deserializer.deserialize(listingDict["item"], # type: ignore[reportGeneralTypeIssues]
                                                        **kwargs)
                    stock.addItem(newItem, quantity=listingDict["count"]) # type: ignore[reportGeneralTypeIssues]
                    if "discounts" in listingDict:
                        for discountDict in listingDict["discounts"]:
                            # I can't find a way to show pyright that the types from the for loop params tuple match
                            stock.getListing(newItem).pushDiscount(itemDiscount.ItemDiscount.deserialize(discountDict, **kwargs)) # type: ignore[reportGeneralTypeIssues]

        return LomaShop(shipsStock=shipsStock, weaponsStock=weaponsStock, modulesStock=modulesStock,
                        turretsStock=turretsStock, toolsStock=toolsStock)


    # Just adding this in so that the type checker knows the structure of the serialized inventoryListings                        
    def serialize(self, **kwargs) -> SerializedLomaShop:
        return cast(SerializedLomaShop, super().serialize(**kwargs))