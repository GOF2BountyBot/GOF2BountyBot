from typing import Optional

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from sqlalchemy.ext.hybrid import hybrid_property

from ...database.tables import TableNames
from . import solarSystem

class Base(DeclarativeBase):
    pass

class BountyRouteEntry(Base):
    __tablename__ = TableNames.BountyRouteEntry.value

    index: Mapped[int] = mapped_column(primary_key=True)
    bountyId: Mapped[int] = mapped_column(ForeignKey(f"{TableNames.Bounty}.id"))
    systemId: Mapped[int] = mapped_column(ForeignKey(f"{TableNames.SolarSystem}.id"), primary_key=True)
    checkedByUserId: Mapped[Optional[int]] = mapped_column(ForeignKey(f"{TableNames.User}.id"))
    
    # This attribute is eagerly loaded, no need for asyncattrs
    system: Mapped[solarSystem.AnySolarSystem] = relationship(lazy="joined")

    @hybrid_property
    def isChecked(self):
        return self.checkedByUserId is not None
