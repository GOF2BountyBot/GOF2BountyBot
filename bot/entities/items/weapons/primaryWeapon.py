from sqlalchemy.orm import DeclarativeBase

from ....cfg import bbData
from ....lib.emojis import BasedEmoji
from ....lib.gameMaths import topThreeItemSpawnRates
from ....baseClasses.embedFillable import embedField
from ..base.itemBase_storeable import itemType
from ....database.constants import StoreableItemType
from ..base.itemBase_spawnable import spawnableItem
from .weapon_json import SerializedWeapon
from .weapon import Weapon


class Base(DeclarativeBase):
    pass


@spawnableItem
@itemType(StoreableItemType.primaryWeapon)
class PrimaryWeapon(Weapon):
    """A primary weapon that can be equipped onto a ship for use in duels.
    """

    @classmethod
    async def deserialize(cls, data: SerializedWeapon, **kwargs) -> "PrimaryWeapon":
        """Factory function constructing a new primaryWeapon object from a dictionary serialised
        representation - the opposite of primaryWeapon.serialize.

        :param dict weaponDict: A dictionary containing all information needed to construct the desired primaryWeapon
        :return: A new primaryWeapon object as described in weaponDict
        :rtype: primaryWeapon
        """
        if emojiData := data.get("emoji", None):
            emoji = await BasedEmoji.deserialize(emojiData)
        else:
            emoji = BasedEmoji.EMPTY

        return PrimaryWeapon(**cls._makeDefaults(data, ("type",),
                             emoji=emoji))

    
    @embedField("BB Shop Spawn Rate", hideWhenNone=True)
    def formattedShopSpawnRate(self): return topThreeItemSpawnRates(self.techLevel, bbData.weaponObjsByTL)
