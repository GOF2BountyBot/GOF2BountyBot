from typing import Optional, Sequence, Type, Any

from ...entities.items.base.item import Item
from ...entities.items.modules.moduleItem import ModuleItem
from ...entities.items.ship.shipInstance import AnyShipInstance

def shipTLHasPrimaries(tl: int, tlItems: Sequence[AnyShipInstance]) -> bool:
    """Decide if at least one ship exists with the given tech level and has at least one primary weapon slot.

    :param int tl: The tech level to search
    :return: True if at least one ship exists with tech level tl and has at least one primary weapon slot. False otherwise
    :rtype: False
    """
    return any(s.getMaxPrimaries() != 0 for s in tlItems)


def itemTlHasType(tl: int, tlItems: Sequence[Item[Any]], itemType: Type[Item[Any]] = Item[Any]) -> bool:
    """Decide if tlItems contains an element of the given type.

    :param int tl: The tech level to search
    :param List[List[Any]] tlItems: A list containing lists of objects to type check
    :param type itemType: The element class to search for
    :return: True if at least one element of the index'th sub-list in db is an instance of itemType, False otherwise
    :rtype: bool
    """
    return any(isinstance(i, itemType) for i in tlItems)


def itemTlHasEquippableType(tl: int, tlItems: Sequence[Item[Any]], itemType: Type[ModuleItem[Any]] = ModuleItem[Any],
                            activeShip: Optional[AnyShipInstance] = None) -> bool:
    """Decide if tlItems contains an element of the given type, and the type of that element is an equippable module on
    the given ship.

    :param int tl: The tech level to search
    :param List[List[Any]] tlItems: A list containing lists of objects to type check
    :param type itemType: The element class to search for
    :param Ship activeShip: The ship to test for element equippability
    :return: True if at least one element of the index'th sub-list in db is an instance of itemType and is equippable on
                activeShip, False otherwise
    :rtype: bool
    """
    if activeShip is None: raise ValueError("activeShip cannot be None")
    return any(isinstance(i, itemType) and activeShip.canEquipModuleType(type(i)) for i in tlItems)


def hasAny(tl: int, tlItems: Sequence[Item[Any]]) -> bool:
    """Decide if tlItems contains any elements.

    :param int tl: The tech level to search
    :param List[List[Any]] tlItems: A list containing lists of objects to check
    :return: True if tlItems is not empty, False otherwise
    :rtype: bool
    """
    return len(tlItems) != 0
