from typing import Union, cast
from typing_extensions import NotRequired

from sqlalchemy.orm import Mapped

from .moduleItem_json import SerializedModuleItem, TypedSerializedModuleItem

from ....baseClasses.serializable import SerializesToSchema
from ....baseClasses.embedFillable import embedField

from .moduleItem import ModuleItem
from ..base.item_spawnable import spawnableItem


class SerializedRepairBotModule(SerializedModuleItem):
    HPps: float


class TypedSerializedRepairBotModule(SerializedRepairBotModule, TypedSerializedModuleItem):
    ...


class AnySerializedRepairBotModule(SerializedRepairBotModule):
    type: NotRequired[str]


SerializedRepairBotModuleUnion = Union[SerializedRepairBotModule, TypedSerializedRepairBotModule]


@spawnableItem
class RepairBotModule(ModuleItem, SerializesToSchema[SerializedRepairBotModuleUnion]):
    """A module providing a ship with a slow health point increase to its hull and armour

    :var HPps: The amount of health points regained per second
    :vartype HPps: int
    """
    HPps: Mapped[float]

#region embed fields

    @embedField("Healing Rate")
    def formattedEffect(self): return f"{self.HPps} HP/s"

#endregion

    def statsStringShort(self):
        return "*HP/s: " + str(self.HPps) + "*"


    async def serialize(self, **kwargs) -> SerializedRepairBotModuleUnion:
        """Serialize this module into dictionary format, to be saved to file.
        Uses the base moduleItem serialize method as a starting point, and adds extra attributes
        implemented by this specific module.

        :return: A dictionary containing all information needed to reconstruct this module
        :rtype: dict
        """
        baseData = await super().serialize(**kwargs)

        data = cast(SerializedRepairBotModuleUnion, {
            **baseData,
            "HPps": self.HPps
        })
        return data
