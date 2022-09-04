# Typing imports
from __future__ import annotations
from typing import List, Optional, Tuple, Union, cast
import math
from typing_extensions import NotRequired

from ..gameObject import LoadedObject, SerializedLoadedObject
from ...baseClasses import aliasable
from ...baseClasses.serializable import SerializesToSchema

class BuiltInSerializedSolarSystem(aliasable.SerializedAliasable, SerializedLoadedObject): pass

class TypedBuiltInSerializedSolarSystem(BuiltInSerializedSolarSystem):
    type: str

class CustomSerializedSolarSystem(BuiltInSerializedSolarSystem):
    faction: str
    neighbours: List[str]
    security: int
    coordinates: Tuple[int, int]
    wiki: NotRequired[str]
    techLevel: NotRequired[int]

class TypedCustomSerializedSolarSystem(CustomSerializedSolarSystem, TypedBuiltInSerializedSolarSystem): pass

BuiltInSerializedSolarSystemUnion = Union[BuiltInSerializedSolarSystem, TypedBuiltInSerializedSolarSystem]
CustomSerializedSolarSystemUnion = Union[CustomSerializedSolarSystem, TypedCustomSerializedSolarSystem]
SerializedSolarSystemUnion = Union[BuiltInSerializedSolarSystem, TypedBuiltInSerializedSolarSystem, CustomSerializedSolarSystem, TypedCustomSerializedSolarSystem]


class SolarSystem(aliasable.AliasableMixin, LoadedObject, SerializesToSchema[SerializedSolarSystemUnion]):
    """A solar system where a bounty may be located.

    :var name: The name of this system
    :vartype name: str
    :var faction: The faction that owns the system, if any
    :vartype faction: str
    :var neighbours: A list of system names that can be reached from this system's jump gate
    :vartype neighbours: list[str]
    :var security: An integer from 0 to 3 indicating the security of this system. 0 => secure, 3 => dangerous.
                    Security levels are configurable in bbConfig.securityLevels
    :vartype security: int
    :var coordinates: A two int tuple representing the system's position in the galaxy.
                        The grid can be viewed in bbData.mapImageWithGraphLink
    :vartype coordinates: tuple[int, int]
    :var wiki: A web page to display as the system's wiki article, if any
    :vartype wiki: str
    :var hasWiki: Whether or not this system's wiki attribute is populated
    :vartype hasWiki: bool
    :var techLevel: The tech level of the system, indicating the typical tech level of items that can be found here
                    - this currently has no behaviour, and is used only for lore.
    :vartype techLevel: int
    :var hasTechLevel: Whether or not this system's techLevel attribute is populated
    :vartype hasTechLevel: bool
    """

    def __init__(self, name: str, faction: str, neighbours: List[str], security: int,
            coordinates: Tuple[int, int], aliases: List[str] = [], wiki: str = "", techLevel: int = -1,
            builtIn: Optional[bool] = False):
        """
        :param str name: The name of this system
        :param str faction: The faction that owns the system, if any
        :param list[str] neighbours: A list of system names that can be reached from this system's jump gate
        :param int security: An integer from 0 to 3 indicating the security of this system. 0 => secure, 3 => dangerous.
                                Security levels are configurable in bbConfig.securityLevels
        :param tuple[int, int] coordinates: A two int tuple representing the system's position in the galaxy.
                                            The grid can be viewed in bbData.mapImageWithGraphLink
        :param list[str] aliases: A list of alternative names by which this system may be referred to. (Default [])
        :param str wiki: A web page to display as the system's wiki article, if any (Default "")
        :param int techLevel: The tech level of the system, indicating the typical tech level of items that can be found here
                                - this currently has no behaviour, and is used only for lore. (Default -1)
        """
        super(SolarSystem, self).__init__(name, aliases, builtIn=builtIn)
        self.name = name
        self.faction = faction
        self.neighbours = neighbours
        self.security = security
        self.coordinates = tuple(coordinates)
        self.wiki = wiki
        self.hasWiki = wiki != ""

        self.techLevel = techLevel
        self.hasTechLevel = techLevel != -1


    def getNeighbours(self) -> List[str]:
        """Get a list of system names that can be reached from this system's jump gate. May be empty.

        :return: A list of system names that can be reached from this system's jump gate
        :rtype: list[str]
        """
        return self.neighbours


    def distanceTo(self, other: SolarSystem) -> float:
        """Calculate the straight-line distance from this system to another.

        :param System other: The other system to calculate distance to
        :return: The pythagorean-distance from this system to other
        :rtype: float
        """
        return math.sqrt((other.coordinates[1] - self.coordinates[1]) ** 2 \
                            + (other.coordinates[0] - self.coordinates[0]) ** 2)


    def hasJumpGate(self) -> bool:
        """Decide whether or not this system has any neighbours.

        :return: True if at least one system can be reached from this one via jump gate, False otherwise
        :rtype: bool
        """
        return bool(self.neighbours)


    def serialize(self, **kwargs) -> SerializedSolarSystemUnion:
        # Casting here so I can add the new fields
        data = cast(SerializedSolarSystemUnion, super().serialize(**kwargs))
        
        if self.builtIn:
            data["name"] = self.name
        else:
            # Casting here because we know the system is not builtIn
            data = cast(CustomSerializedSolarSystemUnion, super().serialize(**kwargs))
            data["faction"] = self.faction
            data["neighbours"] = self.neighbours
            data["security"] = self.security
            data["coordinates"] = self.coordinates

            if self.hasWiki:
                data["wiki"] = self.wiki
            if self.hasTechLevel:
                data["techLevel"] = self.techLevel

        return data


    @classmethod
    def deserialize(cls, sysDict: SerializedSolarSystemUnion, **kwargs) -> SolarSystem:
        """Factory function constructing a new System object from the information in the given dictionary.

        :param dict sysDict: A dictionary containing all information needed to construct the required System.
        :return: The requested System object
        :rtype: System
        """
        return SolarSystem(**cls._makeDefaults(sysDict, ("type",),))
