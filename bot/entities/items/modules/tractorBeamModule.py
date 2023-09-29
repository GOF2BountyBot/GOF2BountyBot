from typing import Union, cast
from typing_extensions import NotRequired

from sqlalchemy.orm import Mapped

from .moduleItem_json import SerializedModuleItem, TypedSerializedModuleItem

from ....baseClasses.serializable import SerializesToSchema
from ....baseClasses.embedFillable import embedField

from .moduleItem import ModuleItem
from ..base.item_spawnable import spawnableItem


class SerializedTractorBeamModule(SerializedModuleItem):
    timeToLock: float


class TypedSerializedTractorBeamModule(SerializedTractorBeamModule, TypedSerializedModuleItem):
    ...


class AnySerializedTractorBeamModule(SerializedTractorBeamModule):
    type: NotRequired[str]


SerializedTractorBeamModuleUnion = Union[SerializedTractorBeamModule, TypedSerializedTractorBeamModule]


@spawnableItem
class TractorBeamModule(ModuleItem, SerializesToSchema[SerializedTractorBeamModuleUnion]):
    """A module providing a ship with the ability to pull nearby debris and items into the ship's cargo hold

    :var timeToLock: The amount of time in seconds needed for the beam to lock onto an item and pull it into the hold
    :vartype timeToLock: float
    """
    timeToLock: Mapped[float]

#region embed fields

    @embedField("Time to Lock")
    def formattedTimeToLock(self): return f"{self.timeToLock}s"

#endregion

    def statsStringShort(self):
        return "*Time To Lock: " + str(self.timeToLock) + "s*"


    async def serialize(self, **kwargs) -> SerializedTractorBeamModuleUnion:
        """Serialize this module into dictionary format, to be saved to file.
        Uses the base moduleItem serialize method as a starting point, and adds extra attributes
        implemented by this specific module.

        :return: A dictionary containing all information needed to reconstruct this module
        :rtype: dict
        """
        baseData = await super().serialize(**kwargs)

        data = cast(SerializedTractorBeamModuleUnion, {
            **baseData,
            "timeToLock": self.timeToLock
        })
        return data
