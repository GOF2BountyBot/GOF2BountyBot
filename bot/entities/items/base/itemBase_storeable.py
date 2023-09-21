from typing import Dict, Type, TypeVar

from . import itemBase
from ....database.constants import StoreableItemType

TClass = TypeVar("TClass", bound=Type["itemBase.ItemBase"])

# A record of all storeable item types.
# This is used during dynamic InventoryListing subclass generation.
StoreableItemTypes: Dict[StoreableItemType, Type["itemBase.ItemBase"]] = {}

def itemType(itemType: StoreableItemType):
    """Class decorator. Register an item type as storeable in an inventory.
    This must be applied as a decorator to a `ItemBase` subclass.

    ```py
    from .itemBase import ItemBase, itemType
    from ..database.constants import StoreableItemType

    @itemType(StoreableItemType.MyItem)
    class MyItem(ItemBase):
        ...
    ```
    """
    def inner(cls: TClass) -> TClass:
        cls._storeableItemType = itemType
        if itemType in StoreableItemTypes:
            raise ValueError(f"{StoreableItemTypes[itemType].__qualname__} is already registered as the class for itemType {itemType.name}")
        StoreableItemTypes[itemType] = cls
        return cls
    return inner