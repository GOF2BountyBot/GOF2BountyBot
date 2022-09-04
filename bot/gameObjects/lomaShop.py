# Typing imports
from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional, TypedDict, cast
if TYPE_CHECKING:
    from ..users import basedUser

from .items import moduleItemFactory, shipItem
from .items.weapons import primaryWeapon, turretWeapon, weapon
from .items.modules import moduleItem
from .inventories import inventory, inventoryListing
from .items.tools import toolItem, toolItemFactory
from . import guildShop, itemDiscount
from ..gameObjects.inventories.inventoryListing import DiscountableItemListing, SerializedDiscountableItemListing

class SerializedLomaShop(TypedDict): # ideally this would inherit from guildShop.SerializedShopBase...
    shipsStock: List[inventoryListing.SerializedDiscountableItemListing[shipItem.SerializedShipUnion]]
    weaponsStock: List[inventoryListing.SerializedDiscountableItemListing[weapon.SerializedWeaponUnion]]
    modulesStock: List[inventoryListing.SerializedDiscountableItemListing[moduleItem.SerializedModuleItemUnion]]
    turretsStock: List[inventoryListing.SerializedDiscountableItemListing[weapon.SerializedWeaponUnion]]
    toolsStock: List[inventoryListing.SerializedDiscountableItemListing[toolItem.SerializedToolItemUnion]]
    

class LomaShop(guildShop.ShopBase[inventory.SerializedInventory[SerializedDiscountableItemListing], DiscountableItemListing]):
    """A private shop unique to each player, for purchasing special items intended only for that player.
    Items cannot be sold to Loma.
    """

    def __init__(self, shipsStock: Optional[inventory.DiscountableInventory[shipItem.Ship, shipItem.SerializedShipUnion]] = None,
                    weaponsStock: Optional[inventory.DiscountableInventory[primaryWeapon.PrimaryWeapon, primaryWeapon.SerializedWeaponUnion]] = None,
                    modulesStock: Optional[inventory.DiscountableInventory[moduleItem.ModuleItem, moduleItem.SerializedModuleItemUnion]] = None,
                    turretsStock: Optional[inventory.DiscountableInventory[turretWeapon.TurretWeapon, turretWeapon.SerializedWeaponUnion]] = None,
                    toolsStock: Optional[inventory.DiscountableInventory[toolItem.ToolItem, toolItem.SerializedToolItemUnion]] = None):
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