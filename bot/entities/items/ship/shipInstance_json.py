from typing import List
from typing_extensions import NotRequired

from .shipSpec_json import SerializedShipSpec


class SerializedShipInstance(SerializedShipSpec):
    skin: NotRequired[str]
    weapons: NotRequired[List[SerializedWeaponUnion]]
    modules: NotRequired[List[SerializedModuleItemUnion]]
    turrets: NotRequired[List[SerializedWeaponUnion]]
    shipUpgrades: NotRequired[List[shipUpgrade.SerializedShipUpgradeUnion]]
    nickname: NotRequired[str]

class SkinnedSerializedShip(SerializedShip):
    skin: shipSkin.SerializedShipSkinUnion
    icon: str

class TypedSkinnedBuiltInSerializedShip(SkinnedSerializedShip, TypedSerializedShip): pass

# Really this should inherit from TypedCustomSerializedGameItem, but that requires techLevel to be present.
# Ships are a special case because their techLevel is calculated dynamically based on value
class TypedCustomSerializedShip(CustomSerializedShip):
    type: str

class SkinnedCustomSerializedShip(CustomSerializedShip):
    skin: shipSkin.SerializedShipSkinUnion
    icon: str

class TypedSkinnedCustomSerializedShip(SkinnedCustomSerializedShip, TypedCustomSerializedShip): pass