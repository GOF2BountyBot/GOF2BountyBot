from typing import List, TypedDict
from typing_extensions import NotRequired

from ...base.workshopable_json import AnySerializedWorkshopable
from ....lib.emojis import SerializedBasedEmoji
from ....baseClasses.aliasable_json import SerializedAliasable


class SerializedCompatibleSkinRegistration(TypedDict):
    name: str
    id: int


class SerializedSkinnableRegionRegistration(TypedDict):
    name: str
    id: int


class SerializedShipSpec(AnySerializedWorkshopable, SerializedAliasable):
    id: int
    value: int
    manufacturer: NotRequired[str]
    iconUrl: str
    emoji: NotRequired[SerializedBasedEmoji]
    techLevel: NotRequired[int]
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
