from typing import Optional, Any, List, Union, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from ..entities.items.ship.shipSpec import AnyShipSpec
from .snowflakeRepository import SnowflakeRepository
# I want this to be exposed with the module for convenience (Should really be done with __all__)
from .util import shipSpecTechLevelSearchFilters as ShipSpecFilter # type: ignore[reportUnusedImport]
from .util.techLevelSearch import walkingTlSearch, FilterNoKwargs, FilterWithKwargs
from ..lib.sql import SqlColumnExpression


class ShipSpecRepository(SnowflakeRepository[AnyShipSpec]):
    def __init__(self, session: AsyncSession):
        super().__init__(AnyShipSpec, session)


    async def walkingTlSearch(self, center: int, minTL: int, maxTL: int, upperBound: int, filter: Union[FilterWithKwargs[AnyShipSpec], FilterNoKwargs[AnyShipSpec]], withOnlyFields: Optional[Tuple[SqlColumnExpression[Any], ...]] = None, **kwargs: Any) -> List[AnyShipSpec]:
        """Attempt to find an integer tl where:
            minTL <= tl <= min(maxTL, center + upperBound)
            filter(tl) == True

        And return all ShipSpecs of the given type at that tech level. If no matching tech level can be found,
        or no ShipSpecs exist at the tech level, then an empty array is returned.

        first [minTL... center] will be searched in descending order.
        then, [center + 1... min(maxTL, center + upperBound)] will be searched in ascending order.
        upperBound is provided for convenience, identical behaviour can be made by giving upperBound = 0 and
        maxTL as center + upperBound' where upperBound' is the value which would have been given for upperBound

        :param int center: The center of the search, being the upper bound for downward searching and
                            the lower bound for upward searching
        :param int minTL: The lowest bound for searching
        :param int maxTL: The upper bound for searching
        :param int upperBound: The maximum number of steps above center to search
        :param function filter: A function deciding whether or not a tl is acceptible.
                                    filter must take two positional arguments, being the tl and the list of ShipSpecs at
                                    that tl, and return a bool. If kwargs are given, they will be passed to filter
        :return: All ShipSpecs that match a number tl, between minTL and min(maxTL, center + upperBound),
                where filter(tl, tlItems) is True. [] if no such number exists or no ShipSpecs are found.
        """
        return await walkingTlSearch(self.session, AnyShipSpec, center, minTL, maxTL, upperBound, filter, withOnlyFields=withOnlyFields, **kwargs)
