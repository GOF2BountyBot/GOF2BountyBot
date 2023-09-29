from typing import Union, cast
from typing_extensions import NotRequired

from sqlalchemy.orm import Mapped

from .moduleItem_json import SerializedModuleItem, TypedSerializedModuleItem

from ....baseClasses.serializable import SerializesToSchema
from ....baseClasses.embedFillable import embedField

from .moduleItem import ModuleItem
from ..base.item_spawnable import spawnableItem


class SerializedScannerModule(SerializedModuleItem):
    timeToLock: float
    showClassAAsteroids: bool
    showCargo: bool


class TypedSerializedScannerModule(SerializedScannerModule, TypedSerializedModuleItem):
    ...


class AnySerializedScannerModule(SerializedScannerModule):
    type: NotRequired[str]


SerializedScannerModuleUnion = Union[SerializedScannerModule, TypedSerializedScannerModule]


@spawnableItem
class ScannerModule(ModuleItem, SerializesToSchema[SerializedScannerModuleUnion]):
    """A module providing a ship with the ability to scan in-range objects, such as asteroids and ships

    :var timeToLock: The number of seconds this scanner takes to lock onto an object and obtain information
    :vartype timeToLock: float
    :var showClassAAsteroids: Whether or not this scanner will display nearby A-class asteroids on the ship's heads up display
    :vartype showClassAAsteroids: bool
    :var showCargo: Whether or not this scanner will display the contents of scanned ships' cargo holds
    :vartype showCargo: bool
    """
    timeToLock: Mapped[float]
    showClassAAsteroids: Mapped[bool]
    showCargo: Mapped[bool]

#region embed fields

    @embedField("Time to Lock")
    def formattedTimeToLock(self): return f"{self.timeToLock}s"
    
    @embedField("Show Class A Asteroids")
    def formattedShowClassAAsteroids(self): return "Yes" if self.showClassAAsteroids else "No"

    @embedField("Show Cargo")
    def formattedShowCargo(self): return "Yes" if self.showCargo else "No"

#endregion


    def statsStringShort(self):
        return "*Time To Lock: " + str(self.timeToLock) \
                + "s, Show Class A Asteroids: " + ("Yes" if self.showClassAAsteroids else "No") \
                + ", Show Cargo: " + ("Yes" if self.showCargo else "No") + "*"


    async def serialize(self, **kwargs) -> SerializedScannerModuleUnion:
        """Serialize this module into dictionary format, to be saved to file.
        Uses the base moduleItem serialize method as a starting point, and adds extra attributes
        implemented by this specific module.

        :return: A dictionary containing all information needed to reconstruct this module
        :rtype: dict
        """
        baseData = await super().serialize(**kwargs)

        data = cast(SerializedScannerModuleUnion, {
            **baseData,
            "timeToLock": self.timeToLock,
            "showClassAAsteroids": self.showClassAAsteroids,
            "showCargo": self.showCargo
        })
        return data
