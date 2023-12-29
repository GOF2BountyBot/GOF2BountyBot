from __future__ import annotations
from typing import cast

from sqlalchemy.orm import Mapped

from ....baseClasses.serializable import SerializesToSchema
from ....baseClasses.embedFillable import embedField
from ...base.workshopable import Workshopable
from ..base.item import Item, ItemWithId
from ..base.item_json import AnySerializedItem
from ...base.workshopable_json import AnySerializedWorkshopable
from .weapon_json import SerializedWeapon


# TODO
class Weapon(ItemWithId, Item, Workshopable, SerializesToSchema[SerializedWeapon]):
    """An abstract class representing weapons that can be equipped onto a ship for use in duels.

    :var dps: The weapon's damage per second to a target ship.
    :vartype dps: float
    """
    dps: Mapped[int]
    value: Mapped[int]

    
    async def getValue(self) -> int:
        return self.value

    
    @embedField("Damage Per Second (DPS)")
    def formattedDps(self): return self.dps


    def statsStringShort(self) -> str:
        """Get a short string summary of the weapon. This currently only includes the DPS.

        :return: a short string summary of the weapon's statistics
        :rtype: str
        """
        return "*Dps: " + str(self.dps) + "*"


    async def serialize(self, **kwargs) -> SerializedWeapon:
        """Serialize this item into dictionary format, for saving to file.

        :param bool saveType: When true, include the string name of the object type in the output.
        :return: A dictionary containing all information needed to reconstruct this weapon.
                    If the weapon is builtIn, this is only its name.
        :rtype: dict
        """
        baseData = cast(AnySerializedItem, await ItemBase.serialize(self, **kwargs))
        workshopableData = cast(AnySerializedWorkshopable, await Workshopable.serialize(self, **kwargs))

        data: SerializedWeapon = {
            **baseData,
            **workshopableData,
            "dps": self.dps
        }
        return data
