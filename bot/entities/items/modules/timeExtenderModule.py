from typing import Union, cast
from typing_extensions import NotRequired

from sqlalchemy.orm import Mapped

from .moduleItem_json import SerializedModuleItem, TypedSerializedModuleItem
from ....lib.stringUtil import formatAdditive, formatMultiplier

from ....baseClasses.serializable import SerializesToSchema
from ....baseClasses.embedFillable import embedField

from .moduleItem import ModuleItem
from ..base.item_spawnable import spawnableItem


class SerializedTimeExtenderModule(SerializedModuleItem):
    effect: float
    duration: float


class TypedSerializedTimeExtenderModule(SerializedTimeExtenderModule, TypedSerializedModuleItem):
    ...


class AnySerializedTimeExtenderModule(SerializedTimeExtenderModule):
    type: NotRequired[str]


SerializedTimeExtenderModuleUnion = Union[SerializedTimeExtenderModule, TypedSerializedTimeExtenderModule]


@spawnableItem
class TimeExtenderModule(ModuleItem, SerializesToSchema[SerializedTimeExtenderModuleUnion]):
    """A module that will slow down time around the ship. The ship remains unaffected.

    :var effect: The amount to slow down time as a multiplier
    :vartype effect: float
    :var duration: The perceived duration in seconds of the effect from the perspective of the pilot
    :vartype duration: float
    """
    effect: Mapped[float]
    duration: Mapped[float]

#region embed fields

    @embedField("Effect")
    def formattedEffect(self): return f"{self.effect*100}%"
    
    @embedField("Duration")
    def formattedDuration(self): return f"{self.duration}s"

#endregion

    def statsStringShort(self):
        return "*Effect: " + formatMultiplier(self.effect) \
                + ", Duration: " + formatAdditive(self.duration) + "s*"


    async def serialize(self, **kwargs) -> SerializedTimeExtenderModuleUnion:
        """Serialize this module into dictionary format, to be saved to file.
        Uses the base moduleItem serialize method as a starting point, and adds extra attributes
        implemented by this specific module.

        :return: A dictionary containing all information needed to reconstruct this module
        :rtype: dict
        """
        baseData = await super().serialize(**kwargs)

        data = cast(SerializedTimeExtenderModuleUnion, {
            **baseData,
            "effect": self.effect,
            "duration": self.duration
        })
        return data
