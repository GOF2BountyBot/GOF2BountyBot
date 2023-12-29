from typing import Sequence, Type

from ...entities.items.ship.shipSpec import AnyShipSpec


def shipSpecTLHasPrimaries(tl: int, tlItems: Sequence[AnyShipSpec]) -> bool:
    """Decide if at least one ship exists with the given tech level and has at least one primary weapon slot.

    :param int tl: The tech level to search
    :return: True if at least one ship exists with tech level tl and has at least one primary weapon slot. False otherwise
    :rtype: False
    """
    return any(s.maxPrimaries != 0 for s in tlItems)


def itemTlHasType(tl: int, tlItems: Sequence[AnyShipSpec], itemType: Type[AnyShipSpec] = AnyShipSpec) -> bool:
    """Decide if tlItems contains an element of the given type.

    :param int tl: The tech level to search
    :param List[List[Any]] tlItems: A list containing lists of objects to type check
    :param type itemType: The element class to search for
    :return: True if at least one element of the index'th sub-list in db is an instance of itemType, False otherwise
    :rtype: bool
    """
    return any(isinstance(i, itemType) for i in tlItems)


def hasAny(tl: int, tlItems: Sequence[AnyShipSpec]) -> bool:
    """Decide if tlItems contains any elements.

    :param int tl: The tech level to search
    :param List[List[Any]] tlItems: A list containing lists of objects to check
    :return: True if tlItems is not empty, False otherwise
    :rtype: bool
    """
    return len(tlItems) != 0