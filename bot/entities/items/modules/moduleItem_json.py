from typing import Union
from typing_extensions import NotRequired

from ..base.item_json import SerializedItem
from ...base.workshopable_json import SerializedBuiltInWorkshopable, SerializedUserSubmittedWorkshopable


class SerializedModuleItemBase(SerializedItem):
    armour: NotRequired[int]
    shield: NotRequired[int]
    cargo: NotRequired[int]
    handling: NotRequired[int]
    armourMultiplier: NotRequired[float]
    shieldMultiplier: NotRequired[float]
    dpsMultiplier: NotRequired[float]
    cargoMultiplier: NotRequired[float]
    handlingMultiplier: NotRequired[float]


class SerializedBuiltInModuleItem(SerializedBuiltInWorkshopable, SerializedModuleItemBase):
    pass


class SerializedUserSubmittedModuleItem(SerializedUserSubmittedWorkshopable, SerializedModuleItemBase):
    pass


SerializedModuleItemUnion = Union[SerializedBuiltInModuleItem, SerializedUserSubmittedModuleItem]
