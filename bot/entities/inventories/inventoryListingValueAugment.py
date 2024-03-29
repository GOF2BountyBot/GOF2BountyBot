from __future__ import annotations
from typing import Any

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import ForeignKey

from ...database.tables import TableNames
from ...baseClasses.serializable import SerializesToSchema
from .inventoryListingValueAugment_json import SerializedValueAugment

class Base(DeclarativeBase):
    pass


class InventoryListingValueAugment(Base, SerializesToSchema[SerializedValueAugment]):
    __tablename__ = TableNames.InventoryListingValueAugment.value

    id: Mapped[int] = mapped_column(primary_key=True)
    inventoryListingId: Mapped[int] = mapped_column(ForeignKey(f"{TableNames.InventoryListing.value}.id"))
    multiplier: Mapped[float]
    description: Mapped[str]

    async def serialize(self, **kwargs: Any) -> SerializedValueAugment:
        return {"multiplier": self.multiplier, "description": self.description}
