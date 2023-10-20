from typing import Any, List, Optional, Tuple, Type, TypedDict, Union, overload, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql._typing import _ColumnsClauseArgument # type: ignore[reportPrivateUsage]
from sqlalchemy import select, and_

from ...database.constants import StoreableItemType
from ..inventories.inventoryListing import InventoryListing
from ..inventories.inventoryListing_json import SerializedInventoryListing
from ..inventories.inventoryBase import InventoryBase
from ..inventories.exceptions import NotStored
from ..items.base.item import Item
from ..items.base.item_json import SerializedItemUnion
from ...lib.exceptions import UnknownItem
from ..items.itemTransaction import ItemTransactionContext, SupportsItems, SupportsTrading
from . import shopArea
from ..items.ship.shipInstance import AnyShipInstance
from ..items.ship.shipInstance_json import SerializedShipInstanceUnion
from ..items.weapons.primaryWeapon import PrimaryWeapon
from ..items.weapons.turretWeapon import TurretWeapon
from ..items.weapons.weapon_json import SerializedWeapon
from ..items.modules.moduleItem import ModuleItem
from ..items.modules.moduleItem_json import SerializedModuleItemUnion
from ..items.tools.toolItem import ToolItem
from ..items.tools.toolItem_json import SerializedToolItem

TStoredItem = TypeVar("TStoredItem", bound=Item[SerializedItemUnion])
TSerializedItem = TypeVar("TSerializedItem", bound=SerializedItemUnion)
TBuyer = TypeVar("TBuyer", bound=Union[SupportsTrading, SupportsItems])
TSeller = TypeVar("TSeller", bound=Union[SupportsTrading, SupportsItems])
TSelf = TypeVar("TSelf", bound="ShopBase")

_INVENTORYLISTING_FIELDS_FOR_ITEM = (InventoryListing.inventoryId, InventoryListing.item, InventoryListing.itemId, InventoryListing.itemType)
_INVENTORYLISTING_FIELDS_FOR_ITEM_WITH_QUANTITY = _INVENTORYLISTING_FIELDS_FOR_ITEM + (InventoryListing.quantity,)

def mergeListingFieldsForItemSelect(withOnlyFields: Optional[Tuple[_ColumnsClauseArgument[InventoryListing[TStoredItem, TSerializedItem]], ...]], quantity: bool = False) -> Tuple[_ColumnsClauseArgument[InventoryListing[TStoredItem, TSerializedItem]], ...]:
    """Extend an optional list of column specifiers such that it also includes all fields necessary to retrieve the item in an InventoryListing.

    :param withOnlyFields: The base column specifiers
    :type withOnlyFields: Optional[Tuple[_ColumnsClauseArgument[TStoredItem], ...]]
    :param quantity: Include the listing quantity in the select, defaults to False
    :type quantity: bool
    :return: A list of the InventoryListing columns that are necessary to retrieve its item, plus any specified in `withOnlyFields`
    :rtype: Tuple[_ColumnsClauseArgument[TStoredItem], ...]
    """
    requiredFields = _INVENTORYLISTING_FIELDS_FOR_ITEM_WITH_QUANTITY if quantity else _INVENTORYLISTING_FIELDS_FOR_ITEM
    if not withOnlyFields:
        return requiredFields
    
    newFields = tuple(f for f in requiredFields if f not in withOnlyFields)
    return withOnlyFields + newFields


class SerializedShopBase(TypedDict):
    shipsStock: List[SerializedInventoryListing[SerializedShipInstanceUnion]]
    weaponsStock: List[SerializedInventoryListing[SerializedWeapon]]
    modulesStock: List[SerializedInventoryListing[SerializedModuleItemUnion]]
    turretsStock: List[SerializedInventoryListing[SerializedWeapon]]
    toolsStock: List[SerializedInventoryListing[SerializedToolItem]]


class ShopBase(InventoryBase, SupportsItems):
    def __init__(self, **kw: Any):
        super().__init__(**kw)
        self.ships = shopArea.ShopArea(self, AnyShipInstance, id=self.id)
        self.modules = shopArea.ShopArea(self, ModuleItem, id=self.id)
        self.weapons = shopArea.ShopArea(self, PrimaryWeapon, id=self.id)
        self.turrets = shopArea.ShopArea(self, TurretWeapon, id=self.id)
        self.tools = shopArea.ShopArea(self, Tool, id=self.id)


    def getInventory(self, itemType: StoreableItemType):
        """Needed to conform with the SupportsItems protocol. Get the inventory that stores a particular type of item.
        """
        if itemType is StoreableItemType.ship:
            return self.ships
        elif itemType is StoreableItemType.module:
            return self.modules
        elif itemType is StoreableItemType.primaryWeapon:
            return self.weapons
        elif itemType is StoreableItemType.turret:
            return self.turrets
        elif itemType is StoreableItemType.tool:
            return self.tools
        else:
            raise ValueError(f"item type {itemType} is not stored in this shop")
        

    @overload
    def getArea(self: TSelf, item: StoreableItemType) -> shopArea.ShopArea[Item, TSelf]:
        """Get the shop area that buys and sells the given item type.

        :param item: The item type whose shop area to get
        :type item: StoreableItemType
        :return: The area of the shop that handles `item`s
        :rtype: shopArea.ShopArea[Item, TSelf]
        """

    @overload
    def getArea(self: TSelf, item: Union[TStoredItem, Type[TStoredItem]]) -> shopArea.ShopArea[TStoredItem, TSelf]:
        """Get the shop area that buys and sells the given item type.

        :param item: The item type whose shop area to get
        :type item: Union[Item, Type[Item]]
        :return: The area of the shop that handles `item`s
        :rtype: shopArea.ShopArea[Item, TSelf]
        """

    def getArea(self: TSelf, item: Union[StoreableItemType, TStoredItem, Type[TStoredItem]]) -> shopArea.ShopArea[TStoredItem, TSelf]:
        if isinstance(item, StoreableItemType):
            return self.getInventory(item)
        return self.getInventory(item._storeableItemType)


    @overload
    async def getItem(self, session: AsyncSession, id: int, *, withOnlyFields: Optional[Tuple[_ColumnsClauseArgument[Item], ...]] = None) -> Optional[Item]:
        """Get an item that is in the shop, by id.

        :param session: The database session from which to look up the item
        :type session: AsyncSession
        :param id: The item id
        :type id: int
        :param withOnlyFields: The InventoryListing fields to select, defaults to all fields
        :type withOnlyFields: Tuple[_ColumnsClauseArgument[Item], ...], optional
        :return: The item stored in this shop, if it was found
        :rtype: Optional[Item]
        """
    
    @overload
    async def getItem(self, session: AsyncSession, id: int, type: Type[TStoredItem], withOnlyFields: Optional[Tuple[_ColumnsClauseArgument[TStoredItem], ...]] = None) -> Optional[TStoredItem]:
        """Get an item that is in the shop, by id.

        :param session: The database session from which to look up the item
        :type session: AsyncSession
        :param id: The item id
        :type id: int
        :param type: The item subclass to select as
        :type type: Type[TStoredItem], optional
        :param withOnlyFields: The item fields to select, defaults to all fields
        :type withOnlyFields: Tuple[_ColumnsClauseArgument[TStoredItem], ...], optional
        :return: The item stored in this shop, if it was found
        :rtype: Optional[TStoredItem]
        """

    async def getItem(self, session: AsyncSession, id: int, type: Optional[Type[Item]] = None, withOnlyFields: Optional[Tuple[_ColumnsClauseArgument[Item], ...]] = None) -> Optional[Item]:
        """There are two implementations
        """
        itemType = Item if type is None else type
        
        query = select(itemType) \
            .join(InventoryListing[itemType].item, InventoryListing[itemType].itemId == itemType.id) \
            .where(and_(InventoryListing.inventoryId == self.id, InventoryListing.item.id == id)) \
            .with_only_columns(*withOnlyFields)

        result = await session.execute(query)
        row = result.one_or_none()
        
        return None if row is None else row.t[0]
    

    @overload
    async def getListing(self, session: AsyncSession, id: int, *, withOnlyFields: Optional[Tuple[_ColumnsClauseArgument[InventoryListing[Item]], ...]] = None) -> Optional[InventoryListing[Item]]:
        """Get the inventory listing for an item that is in the shop, by item id.

        :param session: The database session from which to look up the item
        :type session: AsyncSession
        :param id: The item id
        :type id: int
        :param withOnlyFields: The InventoryListing fields to select, defaults to all fields
        :type withOnlyFields: Tuple[_ColumnsClauseArgument[Item], ...], optional
        :return: The inventory listing for the item stored in this shop, if it was found
        :rtype: Optional[InventoryListing[Item]]
        """
    
    @overload
    async def getListing(self, session: AsyncSession, id: int, type: Type[TStoredItem], withOnlyFields: Optional[Tuple[_ColumnsClauseArgument[InventoryListing[TStoredItem]], ...]] = None) -> Optional[InventoryListing[TStoredItem]]:
        """Get the inventory listing for an item that is in the shop, by item id.

        :param session: The database session from which to look up the item
        :type session: AsyncSession
        :param id: The item id
        :type id: int
        :param type: The item subclass to select as
        :type type: Type[TStoredItem], optional
        :param withOnlyFields: The InventoryListing fields to select, defaults to all fields
        :type withOnlyFields: Tuple[_ColumnsClauseArgument[TStoredItem], ...], optional
        :return: The inventory listing for the item stored in this shop, if it was found
        :rtype: Optional[TStoredItem]
        """

    async def getListing(self, session: AsyncSession, id: int, type: Optional[Type[TStoredItem]] = None, withOnlyFields: Optional[Tuple[_ColumnsClauseArgument[InventoryListing[Item]], ...]] = None) -> Optional[InventoryListing[TStoredItem]]:
        itemType = Item if type is None else type

        query = select(InventoryListing[itemType]) \
            .where(and_(InventoryListing.inventoryId == self.id, InventoryListing.item.id == id))

        if withOnlyFields:
            query = query.with_only_columns(*withOnlyFields)

        result = await session.execute(query)
        row = result.one_or_none()
        
        return None if row is None else row.t[0]

#region item buying

    def buyItemValueIntercept(self, item: Item, value: int) -> int:
        """Overloadable augment of an item's value when buying it from this shop.

        :param item: The item being bought
        :type item: Item
        :param value: The base value of the item
        :type value: int
        :return: The new buying price for the item
        :rtype: int
        """
        return value
    

    @overload
    async def buyItemCheck(self, itemId: int, /, suppliedCredits: int, session: AsyncSession) -> bool:
        """Check whether an amount of credits is enough to buy a particular item.

        :param itemId: The id of the item whose price to check
        :type itemId: int
        :param suppliedCredits: The amount of credits that are available to the buyer
        :type suppliedCredits: int
        :param session: The database session in which to look up the item
        :type session: AsyncSession
        :raises UnknownItem: If `itemId` does not correspond to an item in this inventory
        :return: True if suppliedCredits is within the item's price, False otherwise
        :rtype: bool
        """

    @overload
    async def buyItemCheck(self, item: Item, /, suppliedCredits: int) -> bool:
        """Check whether an amount of credits is enough to buy a particular item.

        :param item: The item whose price to check
        :type item: Item
        :param suppliedCredits: The amount of credits that are available to the buyer
        :type suppliedCredits: int
        :return: True if suppliedCredits is within the item's price, False otherwise
        :rtype: bool
        """

    async def buyItemCheck(self, itemOrId: Union[int, Item], /, suppliedCredits: int, session: Optional[AsyncSession] = None) -> bool:
        """Check whether an amount of credits is enough to buy a particular item.

        :param itemOrId: The item, or the id of the item, whose price to check
        :type itemOrId: Union[int, Item]
        :param suppliedCredits: The amount of credits that are available to the buyer
        :type suppliedCredits: int
        :param session: The database session in which to look up the item
        :type session: AsyncSession
        :raises UnknownItem: If `itemOrId` is an id, but does not correspond to an item in this inventory
        :raises TypeError: If `itemOrId` is an id, but `session` was not provided
        :return: True if suppliedCredits is within the item's price, False otherwise
        :rtype: bool
        """
        if isinstance(itemOrId, int):
            if session is None:
                raise TypeError("A session is required if item is given by id. Found session = None.")
            
            itemAttempt = await self.getItem(session, itemOrId)
            if itemAttempt is None:
                raise UnknownItem(itemOrId)
            
            itemOrId = itemAttempt

        return suppliedCredits <= self.buyItemValueIntercept(itemOrId, await itemOrId.getValue())
    

    async def _beginBuyItemFromListing(self: TSelf, session: AsyncSession, buyer: TBuyer, id: int, quantity: int, listing: Optional[InventoryListing[TStoredItem]]) -> ItemTransactionContext[TStoredItem, TBuyer, TSelf]:
        if listing is None:
            raise NotStored(self.id, id, quantity, 0)
        if quantity > 1 and listing.quantity < quantity:
            raise NotStored(self.id, id, quantity, listing.quantity)
        
        itemPrice = self.buyItemValueIntercept(listing.item, await listing.item.getValue())
        buyTransaction = ItemTransactionContext(buyer, self, listing.item, quantity=quantity, pricePerItem=itemPrice)
        
        async def retrieveItem(transaction):
            await self.remove(session, listing.item, quantity=quantity)

        async def replaceItem(transaction):
            await self.add(session, listing.item, quantity=quantity)

        buyTransaction.addPostBuyStep(retrieveItem, replaceItem)

        if isinstance(buyer, SupportsTrading):
            async def removeCredits(transaction):
                buyer.credits -= await buyTransaction.value()

            async def replaceCredits(transaction):
                buyer.credits += await buyTransaction.value()

            buyTransaction.addPostBuyStep(removeCredits, replaceCredits)

        return buyTransaction
        

    async def beginBuyUntyped(self: TSelf, session: AsyncSession, buyer: TBuyer, id: int, *, quantity: int = 1, withOnlyFields: Optional[Tuple[_ColumnsClauseArgument[InventoryListing[Item]], ...]] = None) -> ItemTransactionContext[Item, TBuyer, TSelf]:
        """The generic version of this method is recommended where possible. See: `beginBuy`
        
        Begin an item-buying transaction.
        This transaction will remove the appropriate amount of credits from `buyer`, if supported.
        The transaction will not move the item into `buyer`'s inventory.

        Usage example:
        ```py
        async with shop.buyItemUntyped(session, buyer, id) as transaction:
            buyer.inventory.add(transaction.item)
        ```

        :param session: The database session to use to look up the item
        :type session: AsyncSession
        :param buyer: The entity buying the item
        :type buyer: TBuyer
        :param id: The id of the item to buy
        :type id: int
        :param quantity: The amount of the item to buy, defaults to 1
        :type quantity: int, optional
        :param withOnlyFields: Limit the inventory listing SELECT to these fields only, defaults to None
        :type withOnlyFields: Optional[Tuple[_ColumnsClauseArgument[InventoryListing[Item]], ...]], optional
        :raises NotStored: If not enough of the item is found in the inventory
        :return: A context in which you should move the item to `buyer`'s inventory.
        :rtype: ItemTransactionContext[Item, TBuyer, TSelf]
        """
        if quantity < 1:
            raise ValueError(f"quantity must be at least 1, given {quantity}")

        withOnlyFields = mergeListingFieldsForItemSelect(withOnlyFields, quantity=quantity > 1)
        listing = await self.getListing(session, id, withOnlyFields=withOnlyFields)
        return await self._beginBuyItemFromListing(session, buyer, id, quantity, listing)


    async def beginBuy(self: TSelf, session: AsyncSession, buyer: TBuyer, id: int, type: Type[TStoredItem], quantity: int = 1, withOnlyFields: Optional[Tuple[_ColumnsClauseArgument[InventoryListing[TStoredItem]], ...]] = None) -> ItemTransactionContext[TStoredItem, TBuyer, TSelf]:
        """Begin an item-buying transaction.
        This transaction will remove the appropriate amount of credits from `buyer`, if supported.
        The transaction will not move the item into `buyer`'s inventory.

        Usage example:
        ```py
        async with shop.beginBuy(session, buyer, id, type) as transaction:
            buyer.inventory.add(transaction.item)
        ```

        :param session: The database session to use to look up the item
        :type session: AsyncSession
        :param buyer: The entity buying the item
        :type buyer: TBuyer
        :param id: The id of the item to buy
        :type id: int
        :param type: The type of item to buy
        :type type: Type[TStoredItem]
        :param quantity: The amount of the item to buy, defaults to 1
        :type quantity: int, optional
        :param withOnlyFields: Limit the inventory listing SELECT to these fields only, defaults to None
        :type withOnlyFields: Optional[Tuple[_ColumnsClauseArgument[InventoryListing[TStoredItem]], ...]], optional
        :raises NotStored: If not enough of the item is found in the inventory
        :return: A context in which you should move the item to `buyer`'s inventory.
        :rtype: ItemTransactionContext[TStoredItem, TBuyer, TSelf]
        """
        if quantity < 1:
            raise ValueError(f"quantity must be at least 1, given {quantity}")
        
        withOnlyFields = mergeListingFieldsForItemSelect(withOnlyFields, quantity=quantity > 1)
        listing = await self.getListing(session, id, type, withOnlyFields=withOnlyFields)
        return await self._beginBuyItemFromListing(session, buyer, id, quantity, listing)
    
#endregion item buying
#region item selling

    def sellItemValueIntercept(self, item: Item, value: int) -> int:
        """Overloadable augment of an item's value when selling it to this shop.

        :param item: The item being sold
        :type item: Item
        :param value: The base value of the item
        :type value: int
        :return: The new selling price for the item
        :rtype: int
        """
        return value
    

    async def beginSell(self: TSelf, session: AsyncSession, seller: TSeller, item: TStoredItem, quantity: int = 1) -> ItemTransactionContext[TStoredItem, TSelf, TSeller]:
        """Begin an item-selling transaction.
        This transaction will add the appropriate amount of credits to `seller`, if supported.
        The transaction will not remove the item from `buyer`'s inventory.

        Usage example:
        ```py
        async with shop.beginSell(session, seller, item, quantity=5) as transaction:
            buyer.inventory.remove(item, quantity=5)
        ```

        :param session: The database session to use to look up the item
        :type session: AsyncSession
        :param seller: The entity selling the item
        :type seller: TSeller
        :param item: The item to sell
        :type item: TStoredItem
        :param quantity: The amount of the item to sell, defaults to 1
        :type quantity: int, optional
        :raises NotStored: If not enough of the item is found in the inventory
        :return: A context in which you should move the item to `buyer`'s inventory.
        :rtype: ItemTransactionContext[TStoredItem, TBuyer, TSelf]
        """
        if quantity < 1:
            raise ValueError(f"quantity must be at least 1, given {quantity}")

        itemPrice = self.sellItemValueIntercept(item, await item.getValue())
        sellTransaction = ItemTransactionContext(self, seller, item, quantity=quantity, pricePerItem=itemPrice)
        
        async def addItem(transaction):
            await self.add(session, item, quantity=quantity)

        async def removeItem(transaction):
            await self.remove(session, item, quantity=quantity)

        sellTransaction.addPostBuyStep(addItem, removeItem)

        if isinstance(seller, SupportsTrading):
            async def removeCredits(transaction):
                seller.credits -= await sellTransaction.value()

            async def addCredits(transaction):
                seller.credits += await sellTransaction.value()

            sellTransaction.addPostBuyStep(addCredits, removeCredits)

        return sellTransaction

#endregion item selling

    def serialize(self, **kwargs) -> SerializedShopBase:
        """Get a dictionary containing all information needed to reconstruct this shop instance.
        This includes maximum item counts, and current stocks.

        :return: A dictionary containing all information needed to reconstruct this shop object
        :rtype: dict
        """
        if not kwargs.get("saveType", False):
            kwargs["saveType"] = True

        data: SerializedShopBase = {"shipsStock": [], "weaponsStock": [], "modulesStock": [], "turretsStock": [], "toolsStock": []}
        
        for invType in [ItemCategory.ship, ItemCategory.weapon, ItemCategory.module, ItemCategory.turret, ItemCategory.tool]:
            stockDict = []
            currentStock = self.getStock(invType)

            for currentItem in currentStock.keys:
                if currentItem in currentStock.items:
                    stockDict.append(currentStock.items[currentItem].serialize(**kwargs))
                else:
                    botState.client.logger.log(type(self).__name__, ShopBase.serialize.__name__,
                                "Failed to save invalid " + invType.value + " key '" + str(currentItem) \
                                    + "' - not found in items dict",
                                category=LogCategory.shop, eventType="UNKWN_KEY")

            data[invType.value + "sStock"] = stockDict

        return data


    @classmethod
    @abstractmethod
    def deserialize(cls: Type[TSelf], shopDict: SerializedShopBase, **kwargs) -> TSelf:
        """Recreate a guildShop instance from its dictionary-serialized representation - the opposite of guildShop.serialize
        A default implementation is provided here, to load plain old Inventory objects.
        For inventories with a different listing type, you could copy paste this with your new listing type.

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
                for listingDict in cast(List[JsonType], shopDict[key]):
                    # I can't find a way to convince pyright that each tuple in the the params only contains matching types,
                    # Even if I cast the items in the tuple!
                    stock.addItem(deserializer.deserialize(listingDict["item"], **kwargs), # type: ignore[reportGeneralTypeIssues]
                                    quantity=cast(int, listingDict["count"]))

        return cls(shipsStock=shipsStock, weaponsStock=weaponsStock, modulesStock=modulesStock,
                            turretsStock=turretsStock, toolsStock=toolsStock)
