from typing import Union, cast
from typing_extensions import NotRequired

from sqlalchemy.orm import Mapped

from .moduleItem_json import SerializedModuleItem, TypedSerializedModuleItem
from ....lib.stringUtil import formatAdditive

from ....baseClasses.serializable import SerializesToSchema
from ....baseClasses.embedFillable import embedField

from .moduleItem import ModuleItem
from ..base.item_spawnable import spawnableItem


class SerializedEmergencySystemModule(SerializedModuleItem):
    duration: float


class TypedSerializedEmergencySystemModule(SerializedEmergencySystemModule, TypedSerializedModuleItem):
    ...


class AnySerializedEmergencySystemModule(SerializedEmergencySystemModule):
    type: NotRequired[str]


SerializedEmergencySystemModuleUnion = Union[SerializedEmergencySystemModule, TypedSerializedEmergencySystemModule]


@spawnableItem
class EmergencySystemModule(ModuleItem, SerializesToSchema[SerializedEmergencySystemModuleUnion]):
    """"A module providing a ship with a short period of invincibility just before dying

    :var duration: The number of seconds the effect is active for
    :vartype duration: float
    """
    duration: Mapped[float]

#region embed fields

    @embedField("Duration", hideWhenNone=True)
    def formattedDuration(self): return f"{self.duration}s"

#endregion


    def statsStringShort(self):
        return "*Duration: " + formatAdditive(self.duration) + "s*"


    async def serialize(self, **kwargs) -> SerializedEmergencySystemModuleUnion:
        """Serialize this module into dictionary format, to be saved to file.
        Uses the base moduleItem serialize method as a starting point, and adds extra attributes
        implemented by this specific module.

        :return: A dictionary containing all information needed to reconstruct this module
        :rtype: dict
        """
        baseData = await super().serialize(**kwargs)

        data = cast(SerializedEmergencySystemModuleUnion, {
            **baseData,
            "duration": self.duration
        })
        return data

