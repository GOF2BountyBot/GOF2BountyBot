from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from .inventoryBase import Inventory
from ..items.ships.shipItem import Ship
from ..items.ships.shipBase import SerializedShipUnion
from ..items.weapons.primaryWeapon import PrimaryWeapon
from ..items.weapons.turretWeapon import TurretWeapon

from ...lib.sql import AbcSqlTableMeta

class Base(DeclarativeBase):
    pass


class ShipInventory(Base, Inventory[Ship, SerializedShipUnion], metaclass=AbcSqlTableMeta):
    """An inventory of ships.
    """
    __tablename__ = "shipInventory"
    id: Mapped[int] = mapped_column(primary_key=True)


class WeaponInventory(Base, Inventory[Ship, SerializedShipUnion], metaclass=AbcSqlTableMeta):
    """An inventory of weapons.
    """
    __tablename__ = "weaponInventory"
    id: Mapped[int] = mapped_column(primary_key=True)


class ModuleInventory(Base, Inventory[Ship, SerializedShipUnion], metaclass=AbcSqlTableMeta):
    """An inventory of modules.
    """
    __tablename__ = "moduleInventory"
    id: Mapped[int] = mapped_column(primary_key=True)


class TurretInventory(Base, Inventory[Ship, SerializedShipUnion], metaclass=AbcSqlTableMeta):
    """An inventory of turrets.
    """
    __tablename__ = "turretInventory"
    id: Mapped[int] = mapped_column(primary_key=True)


class ToolInventory(Base, Inventory[Ship, SerializedShipUnion], metaclass=AbcSqlTableMeta):
    """An inventory of tools.
    """
    __tablename__ = "toolInventory"
    id: Mapped[int] = mapped_column(primary_key=True)

