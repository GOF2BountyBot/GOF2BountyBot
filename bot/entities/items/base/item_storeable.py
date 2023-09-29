from typing import Any, Dict, Type, TypeVar

from . import item
from ....database.constants import StoreableItemType

TClass = TypeVar("TClass", bound=Type["item.Item[Any]"])

# A record of all storeable item types.
# This is used during dynamic InventoryListing subclass generation.
StoreableItemTypes: Dict[StoreableItemType, Type["item.Item[Any]"]] = {}

def itemType(itemType: StoreableItemType):
    """Class decorator. Register an item type as storeable in an inventory.
    This must be applied as a decorator to an `Item` subclass.

    Items each belong to a category defined by the StoreableItemType enum.
    When an inventory receives an item from the database, it needs to know what type of item it is,
    in order to keep the item in the correct section of the inventory.

    For this reason, direct Item subclasses must be decarated with `itemType`.
    Indirect subclasses will inherit the parent's item type, and therefore be categorized the same in inventories.

    ```py
    from .item import Item
    from .item import itemType
    from ..database.constants import StoreableItemType

    @itemType(StoreableItemType.MyItem)
    class MyItem(Item):
        ...
    ```

    Only one class can be registered for a given StoreableItemType.
    If several classes should be categorized as the same StoreableItemType, they must all inherit from base class
    that is decorated with that StoreableItemType. The SQLAlchemy joined table inheritance pattern will automatically
    ensure that your concrete item types will be mapped from the database.
    """
    def inner(cls: TClass) -> TClass:
        cls._storeableItemType = itemType # type: ignore[reportPrivateUsage]
        if itemType in StoreableItemTypes:
            raise ValueError(f"{StoreableItemTypes[itemType].__qualname__} is already registered as the class for itemType {itemType.name}")
        StoreableItemTypes[itemType] = cls
        return cls
    return inner