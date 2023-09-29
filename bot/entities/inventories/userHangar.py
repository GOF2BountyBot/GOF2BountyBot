from typing import List

from sqlalchemy.orm import Mapped, relationship, mapped_column

from .inventoryListing import InventoryListing
from .inventoryBase import InventoryBase
from ...database.tables import TableNames

from ..items.ship.shipInstance import ShipInstance
from ..items.ship.shipInstance_json import SerializedShipInstanceUnion
from ..items.modules.moduleItem import ModuleItem
from ..items.modules.moduleItem_json import SerializedModuleItemUnion
from ..items.weapons.primaryWeapon import PrimaryWeapon
from ..items.weapons.weapon_json import SerializedWeapon
from ..items.weapons.turretWeapon import TurretWeapon
from ..items.tools.toolItem import ToolItem
from ..items.tools.toolItem_json import SerializedToolItemUnion

class UserHangar(InventoryBase):
    __tablename__ = TableNames.Inventory.value

    id: Mapped[int] = mapped_column(primary_key=True)

    ships: Mapped[List[InventoryListing[ShipInstance, SerializedShipInstanceUnion]]] = relationship()
    modules: Mapped[List[InventoryListing[ModuleItem, SerializedModuleItemUnion]]] = relationship()
    weapons: Mapped[List[InventoryListing[PrimaryWeapon, SerializedWeapon]]] = relationship()
    turrets: Mapped[List[InventoryListing[TurretWeapon, SerializedWeapon]]] = relationship()
    tools: Mapped[List[InventoryListing[ToolItem, SerializedToolItemUnion]]] = relationship()
