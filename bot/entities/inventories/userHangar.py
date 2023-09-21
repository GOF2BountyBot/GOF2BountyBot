from typing import List

from sqlalchemy.orm import Mapped, relationship, mapped_column

from .inventoryListing import InventoryListing
from .inventoryBase import InventoryBase
from ...database.tables import TableNames


class UserHangar(InventoryBase):
    __tablename__ = TableNames.Inventory.value

    id: Mapped[int] = mapped_column(primary_key=True)

    ships: Mapped[List[InventoryListing[ShipInstance]]] = relationship()
    modules: Mapped[List[InventoryListing[Module]]] = relationship()
    weapons: Mapped[List[InventoryListing[PrimaryWeapon]]] = relationship()
    turrets: Mapped[List[InventoryListing[TurretWeapon]]] = relationship()
    tools: Mapped[List[InventoryListing[Tool]]] = relationship()
