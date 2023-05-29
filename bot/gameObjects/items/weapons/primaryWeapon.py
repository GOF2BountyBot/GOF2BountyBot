from typing import cast
from ..gameItem import spawnableItem, topThreeItemSpawnRates
from ....cfg import bbData
from .... import lib
from .weapon import Weapon, SerializedWeaponUnion, CustomSerializedWeaponUnion
from ....baseClasses.embedFillable import embedField


@spawnableItem
class PrimaryWeapon(Weapon):
    """A primary weapon that can be equipped onto a bbShip for use in duels.
    """

    @classmethod
    def deserialize(cls, weaponDict: SerializedWeaponUnion, **kwargs) -> "PrimaryWeapon":
        """Factory function constructing a new primaryWeapon object from a dictionary serialised
        representation - the opposite of primaryWeapon.serialize.

        :param dict weaponDict: A dictionary containing all information needed to construct the desired primaryWeapon
        :return: A new primaryWeapon object as described in weaponDict
        :rtype: primaryWeapon
        """
        if weaponDict.get("builtIn", False):
            return bbData.builtInWeaponObjs[weaponDict["name"]]
        else:
            # Casting here because we know the weapon is not builtIn
            weaponDict = cast(CustomSerializedWeaponUnion, weaponDict)
            return PrimaryWeapon(**cls._makeDefaults(weaponDict, ("type",),
                                emoji=lib.emojis.BasedEmoji.fromStr(weaponDict["emoji"]) \
                                        if "emoji" in weaponDict else lib.emojis.BasedEmoji.EMPTY))

    
    @embedField("BB Shop Spawn Rate", hideWhenNone=True)
    def formattedShopSpawnRate(self): return topThreeItemSpawnRates(self, bbData.weaponObjsByTL)
