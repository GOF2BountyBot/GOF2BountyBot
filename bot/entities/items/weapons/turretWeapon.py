from ....cfg import bbData
from ....baseClasses.embedFillable import embedField
from ....lib.emojis import BasedEmoji
from ....lib.gameMaths import topThreeItemSpawnRates
from ....database.constants import StoreableItemType
from ..base.item_storeable import itemType
from ..base.item_spawnable import spawnableItem
from .weapon_json import SerializedWeapon
from .weapon import Weapon


@spawnableItem
@itemType(StoreableItemType.turret)
class TurretWeapon(Weapon):
    """A turret that can be equipped onto a ship for use in duels.
    """

    @classmethod
    async def deserialize(cls, data: SerializedWeapon, **kwargs) -> "TurretWeapon":
        """Factory function constructing a new turretWeapon object from a dictionary serialised
        representation - the opposite of turretWeapon.serialize.

        :param dict weaponDict: A dictionary containing all information needed to construct the desired turretWeapon
        :return: A new turretWeapon object as described in weaponDict
        :rtype: turretWeapon
        """
        if emojiData := data.get("emoji", None):
            emoji = await BasedEmoji.deserialize(emojiData)
        else:
            emoji = BasedEmoji.EMPTY

        return TurretWeapon(**cls._makeDefaults(data, ("type",),
                             emoji=emoji))

    
    @embedField("BB Shop Spawn Rate", hideWhenNone=True)
    def formattedShopSpawnRate(self): return topThreeItemSpawnRates(self.techLevel, bbData.turretObjsByTL)
