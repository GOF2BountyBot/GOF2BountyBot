from typing import Union
from typing_extensions import NotRequired

from ...base.workshopable_json import AnySerializedWorkshopable

class SerializedShipUpgrade(AnySerializedWorkshopable):
    vendor: NotRequired[str]
    shipToUpgradeValueMult: float
    armour: NotRequired[int]
    cargo: NotRequired[int]
    handling: NotRequired[int]
    maxSecondaries: NotRequired[int]
    maxPrimaries: NotRequired[int]
    maxTurrets: NotRequired[int]
    maxModules: NotRequired[int]
    armourMultiplier: NotRequired[float]
    cargoMultiplier: NotRequired[float]
    handlingMultiplier: NotRequired[float]
    maxSecondariesMultiplier: NotRequired[float]
    maxPrimariesMultiplier: NotRequired[float]
    maxTurretsMultiplier: NotRequired[float]
    maxModulesMultiplier: NotRequired[float]

class TypedSerializedShipUpgrade(SerializedShipUpgrade):
    type: str


class AnySerializedShipUpgrade(SerializedShipUpgrade):
    type: NotRequired[type]


SerializedShipUpgradeUnion = Union[SerializedShipUpgrade, TypedSerializedShipUpgrade]