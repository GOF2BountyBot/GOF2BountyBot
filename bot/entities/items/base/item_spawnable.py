from typing import Any, Dict, Type, TypeVar

from . import item, item_json


TClass = TypeVar("TClass", bound=Type["item.Item[Any]"])

# A record of all item types that can be deserialized from json.
# Do not access this directly. For proper typing, use the helper methods provided.
SpawnableItemTypesByName: Dict[str, Type["item.Item[Any]"]] = {}
SpawnableItemTypesByType: Dict[Type["item.Item[Any]"], str] = {}

def spawnableItem(cls: TClass) -> TClass:
    """Class decorator. Register an item type as 'spawnable' (json-deserializable).
    This must be applied as a decorator to a `Item` subclass.

    ```py
    from .item import Item
    from .item_spawnable import spawnableItem

    @spawnableItem
    class MyItem(Item):
        ...
    ```
    """
    if cls.__name__ in SpawnableItemTypesByName:
        raise ValueError(f"{SpawnableItemTypesByName[cls.__name__].__qualname__} is already registered as a spawnable class with name {cls.__name__}")
    
    SpawnableItemTypesByName[cls.__name__] = cls
    SpawnableItemTypesByType[cls] = cls.__name__
    return cls


async def spawnItem(data: "item_json.TypedSerializedItem") -> "item.Item[Any]":
    """Json-deserialize an item.
    the `type` field in `data` is required.

    :param data: The json-serialized item
    :type data: TypedSerializedItem
    :raises NameError: If `data` does not contain the item type
    :raises KeyError: If the item type does not correspond to the name of a spawnable item class
    :return: The deserialized item
    :rtype: Item
    """
    if not data.get("type", None):
        raise NameError("Not given a type")
    
    elif data["type"] not in SpawnableItemTypesByName:
        raise KeyError(f"Unrecognised item type: {data['type']}")

    return await SpawnableItemTypesByName[data["type"]].deserialize(data)


def isSpawnableItemClass(cls: Type["item.Item[Any]"]) -> bool:
    """Decide whether a given type is a spawnable item type

    :param cls: The class to test
    :type cls: Type[Item]
    :return: True if `cls` is marked as spawnable, False otherwise
    :rtype: bool
    """
    return cls in SpawnableItemTypesByType


def spawnableItemClassFromName(n: str) -> Type["item.Item[Any]"]:
    """Get the spawnable item class that is called `n`

    :param n: The class name
    :type n: str
    :return: The spawnable class called `n`
    :rtype: Type[Item]
    """
    return SpawnableItemTypesByName[n]