from typing import Union, cast
from typing_extensions import NotRequired

from sqlalchemy.orm import Mapped

from .moduleItem_json import SerializedModuleItem, TypedSerializedModuleItem
from ....lib.stringUtil import formatMultiplier

from ....baseClasses.serializable import SerializesToSchema
from ....baseClasses.embedFillable import embedField

from .moduleItem import ModuleItem
from ..base.item_spawnable import spawnableItem


class SerializedGammaShieldModule(SerializedModuleItem):
    effect: float


class TypedSerializedGammaShieldModule(SerializedGammaShieldModule, TypedSerializedModuleItem):
    ...


class AnySerializedGammaShieldModule(SerializedGammaShieldModule):
    type: NotRequired[str]


SerializedGammaShieldModuleUnion = Union[SerializedGammaShieldModule, TypedSerializedGammaShieldModule]


@spawnableItem
class GammaShieldModule(ModuleItem, SerializesToSchema[SerializedGammaShieldModuleUnion]):
    """"A module providing a ship with protection agains gamma radiation

    :var effect: The reduction in gamma radiation received as a multiplier
    :vartype effect: float
    """
    effect: Mapped[float]

#region embed fields

    @embedField("Effect")
    def formattedEffect(self): return f"{self.effect*100}%"

#endregion

    def statsStringShort(self):
        return "*Gamma Shielding: " + formatMultiplier(self.effect) + "*"


    async def serialize(self, **kwargs) -> SerializedGammaShieldModuleUnion:
        """Serialize this module into dictionary format, to be saved to file.
        Uses the base moduleItem serialize method as a starting point, and adds extra attributes
        implemented by this specific module.

        :return: A dictionary containing all information needed to reconstruct this module
        :rtype: dict
        """
        baseData = await super().serialize(**kwargs)

        data = cast(SerializedGammaShieldModuleUnion, {
            **baseData,
            "effect": self.effect
        })
        return data
