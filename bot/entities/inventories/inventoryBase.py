from typing import Any, Generic, List, Optional, TypeVar

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession

from ...database.tables import TableNames
from . import inventoryListing
from ..items.base.item import Item
from ..items.base.item_json import SerializedItemUnion
from .exceptions import NotStored


class Base(AsyncAttrs, DeclarativeBase):
    pass


TStoredItem = TypeVar("TStoredItem", bound=Item[Any])
TSerializedItem = TypeVar("TSerializedItem", bound=SerializedItemUnion)


class InventoryBase(Base, Generic[TStoredItem, TSerializedItem]):
    __tablename__ = TableNames.Inventory.value

    id: Mapped[int] = mapped_column(primary_key=True)
    _allListings: "Mapped[List[inventoryListing.InventoryListing[TStoredItem, TSerializedItem]]]" = relationship()

    @property
    async def allListings(self) -> List["inventoryListing.InventoryListing[TStoredItem, TSerializedItem]"]:
        """All item listings in the inventory, of any type.
        This property must be awaited.
        """
        return await self.awaitable_attrs.allListings
    

    @allListings.setter
    def allListings(self, value: List["inventoryListing.InventoryListing[TStoredItem, TSerializedItem]"]):
        self._allListings = value


    async def isEmpty(self, session: AsyncSession) -> bool:
        query = select(inventoryListing.InventoryListing) \
            .where(inventoryListing.InventoryListing.inventoryId == self.id) \
            .with_only_columns(inventoryListing.InventoryListing.id)
        result = await session.execute(query)
        return result.first() is None

    
    async def add(self, session: AsyncSession, item: TStoredItem, quantity: int = 1) -> "inventoryListing.InventoryListing[TStoredItem, TSerializedItem]":
        query = \
            select(inventoryListing.InventoryListing[type(item), TSerializedItem]) \
            .where(and_(
                inventoryListing.InventoryListing.inventoryId == self.id,
                inventoryListing.InventoryListing.itemId == item.id)
            )
        
        result = await session.execute(query)
    
        row = result.one_or_none()

        if row is not None:
            listing = row.t[0]
            listing.quantity += quantity
        
        else:
            listing = inventoryListing.InventoryListing[TStoredItem, TSerializedItem](
                inventoryId=self.id,
                quantity=quantity,
                itemType=item._storeableItemType, # type: ignore[reportPrivateUsage]
                itemId=item.id,
                item=item
            )

            session.add(listing)

        return listing
    

    async def remove(self, session: AsyncSession, item: TStoredItem, quantity: int = 1) -> Optional["inventoryListing.InventoryListing[TStoredItem, SerializedItemUnion]"]:
        query = select(inventoryListing.InventoryListing[type(item), TSerializedItem]) \
            .where(and_(
                inventoryListing.InventoryListing.inventoryId == self.id,
                inventoryListing.InventoryListing.itemId == item.id)
            )
        
        result = await session.execute(query)
    
        row = result.one_or_none()

        if row is None:
            raise NotStored(self.id, item.id, quantity, 0)

        listing = row.t[0]

        if listing.quantity < quantity:
            raise NotStored(self.id, item.id, quantity, listing.quantity)
        
        if listing.quantity == quantity:
            await session.delete(listing)
            return None

        listing.quantity -= quantity
        return listing
