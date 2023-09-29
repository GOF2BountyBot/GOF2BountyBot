from typing import Union, cast
from typing_extensions import NotRequired

from sqlalchemy.orm import Mapped

from .moduleItem_json import SerializedModuleItem, TypedSerializedModuleItem

from ....baseClasses.serializable import SerializesToSchema
from ....baseClasses.embedFillable import embedField

from .moduleItem import ModuleItem
from ..base.item_spawnable import spawnableItem


class SerializedShieldInjectorModule(SerializedModuleItem):
    plasmaConsumption: int


class TypedSerializedShieldInjectorModule(SerializedShieldInjectorModule, TypedSerializedModuleItem):
    ...


class AnySerializedShieldInjectorModule(SerializedShieldInjectorModule):
    type: NotRequired[str]


SerializedShieldInjectorModuleUnion = Union[SerializedShieldInjectorModule, TypedSerializedShieldInjectorModule]


@spawnableItem
class ShieldInjectorModule(ModuleItem, SerializesToSchema[SerializedShieldInjectorModuleUnion]):
    """A module providing a ship with the ability to instantly refill their shield capacity, in exchange for blue plasma

    :var plasmaConsumption: The amount of plasma required to refill shields
    :vartype plasmaConsumption: int
    """
    plasmaConsumption: Mapped[int]

#region embed fields

    @embedField("Plasma Consumption")
    def formattedPlasmaConsumption(self): return self.plasmaConsumption

#endregion

    def statsStringShort(self):
        return "*Plasma Consumption: " + str(self.plasmaConsumption) + "*"


    async def serialize(self, **kwargs) -> SerializedShieldInjectorModuleUnion:
        """Serialize this module into dictionary format, to be saved to file.
        Uses the base moduleItem serialize method as a starting point, and adds extra attributes
        implemented by this specific module.

        :return: A dictionary containing all information needed to reconstruct this module
        :rtype: dict
        """
        baseData = await super().serialize(**kwargs)

        data = cast(SerializedShieldInjectorModuleUnion, {
            **baseData,
            "plasmaConsumption": self.plasmaConsumption
        })
        return data
