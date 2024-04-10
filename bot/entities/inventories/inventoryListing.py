from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, TypeVar, Generic, Union, cast, overload
from typing_extensions import Never

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, declared_attr
from sqlalchemy import ForeignKey
from sqlalchemy.ext.asyncio import AsyncAttrs

from abc import ABC

from .inventoryListingValueAugment import InventoryListingValueAugment
from ...database.constants import StoreableItemType
from ...database.tables import TableNames
from ..items.base.item import Item
from ..items.base.item_storeable import StoreableItemTypes
from ..items.base.item_json import SerializedItemUnion
from ...lib.sql import AbcSqlTableMeta
from ...baseClasses.serializable import SerializesToSchema
from .inventoryListing_json import SerializedInventoryListing


class Base(AsyncAttrs, DeclarativeBase):
    pass


TStoredItem = TypeVar("TStoredItem", bound=Item[Any])
TItemSerialized = TypeVar("TItemSerialized", bound=SerializedItemUnion)


class InventoryListing(Base, ABC, Generic[TStoredItem, TItemSerialized], SerializesToSchema[SerializedInventoryListing[TItemSerialized]], metaclass=AbcSqlTableMeta):
    """Subclassing is not supported for this class.
    An entry in an item inventory, containing the item reference, the quantity, and an optional **stack** of value augments (e.g discounts).
    This class is generic in the type of stored item.

    Since the type of the stored item is not known at class creation time, InventoryListing has several complications:
        - Ease of accessing the stored item reference from the listing
        - Static typing of the concrete item reference
        - Eager loading of the item reference

    To solve these issues, the generic type parameter is added at the base class level, and populated
    using the SQLAlchemy single table inheritance pattern.
    The inheritance heirarchy consists of concrete, non-generic ItemListing subclasses.
    """
    __tablename__ = TableNames.InventoryListing.value

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    inventoryId: Mapped[int] = mapped_column(ForeignKey(f"{TableNames.Inventory.value}.id"))

    _valueAugments: Mapped[List[InventoryListingValueAugment]] = relationship()
    quantity: Mapped[int]

    itemType: Mapped[StoreableItemType]
    itemId: Mapped[int] = mapped_column(ForeignKey(f"{TableNames.AllItems.value}.id"))
    item: Mapped[TStoredItem] = relationship(lazy='joined')

    @declared_attr.directive
    def __mapper_args__(cls) -> Dict[str, Any]:
        return {
            "polymorphic_on": cls.itemType,
        }
    

    @property
    async def valueAugments(self) -> List[InventoryListingValueAugment]:
        return await self.awaitable_attrs._valueAugments
    

    @valueAugments.setter
    def setValueAugments(self, value: List[InventoryListingValueAugment]):
        self._valueAugments = value


    def __init__(self,
                 inventoryId: Optional[int],
                 quantity: Optional[int],
                 itemType: Optional[StoreableItemType],
                 itemId: Optional[int],
                 item: Optional[TStoredItem],
                 **kw: Any):
        
        super().__init__(inventoryId=inventoryId, quantity=quantity, itemType=itemType, itemId=itemId, item=item, **kw)
    

    async def serialize(self, **kwargs: Any) -> SerializedInventoryListing[TItemSerialized]:
        """Return a dictionary description of this inventory listing.

        :return: A dictionary identifying the object stored, and the amount
        :rtype: int
        """
        # Casting here with the assumption that TItemSerialized is the serialized form of TItem
        serialized = cast(TItemSerialized, await self.item.serialize(**kwargs))
        data: SerializedInventoryListing[TItemSerialized] = {"item": serialized, "count": self.quantity}
        if len(await self.valueAugments) > 0:
            data["valueAugments"] = [
                await a.serialize(**kwargs) for a in await self.valueAugments
            ]
        return data


    @classmethod
    def deserialize(cls, data: SerializedInventoryListing[TItemSerialized], **kwargs: Any) -> Never: # type: ignore[reportUnknownParameterType] return type being unknown is fine here
        raise NotImplementedError("Cannot deserialize on InventoryListing in the general case. " \
                                    + "Instead instance InventoryListing with your deserialized item object.")


AnyInventoryListing = InventoryListing[Item[Any], SerializedItemUnion]

ListingTypes: Dict[Type[Item[Any]], Type[InventoryListing[Item[Any], SerializedItemUnion]]] = {}


# Dynamically create concrete subclasses for each item type.
# We do this to enable the SQLAlchemy single table inheritance pattern.
# InventoryListing is generic in the stored item type, but SQLAlchemy can only infer the type from the discriminator column,
# not the generic type parameter. Therefore, we associate each discriminator value with its own non-generic type.
for itemType, itemTypeClass in StoreableItemTypes.items():
    __mapper_args__ = {
            "polymorphic_identity": itemType.value,
        }
    
    ListingTypes[itemTypeClass] = type(
        f"{itemTypeClass.__name__}InventoryListing",
        (InventoryListing[itemTypeClass, SerializedItemUnion],),
        {"__mapper_args__": __mapper_args__}
    )


@overload
def inventoryListingType(storedItemType: Type[TStoredItem]) -> Type[InventoryListing[TStoredItem, SerializedItemUnion]]:
    """Given a stored item type `MyItem`, get a concrete, non-generic InventoryListing subclass that stores `MyItem`s.

    :param storedItemType: The item type that the listing type should store. This is what would be given as the generic type parameter.
    :type storedItemType: Type[StoreableItem]
    :return: A type `MyItemInventoryListing`, that represents `InventoryListing[storedItemType]`.
    :rtype: Type[InventoryListing[storedItemType]]
    """

@overload
def inventoryListingType(storedItemType: StoreableItemType) -> Type[InventoryListing[Item[Any], SerializedItemUnion]]:
    """Given a stored item type `MyItem`, get a concrete, non-generic InventoryListing subclass that stores `MyItem`s.
    It is recommended to use the generic overload of this function where possible, to enable proper typing.

    :param storedItemType: The identifier for the item type that the listing type should store. This indentifies what would be given as the generic type parameter.
    :type storedItemType: StoreableItemType
    :return: A type `MyItemInventoryListing`, that represents `InventoryListing[MyItem]`, where `MyItem` is the class identified by `storedItemType`
    :rtype: Type[InventoryListing[StoreableItem]]
    """

def inventoryListingType(storedItemType: Union[Type[Item[Any]], StoreableItemType]) -> Type[InventoryListing[Any, SerializedItemUnion]]:
    if isinstance(storedItemType, StoreableItemType):
        return ListingTypes[StoreableItemTypes[storedItemType]]
    return ListingTypes[storedItemType]
