from typing import Union, cast
from typing_extensions import NotRequired

from sqlalchemy.orm import Mapped

from .moduleItem_json import SerializedModuleItem, TypedSerializedModuleItem
from ....lib.stringUtil import formatAdditive, formatMultiplier

from ....baseClasses.serializable import SerializesToSchema
from ....baseClasses.embedFillable import embedField

from .moduleItem import ModuleItem
from ..base.item_spawnable import spawnableItem


class SerializedRepairBeamModule(SerializedModuleItem):
    effect: float
    count: int


class TypedSerializedRepairBeamModule(SerializedRepairBeamModule, TypedSerializedModuleItem):
    ...


class AnySerializedRepairBeamModule(SerializedRepairBeamModule):
    type: NotRequired[str]


SerializedRepairBeamModuleUnion = Union[SerializedRepairBeamModule, TypedSerializedRepairBeamModule]


@spawnableItem
class RepairBeamModule(ModuleItem, SerializesToSchema[SerializedRepairBeamModuleUnion]):
    """A module providing a ship with the ability to slowly add health points to nearby friendly ships

    :var effect: The amount of health added to nearby ships per time quantum
    :vartype effect: float
    :var count: The number of nearby ships that can be healed simultaneously
    :vartype count: int
    """
    effect: Mapped[float]
    count: Mapped[int]

#region embed fields

    @embedField("Effect")
    def formattedEffect(self): return f"{self.effect*100}%"
    
    @embedField("Count")
    def formattedCount(self): return self.count

#endregion

    def statsStringShort(self):
        return "*Effect: " + formatMultiplier(self.effect) \
                + ", Count: " + formatAdditive(self.count) + "*"


    async def serialize(self, **kwargs) -> SerializedRepairBeamModuleUnion:
        """Serialize this module into dictionary format, to be saved to file.
        Uses the base moduleItem serialize method as a starting point, and adds extra attributes
        implemented by this specific module.

        :return: A dictionary containing all information needed to reconstruct this module
        :rtype: dict
        """
        baseData = await super().serialize(**kwargs)

        data = cast(SerializedRepairBeamModuleUnion, {
            **baseData,
            "effect": self.effect,
            "count": self.count
        })
        return data
