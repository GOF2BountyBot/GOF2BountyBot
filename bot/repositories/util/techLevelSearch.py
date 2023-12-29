from typing import Optional, TypeVar, Any, List, Type, Union, Protocol, Tuple, Set, Sequence, Generic

from sqlalchemy import select, Select, and_
from sqlalchemy.orm import Mapped
from sqlalchemy.ext.asyncio import AsyncSession

from ...lib.sql import SqlTableExpression, SqlColumnExpression, DeclarativeBaseProtocol


class HasTechLevel(DeclarativeBaseProtocol, Protocol):
    techLevel: Mapped[int]


class HasOptionalTechLevel(DeclarativeBaseProtocol, Protocol):
    techLevel: Mapped[Optional[int]]


TElement = TypeVar("TElement", bound=Union[HasTechLevel, HasOptionalTechLevel], contravariant=True)

class FilterWithKwargs(Protocol, Generic[TElement]):
    def __call__(self, tl: int, tlItems: Sequence[TElement], **kwargs: Any) -> bool: ...


class FilterNoKwargs(Protocol, Generic[TElement]):
    def __call__(self, tl: int, tlItems: Sequence[TElement]) -> bool: ...


async def walkingTlSearch(session: AsyncSession, ElementType: Type[TElement], center: int, minTL: int, maxTL: int, upperBound: int, filter: Union[FilterWithKwargs[TElement], FilterNoKwargs[TElement]], TableExpression: Optional[SqlTableExpression[TElement]] = None, withOnlyFields: Optional[Tuple[SqlColumnExpression[Any], ...]] = None, **kwargs: Any) -> List[TElement]:
    """Attempt to find an integer tl where:
        minTL <= tl <= min(maxTL, center + upperBound)
        filter(tl) == True

    And return all rows of the given type at that tech level. If no matching tech level can be found,
    or no rows exist at the tech level, then an empty array is returned.

    first [minTL... center] will be searched in descending order.
    then, [center + 1... min(maxTL, center + upperBound)] will be searched in ascending order.
    upperBound is provided for convenience, identical behaviour can be made by giving upperBound = 0 and
    maxTL as center + upperBound' where upperBound' is the value which would have been given for upperBound

    :param AsyncSession session: The session in which to query for rows
    :param ElementType: The class of row to query
    :type ElementType: Type[HasTechLevel]
    :param int center: The center of the search, being the upper bound for downward searching and
                        the lower bound for upward searching
    :param int minTL: The lowest bound for searching
    :param int maxTL: The upper bound for searching
    :param int upperBound: The maximum number of steps above center to search
    :param function filter: A function deciding whether or not a tl is acceptible.
                                filter must take two positional arguments, being the tl and the list of rows at
                                that tl, and return a bool. If kwargs are given, they will be passed to filter
    :return: All rows that match a number tl, between minTL and min(maxTL, center + upperBound),
            where filter(tl, tlItems) is True. [] if no such number exists or no rows are found.
    """
    if minTL > maxTL:
        raise ValueError("maxTL must be at least minTL. minTL = " + str(minTL) + ", maxTL = " + str(maxTL))
    if center < minTL or center > maxTL:
        raise ValueError("center must be between minTL and maxTL, inclusive. " \
                            + "minTL = " + str(minTL) + ", maxTL = " + str(maxTL) + ", center = " + str(center))
    if upperBound < 0:
        raise ValueError("upperBound must be at least 0. Given " + str(upperBound))
    
    tl = center
    maxTL = min(maxTL, center + upperBound)

    # Ignoring this warning because pyright doesn't realize that InstrumentedAttribute[Optional[...]] can be None
    query: Select[Tuple[ElementType]] = select(TableExpression or ElementType).where(ElementType.techLevel != None) # type: ignore[reportUnnecessaryComparison]
    query = query.where(and_(ElementType.techLevel >= minTL, ElementType.techLevel <= maxTL)) \
                 .order_by(ElementType.techLevel)
            
    if withOnlyFields:
        query = query.with_only_columns(*withOnlyFields)
    
    rows = await session.execute(query)
    checkedRowIndexes: Set[int] = set()

    def itemsAtTl(tl: int):
        tlItems: List[ElementType] = []
        for i, row in ((i, row) for i, row in enumerate(rows) if i not in checkedRowIndexes):
            checkedRowIndexes.add(i)
            tlItems.append(row.t[0])
        
        return tlItems

    while tl >= minTL:
        tlItems = itemsAtTl(tl)
        if filter(tl, tlItems, **kwargs):
            return tlItems
        tl -= 1
    
    if center < maxTL:
        tl = center + 1
        while tl <= maxTL:
            tlItems = itemsAtTl(tl)
            if filter(tl, tlItems, **kwargs):
                return tlItems
            tl += 1
    
    return []
