from typing import Union, cast
from typing_extensions import NotRequired

from sqlalchemy.orm import Mapped

from .moduleItem_json import SerializedModuleItem, TypedSerializedModuleItem

from ....baseClasses.serializable import SerializesToSchema
from ....baseClasses.embedFillable import embedField

from .moduleItem import ModuleItem
from ..base.item_spawnable import spawnableItem


class SerializedSpectralFilterModule(SerializedModuleItem):
    showOnRadar: bool
    showInfo: bool


class TypedSerializedSpectralFilterModule(SerializedSpectralFilterModule, TypedSerializedModuleItem):
    ...


class AnySerializedSpectralFilterModule(SerializedSpectralFilterModule):
    type: NotRequired[str]


SerializedSpectralFilterModuleUnion = Union[SerializedSpectralFilterModule, TypedSerializedSpectralFilterModule]


@spawnableItem
class SpectralFilterModule(ModuleItem, SerializesToSchema[SerializedSpectralFilterModuleUnion]):
    """A module allowing the user to see plasma clouds in space.

    :var showOnRadar: Whether or not plasma clouds are marked on the ships radar
    :vartype showOnRadar: bool
    :var showInfo: Whether information about plasma clouds is shown on the ship's heads up display
    :vartype showInfo: bool
    """
    showOnRadar: Mapped[bool]
    showInfo: Mapped[bool]

#region embed fields

    @embedField("Show On Radar")
    def formattedShowOnRadar(self): return "Yes" if self.showOnRadar else "No"
    
    @embedField("Show Info")
    def formattedShowInfo(self): return "Yes" if self.showInfo else "No"

#endregion

    def statsStringShort(self):
        return "*Show Info? " + ("Yes" if self.showInfo else "No") \
                + ", Show On Radar? " + ("Yes" if self.showOnRadar else "No") + "*"


    async def serialize(self, **kwargs) -> SerializedSpectralFilterModuleUnion:
        """Serialize this module into dictionary format, to be saved to file.
        Uses the base moduleItem serialize method as a starting point, and adds extra attributes
        implemented by this specific module.

        :return: A dictionary containing all information needed to reconstruct this module
        :rtype: dict
        """
        baseData = await super().serialize(**kwargs)

        data = cast(SerializedSpectralFilterModuleUnion, {
            **baseData,
            "showOnRadar": self.showOnRadar,
            "showInfo": self.showInfo
        })
        return data
