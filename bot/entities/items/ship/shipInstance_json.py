from typing import List, Union
from typing_extensions import NotRequired

from .shipSpec_json import SerializedShipSpec
from ..weapons.weapon_json import SerializedWeapon
from ..modules.moduleItem_json import SerializedModuleItemUnion
from .shipUpgrade_json import SerializedShipUpgradeUnion
from ..base.item_json import TypedSerializedItem, SerializedItem


class SerializedShipInstance(SerializedShipSpec, SerializedItem):
    shipSpecId: int
    skin: NotRequired[int]
    weapons: NotRequired[List[SerializedWeapon]]
    modules: NotRequired[List[SerializedModuleItemUnion]]
    turrets: NotRequired[List[SerializedWeapon]]
    shipUpgrades: NotRequired[List[SerializedShipUpgradeUnion]]
    nickname: NotRequired[str]


class TypedSerializedShipInstance(SerializedShipInstance, TypedSerializedItem): pass


class AnySerializedShipInstance(SerializedShipInstance):
    type: NotRequired[str]


SerializedShipInstanceUnion = Union[SerializedShipInstance, TypedSerializedShipInstance]
