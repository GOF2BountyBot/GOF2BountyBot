from typing import Any, List, Optional, TypeVar

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


class InventoryBase(Base):
    __tablename__ = TableNames.Inventory.value

    id: Mapped[int] = mapped_column(primary_key=True)
    _allListings: Mapped[List["inventoryListing.InventoryListing[Item[SerializedItemUnion], SerializedItemUnion]"]] = relationship()

    @property
    async def allListings(self) -> List["inventoryListing.InventoryListing[Item[SerializedItemUnion], SerializedItemUnion]"]:
        """All item listings in the inventory, of any type.
        This property must be awaited.
        """
        return await self.awaitable_attrs.allListings
    

    @allListings.setter
    def setAllListings(self, value: List["inventoryListing.InventoryListing[Item[SerializedItemUnion], SerializedItemUnion]"]):
        self._allListings = value


    async def isEmpty(self) -> bool:
        return len(await self.allListings) == 0

    
    async def add(self, session: AsyncSession, item: TStoredItem, quantity: int = 1) -> "inventoryListing.InventoryListing[TStoredItem, SerializedItemUnion]":
        query = select(inventoryListing.InventoryListing[type(item), Any]) \
            .where(and_(
                inventoryListing.InventoryListing.inventoryId == self.id,
                inventoryListing.InventoryListing.itemId == item.id)
            )
        
        result = await session.execute(query)
    
        row = result.one_or_none()

        if row is not None:
            listing: inventoryListing.InventoryListing[TStoredItem, SerializedItemUnion] = row[0]
            listing.quantity += quantity
        
        else:
            listing = inventoryListing.InventoryListing(
                inventoryId=self.id,
                quantity=quantity,
                itemType=item._storeableItemType, # type: ignore[reportPrivateUsage]
                itemId=item.id,
                item=item
            )

            session.add(listing)

        return listing
    

    async def remove(self, session: AsyncSession, item: TStoredItem, quantity: int = 1) -> Optional["inventoryListing.InventoryListing[TStoredItem, SerializedItemUnion]"]:
        query = select(inventoryListing.InventoryListing[type(item), Any]) \
            .where(and_(
                inventoryListing.InventoryListing.inventoryId == self.id,
                inventoryListing.InventoryListing.itemId == item.id)
            )
        
        result = await session.execute(query)
    
        row = result.one_or_none()

        if row is None:
            raise NotStored(self.id, item.id, quantity, 0)

        listing: inventoryListing.InventoryListing[TStoredItem, SerializedItemUnion] = row[0]

        if listing.quantity < quantity:
            raise NotStored(self.id, item.id, quantity, listing.quantity)
        
        if listing.quantity == quantity:
            await session.delete(listing)
            return None

        listing.quantity -= quantity
        return listing
