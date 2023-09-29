from typing import Union, cast
from typing_extensions import NotRequired

from sqlalchemy.orm import Mapped

from .moduleItem_json import SerializedModuleItem, TypedSerializedModuleItem

from ....baseClasses.serializable import SerializesToSchema
from ....baseClasses.embedFillable import embedField

from .moduleItem import ModuleItem
from ..base.item_spawnable import spawnableItem

class SerializedCabinModule(SerializedModuleItem):
    cabinSize: int

class TypedSerializedCabinModule(SerializedCabinModule, TypedSerializedModuleItem): ...

class AnySerializedCabinModule(SerializedCabinModule):
    type: NotRequired[str]

SerializedCabinModuleUnion = Union[SerializedCabinModule, TypedSerializedCabinModule]


@spawnableItem
class CabinModule(ModuleItem, SerializesToSchema[SerializedCabinModuleUnion]):
    """"A module providing a ship with the ability to carry passengers.

    :var cabinSize: The number of passengers that can fit in this cabin
    :vartype cabinSize: int
    """
    cabinSize: Mapped[int]

#region embed fields

    @embedField("Cabin Size")
    def formattedCabinSize(self): return self.cabinSize

#endregion

    def statsStringShort(self):
        return "*Cabin Size: " + str(self.cabinSize) + "*"


    async def serialize(self, **kwargs) -> SerializedCabinModuleUnion:
        """Serialize this module into dictionary format, to be saved to file. Uses the base moduleItem
        serialize method as a starting point, and adds extra attributes implemented by this specific module.

        :return: A dictionary containing all information needed to reconstruct this module
        :rtype: dict
        """
        baseData = await super().serialize(**kwargs)
        
        data = cast(SerializedCabinModuleUnion, {
            **baseData,
            "cabinSize": self.cabinSize
        })
        return data
