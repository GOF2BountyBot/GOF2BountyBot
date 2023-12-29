from typing import List

from ...baseClasses.aliasable_json import SerializedAliasable

class SerializedSolarSystem(SerializedAliasable):
    id: int
    faction: str
    security: int
    techLevel: int
    neighbours: List[int]
