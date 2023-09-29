from typing import List, Literal, Union, TypedDict
from typing_extensions import NotRequired

from ....baseClasses.hasRarity_json import SerializedWithRarity
from ...base.workshopable_json import AnySerializedWorkshopable


class SerializedAutoskinConfiguration(TypedDict):
    skinnedRegions: List[str]
    disabledRegions: NotRequired[List[str]]


class SerializedBaseClasses(AnySerializedWorkshopable, SerializedWithRarity):
    pass


class SerializedShipSkinBase(SerializedBaseClasses):
    diffuse: SerializedAutoskinConfiguration
    # normalSpecular: Optional[SerializedAutoskinConfiguration]
    method: str


class SerializedAllShipsShipSkin(SerializedShipSkinBase):
    allShips: Literal[True]


class SerializedNotAllShipsShipSkin(SerializedShipSkinBase):
    allShips: Literal[False]
    compatibleShips: List[int]


class TypedSerializedAllShipsShipSkin(SerializedAllShipsShipSkin):
    type: str


class TypedSerializedNotAllShipsShipSkin(SerializedNotAllShipsShipSkin):
    type: str


class AnySerializedShipSkin(SerializedShipSkinBase):
    type: NotRequired[str]
    allShips: bool
    compatibleShips: NotRequired[List[int]]


SerializedShipSkinUnion = Union[SerializedAllShipsShipSkin, SerializedNotAllShipsShipSkin, TypedSerializedAllShipsShipSkin, TypedSerializedNotAllShipsShipSkin]