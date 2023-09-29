from typing import Union, cast
from typing_extensions import NotRequired

from sqlalchemy.orm import Mapped

from .moduleItem_json import SerializedModuleItem, TypedSerializedModuleItem
from ....lib.stringUtil import formatMultiplier

from ....baseClasses.serializable import SerializesToSchema
from ....baseClasses.embedFillable import embedField

from .moduleItem import ModuleItem
from ..base.item_spawnable import spawnableItem


class SerializedMiningDrillModule(SerializedModuleItem):
    oreYield: float
    drillHandling: float


class TypedSerializedMiningDrillModule(SerializedMiningDrillModule, TypedSerializedModuleItem):
    ...


class AnySerializedMiningDrillModule(SerializedMiningDrillModule):
    type: NotRequired[str]


SerializedMiningDrillModuleUnion = Union[SerializedMiningDrillModule, TypedSerializedMiningDrillModule]


@spawnableItem
class MiningDrillModule(ModuleItem, SerializesToSchema[SerializedMiningDrillModuleUnion]):
    """"A module providing a ship with the ability to mine ore from asteroids

    :var oreYield: The percentage of the maximum ore this drill will receive from an asteroid
    :vartype oreYield: float
    :var drillHandling: The drill's ease of use
    :vartype drillHandling: float
    """
    oreYield: Mapped[float]
    drillHandling: Mapped[float]

#region embed fields

    @embedField("Ore Yield")
    def formattedYield(self): return f"{self.oreYield*100}%"
    
    @embedField("Handling")
    def formattedDrillHandling(self): return f"{self.drillHandling*100}%"

#endregion


    def statsStringShort(self):
        return "*Yield: " + formatMultiplier(self.oreYield) \
                + ", Handling: " + formatMultiplier(self.drillHandling) + "*"


    async def serialize(self, **kwargs) -> SerializedMiningDrillModuleUnion:
        """Serialize this module into dictionary format, to be saved to file.
        Uses the base moduleItem serialize method as a starting point, and adds extra attributes
        implemented by this specific module.

        :return: A dictionary containing all information needed to reconstruct this module
        :rtype: dict
        """
        baseData = await super().serialize(**kwargs)

        data = cast(SerializedMiningDrillModuleUnion, {
            **baseData,
            "oreYield": self.oreYield,
            "drillHandling": self.drillHandling
        })
        return data
