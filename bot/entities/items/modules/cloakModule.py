from typing import Union, cast
from typing_extensions import NotRequired

from sqlalchemy.orm import Mapped

from .moduleItem_json import SerializedModuleItem, TypedSerializedModuleItem
from ....lib.stringUtil import formatAdditive

from ....baseClasses.serializable import SerializesToSchema
from ....baseClasses.embedFillable import embedField

from .moduleItem import ModuleItem
from ..base.item_spawnable import spawnableItem


class SerializedCloakModule(SerializedModuleItem):
    duration: float


class TypedSerializedCloakModule(SerializedCloakModule, TypedSerializedModuleItem):
    ...


class AnySerializedCloakModule(SerializedCloakModule):
    type: NotRequired[str]


SerializedCloakModuleUnion = Union[SerializedCloakModule, TypedSerializedCloakModule]


@spawnableItem
class CloakModule(ModuleItem, SerializesToSchema[SerializedCloakModuleUnion]):
    """"A module providing a ship with the ability to turn invisible for a short period of time

    :var duration: The number of seconds this effect lasts
    :vartype duration: float
    """
    duration: Mapped[float]

#region embed fields

    @embedField("Duration", hideWhenNone=True)
    def formattedDuration(self): return f"{self.duration}s"

#endregion


    def statsStringShort(self):
        return "*Duration: " + formatAdditive(self.duration) + "s*"


    async def serialize(self, **kwargs) -> SerializedCloakModuleUnion:
        """Serialize this module into dictionary format, to be saved to file.
        Uses the base moduleItem serialize method as a starting point, and adds extra attributes
        implemented by this specific module.

        :return: A dictionary containing all information needed to reconstruct this module
        :rtype: dict
        """
        baseData = await super().serialize(**kwargs)

        data = cast(SerializedCloakModuleUnion, {
            **baseData,
            "duration": self.duration
        })
        return data
