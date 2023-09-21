from typing import List, Union, TypedDict
from typing_extensions import NotRequired

from ..base.itemBase_json import SerializedItemBase, TypedSerializedItemBase
from ...base.workshopable_json import AnySerializedWorkshopable


class SerializedCompatibleSkinRegistration(TypedDict):
    name: str
    id: int


class SerializedSkinnableRegionRegistration(TypedDict):
    name: str
    id: int


class SerializedShipSpec(AnySerializedWorkshopable, SerializedItemBase):
    armour: int
    cargo: int
    maxSecondaries: int
    handling: int
    maxPrimaries: int
    maxTurrets: int
    maxModules: int
    skinnable: bool
    compatibleSkins: NotRequired[List[SerializedCompatibleSkinRegistration]]
    skinnableTextureRegions: NotRequired[List[SerializedSkinnableRegionRegistration]]
    

class TypedSerializedShipSpec(SerializedShipSpec, TypedSerializedItemBase): pass


SerializedShipSpecUnion = Union[SerializedShipSpec, TypedSerializedShipSpec]
