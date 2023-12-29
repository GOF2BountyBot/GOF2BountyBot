from sqlalchemy.ext.asyncio import AsyncSession

from ..entities.items.ship.shipInstance import AnyShipInstance
from .snowflakeRepository import SnowflakeRepository


class ShipInstanceRepository(SnowflakeRepository[AnyShipInstance]):
    def __init__(self, session: AsyncSession):
        super().__init__(AnyShipInstance, session)
