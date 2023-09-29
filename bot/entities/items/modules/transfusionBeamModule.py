from typing import Union, cast
from typing_extensions import NotRequired

from sqlalchemy.orm import Mapped

from .moduleItem_json import SerializedModuleItem, TypedSerializedModuleItem

from ....baseClasses.serializable import SerializesToSchema
from ....baseClasses.embedFillable import embedField

from .moduleItem import ModuleItem
from ..base.item_spawnable import spawnableItem


class SerializedTransfusionBeamModule(SerializedModuleItem):
    HPps: float
    count: int


class TypedSerializedTransfusionBeamModule(SerializedTransfusionBeamModule, TypedSerializedModuleItem):
    ...


class AnySerializedTransfusionBeamModule(SerializedTransfusionBeamModule):
    type: NotRequired[str]


SerializedTransfusionBeamModuleUnion = Union[SerializedTransfusionBeamModule, TypedSerializedTransfusionBeamModule]


@spawnableItem
class TransfusionBeamModule(ModuleItem, SerializesToSchema[SerializedTransfusionBeamModuleUnion]):
    """A module that slowly steals health from nearby ships, and adds the stolen heath to this ship's health.

    :var HPps: The amount of health points per second to steal
    :vartype HPps: int
    :var count: The number of ships from which health may be stolen simultaneously
    :vartype count: int
    """
    HPps: Mapped[float]
    count: Mapped[int]

#region embed fields

    @embedField("Healing Rate")
    def formattedHealingRate(self): return f"{self.HPps} HP/s"
    
    @embedField("Count")
    def formattedCount(self): return self.count

#endregion

    def statsStringShort(self):
        return "*HP/s: " + str(self.HPps) + ", Count: " + str(self.count) + "*"


    async def serialize(self, **kwargs) -> SerializedTransfusionBeamModuleUnion:
        """Serialize this module into dictionary format, to be saved to file.
        Uses the base moduleItem serialize method as a starting point, and adds extra attributes
        implemented by this specific module.

        :return: A dictionary containing all information needed to reconstruct this module
        :rtype: dict
        """
        baseData = await super().serialize(**kwargs)

        data = cast(SerializedTransfusionBeamModuleUnion, {
            **baseData,
            "HPps": self.HPps,
            "count": self.count
        })
        return data
