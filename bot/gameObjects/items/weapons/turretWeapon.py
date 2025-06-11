from __future__ import annotations
from typing import cast
from bot.gameObjects.items.gameItem import spawnableItem, topThreeItemSpawnRates
from bot.cfg import bbData
from bot import lib
from bot.gameObjects.items.weapons.weapon import Weapon, CustomSerializedWeaponUnion, SerializedWeaponUnion
from bot.baseClasses.embedFillable import embedField


@spawnableItem
class TurretWeapon(Weapon):
    """A turret that can be equipped onto a bbShip for use in duels.
    """

    @classmethod
    def deserialize(cls, turretDict: SerializedWeaponUnion, **kwargs) -> TurretWeapon:
        """Factory function constructing a new turretWeapon object from a dictionary serialised representation -
        the opposite of turretWeapon.serialize.

        :param dict turretDict: A dictionary containing all information needed to construct the desired turretWeapon
        :return: A new turretWeapon object as described in turretDict
        :rtype: turretWeapon
        """
        if turretDict.get("builtIn", False):
            return bbData.builtInTurretObjs[turretDict["name"]]
        else:
            # Casting here because we know the weapon is not builtIn
            turretDict = cast(CustomSerializedWeaponUnion, turretDict)
            return TurretWeapon(**cls._makeDefaults(turretDict, ("type",),
                                                    emoji=lib.emojis.BasedEmoji.fromStr(turretDict["emoji"]) \
                                                            if "emoji" in turretDict else lib.emojis.BasedEmoji.EMPTY))

    
    @embedField("BB Shop Spawn Rate", hideWhenNone=True)
    def formattedShopSpawnRate(self): return topThreeItemSpawnRates(self, bbData.turretObjsByTL)
