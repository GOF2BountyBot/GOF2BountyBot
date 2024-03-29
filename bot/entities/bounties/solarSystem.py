from typing import Any, Tuple, TypeVar, Generic, List

import math

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.ext.hybrid import hybrid_property

from ...database.tables import TableNames
from ...baseClasses.aliasable import AliasableMixin
from ...baseClasses.wikiEntity import SqlNamedWikiEntity
from .solarSystem_json import SerializedSolarSystem
from ...baseClasses.embedFillable import embedColour, embedField, embedFooterUrl
from ...cfg import cfg

class Base(DeclarativeBase):
    pass

SystemsAreNeighbours = Table(
    TableNames.UserHasMedal.value,
    Base.metadata,
    Column("systemId", Integer, ForeignKey(f"{TableNames.SolarSystem.value}.id"), primary_key=True),
    Column("system2Id", Integer, ForeignKey(f"{TableNames.SolarSystem.value}.id"), primary_key=True)
)

TSchema = TypeVar("TSchema", bound=SerializedSolarSystem)

class SolarSystem(Base, AliasableMixin[TSchema], SqlNamedWikiEntity, Generic[TSchema]):
    __tablename__ = TableNames.SolarSystem.value

    id: Mapped[int] = mapped_column(primary_key=True)
    faction: Mapped[str]
    security: Mapped[int]
    gridXCoordinate: Mapped[int]
    gridYCoordinate: Mapped[int]
    techLevel: Mapped[int]

    # Eager loaded attribute, no need for asyncattrs
    neighbours: Mapped[List["SolarSystem[TSchema]"]] = relationship(
        secondary=SystemsAreNeighbours,
        primaryjoin="SystemsAreNeighbours.c.system1Id == SolarSystem.id",
        lazy="joined")
    

    @hybrid_property
    def hasTechLevel(self) -> bool:
        return self.techLevel != -1
    

    @hybrid_property
    def hasJumpGate(self) -> bool:
        """Decide whether or not this system has any neighbours.

        :return: True if at least one system can be reached from this one via jump gate, False otherwise
        :rtype: bool
        """
        return len(self.neighbours) != 0


    @hybrid_property
    def coordinates(self) -> Tuple[int, int]:
        return (self.gridXCoordinate, self.gridYCoordinate)


    @embedField("Neighbour Systems")
    @property
    def neighboursStr(self): return ", ".join(i.name.title() for i in self.neighbours) if self.neighbours else "No Jumpgate"


    @embedFooterUrl
    def formattedFaction(self): return (self.faction.title(), self.embedThumbnail())


    @embedField("Security Level")
    @property
    def securityLevelName(self): return bbData.securityLevels[self.security].title()


    @embedColour
    def filledEmbedColour(self): return cfg.factionColourOrDefault(self.faction)


    # @embedThumbnailUrl
    def embedThumbnail(self): return bbData.factionIcons.get(self.faction, None)


    def distanceTo(self, other: "SolarSystem[Any]") -> float:
        """Calculate the straight-line distance from this system to another.

        :param System other: The other system to calculate distance to
        :return: The pythagorean-distance from this system to other
        :rtype: float
        """
        return math.sqrt((other.gridYCoordinate - self.gridYCoordinate) ** 2 \
                            + (other.gridXCoordinate - self.gridXCoordinate) ** 2)


    async def serialize(self, **kwargs: Any) -> TSchema:
        data = await super().serialize(**kwargs)

        data["id"] = self.id
        data["faction"] = self.faction
        data["neighbours"] = [s.id for s in self.neighbours]
        data["security"] = self.security

        if self.hasTechLevel:
            data["techLevel"] = self.techLevel

        return data


    @classmethod
    async def deserialize(cls, data: TSchema, **kwargs: Any) -> "SolarSystem[TSchema]":
        """Factory function constructing a new System object from the information in the given dictionary.

        :param dict sysDict: A dictionary containing all information needed to construct the required System.
        :return: The requested System object
        :rtype: System
        """
        return SolarSystem(**cls._makeDefaults(data, ("type",),))


AnySolarSystem = SolarSystem[SerializedSolarSystem]
