from typing import Union, cast
from typing_extensions import NotRequired

from sqlalchemy.orm import Mapped

from .moduleItem_json import SerializedModuleItem, TypedSerializedModuleItem
from ....lib.stringUtil import formatAdditive, formatMultiplier

from ....baseClasses.serializable import SerializesToSchema
from ....baseClasses.embedFillable import embedField

from .moduleItem import ModuleItem
from ..base.item_spawnable import spawnableItem


class SerializedBoosterModule(SerializedModuleItem):
    effect: float
    duration: float


class TypedSerializedBoosterModule(SerializedBoosterModule, TypedSerializedModuleItem):
    ...


class AnySerializedBoosterModule(SerializedBoosterModule):
    type: NotRequired[str]


SerializedBoosterModuleUnion = Union[SerializedBoosterModule, TypedSerializedBoosterModule]


@spawnableItem
class BoosterModule(ModuleItem, SerializesToSchema[SerializedBoosterModuleUnion]):
    """"A module providing a ship with the ability to boost its speed for a short period of time.

    :var effect: Multiplier to apply to the ship's velocity
    :vartype effect: float
    :var duration: Number of seconds the boost lasts
    :vartype duration: float
    """
    effect: Mapped[float]
    duration: Mapped[float]

#region embed fields

    @embedField("Effect")
    def formattedEffect(self): return f"{self.effect*100}%"
    
    @embedField("Duration", hideWhenNone=True)
    def formattedDuration(self): return f"{self.duration}s"

#endregion

    def statsStringShort(self):
        return "*Effect: " + formatMultiplier(self.effect) \
                + ", Duration: " + formatAdditive(self.duration) + "s*"


    async def serialize(self, **kwargs) -> SerializedBoosterModuleUnion:
        """Serialize this module into dictionary format, to be saved to file.
        Uses the base moduleItem serialize method as a starting point, and adds extra attributes
        implemented by this specific module.

        :return: A dictionary containing all information needed to reconstruct this module
        :rtype: dict
        """
        baseData = await super().serialize(**kwargs)

        data = cast(SerializedBoosterModuleUnion, {
            **baseData,
            "effect": self.effect,
            "duration": self.duration
        })
        return data
