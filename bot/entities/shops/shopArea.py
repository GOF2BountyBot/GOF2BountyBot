from typing import Any, List, Optional, Tuple, Type, Union, cast, overload, TypeVar, Generic

from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql._typing import _ColumnsClauseArgument
from sqlalchemy import select, and_

from ..inventories.inventoryListing import InventoryListing
from ..items.base.item import ItemBase
from ..items.itemTransaction import ItemTransactionContext, SupportsItems, SupportsTrading
from . import shopBase

TStoredItem = TypeVar("TStoredItem", bound=ItemBase)
TStoredItemSubclass = TypeVar("TStoredItemSubclass", bound=ItemBase)
TBuyer = TypeVar("TBuyer", bound=Union[SupportsTrading, SupportsItems])
TSeller = TypeVar("TSeller", bound=Union[SupportsTrading, SupportsItems])
TShop = TypeVar("TShop", bound="shopBase.ShopBase")

class ShopArea(Generic[TStoredItem, TShop]):
    """An area of a shop, containing a specific type of item.
    This class simply acts as a proxy to the shop, passing TStoredItem to generic methods.
    """

    listings: Mapped[List[InventoryListing[TStoredItem]]] = relationship()

    def __init__(self, shop: TShop, itemType: Type[TStoredItem], **kw: Any):
        self.itemType = itemType
        self.shop = shop
        super().__init__(**kw)


    async def isEmpty(self, session: AsyncSession) -> bool:
        query = select(InventoryListing[self.itemType]) \
            .where(and_(InventoryListing.inventoryId == self.shop.id, InventoryListing.item.id == id)) \
            .with_only_columns(InventoryListing.id) \

        result = await session.execute(query)
        row = result.one_or_none()
        
        return row is None


    @overload
    async def get(self, session: AsyncSession, id: int, *, withOnlyFields: Optional[Tuple[_ColumnsClauseArgument[TStoredItem], ...]] = None) -> Optional[TStoredItem]:
        """Get an item that is in the shop, by id.

        :param session: The database session from which to look up the item
        :type session: AsyncSession
        :param id: The item id
        :type id: int
        :param withOnlyFields: The InventoryListing fields to select, defaults to all fields
        :type withOnlyFields: Tuple[_ColumnsClauseArgument[TStoredItem], ...], optional
        :return: The item stored in this shop area, if it was found
        :rtype: Optional[TStoredItem]
        """
    
    @overload
    async def get(self, session: AsyncSession, id: int, type: Type[TStoredItemSubclass], withOnlyFields: Optional[Tuple[_ColumnsClauseArgument[TStoredItemSubclass], ...]] = None) -> Optional[TStoredItemSubclass]:
        """Get an item that is in the shop, by id.
        `type` must be a subclass of the stored item type.

        :param session: The database session from which to look up the item
        :type session: AsyncSession
        :param id: The item id
        :type id: int
        :param type: The item subclass to select as
        :type type: Type[TStoredItem], optional
        :param withOnlyFields: The InventoryListing fields to select, defaults to all fields
        :type withOnlyFields: Tuple[_ColumnsClauseArgument[TStoredItem], ...], optional
        :raises TypeError: If `type` is not a subclass of the stored item type
        :return: The item stored in this shop area, if it was found
        :rtype: Optional[TStoredItem]
        """

    async def get(self, session: AsyncSession, id: int, type: Optional[Type[ItemBase]] = None, withOnlyFields: Optional[Tuple[_ColumnsClauseArgument[ItemBase], ...]] = None) -> Optional[ItemBase]:
        if type is None:
            itemType = self.itemType
        elif not issubclass(type, self.itemType):
            raise TypeError(f"Given item type is not stored in this shop area. Must be a subclass of {self.itemType}, given type {type}")
        else:
            itemType = type

        return await self.shop.getItem(session, id, itemType, withOnlyFields)
    

    @overload
    async def getListing(self, session: AsyncSession, id: int, *, withOnlyFields: Optional[Tuple[_ColumnsClauseArgument[InventoryListing[TStoredItem]], ...]] = None) -> Optional[InventoryListing[TStoredItem]]:
        """Get the inventory listing for an item that is in the shop, by item id.

        :param session: The database session from which to look up the item
        :type session: AsyncSession
        :param id: The item id
        :type id: int
        :param withOnlyFields: The InventoryListing fields to select, defaults to all fields
        :type withOnlyFields: Tuple[_ColumnsClauseArgument[TStoredItem], ...], optional
        :return: The inventory listing for the item stored in this shop area, if it was found
        :rtype: Optional[InventoryListing[TStoredItem]]
        """
    
    @overload
    async def getListing(self, session: AsyncSession, id: int, type: Type[TStoredItemSubclass], withOnlyFields: Optional[Tuple[_ColumnsClauseArgument[InventoryListing[TStoredItemSubclass]], ...]] = None) -> Optional[InventoryListing[TStoredItemSubclass]]:
        """Get the inventory listing for an item that is in the shop, by item id.
        `type` must be a subclass of the stored item type.

        :param session: The database session from which to look up the item
        :type session: AsyncSession
        :param id: The item id
        :type id: int
        :param type: The item subclass to select as
        :type type: Type[TStoredItem], optional
        :param withOnlyFields: The InventoryListing fields to select, defaults to all fields
        :type withOnlyFields: Tuple[_ColumnsClauseArgument[TStoredItem], ...], optional
        :raises TypeError: If `type` is not a subclass of the area's stored item type
        :return: The inventory listing for the item stored in this shop area, if it was found
        :rtype: Optional[TStoredItem]
        """

    async def getListing(self, session: AsyncSession, id: int, type: Optional[Type[TStoredItemSubclass]] = None, withOnlyFields: Optional[Tuple[_ColumnsClauseArgument[InventoryListing[TStoredItemSubclass]], ...]] = None) -> Optional[InventoryListing[TStoredItemSubclass]]:
        if type is None:
            itemType = self.itemType
        elif not issubclass(type, self.itemType):
            raise TypeError(f"Given item type is not stored in this shop area. Must be a subclass of {self.itemType}, given type {type}")
        else:
            itemType = type
        
        listing = await self.shop.getListing(session, id, cast(Type[TStoredItemSubclass], itemType), withOnlyFields)

        return listing

#region item buying
        

    async def beginBuyUntyped(self, session: AsyncSession, buyer: TBuyer, id: int, *, quantity: int = 1, withOnlyFields: Optional[Tuple[_ColumnsClauseArgument[InventoryListing[TStoredItem]], ...]] = None) -> ItemTransactionContext[TStoredItem, TBuyer, TShop]:
        """The generic version of this method is recommended where possible. See: `beginBuy`
        
        Begin an item-buying transaction.
        This transaction will remove the appropriate amount of credits from `buyer`, if supported.
        The transaction will not move the item into `buyer`'s inventory.

        Usage example:
        ```py
        async with shop.area.buyItemUntyped(session, buyer, id) as transaction:
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
        :type withOnlyFields: Optional[Tuple[_ColumnsClauseArgument[InventoryListing[ItemBase]], ...]], optional
        :raises NotStored: If not enough of the item is found in the inventory
        :return: A context in which you should move the item to `buyer`'s inventory.
        :rtype: ItemTransactionContext[ItemBase, TBuyer, TSelf]
        """
        return await self.shop.beginBuy(session, buyer, id, self.itemType, quantity, withOnlyFields)


    async def beginBuy(self, session: AsyncSession, buyer: TBuyer, id: int, type: Type[TStoredItemSubclass], quantity: int = 1, withOnlyFields: Optional[Tuple[_ColumnsClauseArgument[InventoryListing[TStoredItemSubclass]], ...]] = None) -> ItemTransactionContext[TStoredItemSubclass, TBuyer, TShop]:
        """Begin an item-buying transaction.
        This transaction will remove the appropriate amount of credits from `buyer`, if supported.
        The transaction will not move the item into `buyer`'s inventory.

        Usage example:
        ```py
        async with shop.area.beginBuy(session, buyer, id, type) as transaction:
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
        :raises TypeError: If `type` is not a subclass of the area's stored item type
        :raises NotStored: If not enough of the item is found in the inventory
        :return: A context in which you should move the item to `buyer`'s inventory.
        :rtype: ItemTransactionContext[TStoredItem, TBuyer, TSelf]
        """
        if type is None:
            itemType = self.itemType
        elif not issubclass(type, self.itemType):
            raise TypeError(f"Given item type is not stored in this shop area. Must be a subclass of {self.itemType}, given type {type}")
        else:
            itemType = type

        return await self.shop.beginBuy(session, buyer, id, cast(Type[TStoredItemSubclass], itemType), quantity, withOnlyFields)
    
#endregion item buying
#region item selling
    

    async def beginSell(self, session: AsyncSession, seller: TSeller, item: TStoredItem, quantity: int = 1) -> ItemTransactionContext[TStoredItem, TShop, TSeller]:
        """Begin an item-selling transaction.
        This transaction will add the appropriate amount of credits to `seller`, if supported.
        The transaction will not remove the item from `buyer`'s inventory.

        Usage example:
        ```py
        async with shop.area.beginSell(session, seller, item) as transaction:
            buyer.inventory.remove(item)
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
        if not isinstance(item, self.itemType):
            raise TypeError(f"Given item type is not stored in this shop area. Must be a subclass of {self.itemType}, given type {type}")
            
        return await self.shop.beginSell(session, seller, item, quantity)

#endregion item selling