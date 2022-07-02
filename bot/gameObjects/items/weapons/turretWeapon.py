from __future__ import annotations
from ..gameItem import spawnableItem
from ....cfg import bbData
from .... import lib
from .weapon import Weapon


@spawnableItem
class TurretWeapon(Weapon):
    """A turret that can be equipped onto a bbShip for use in duels.
    """

    @classmethod
    def deserialize(cls, turretDict: dict, **kwargs) -> TurretWeapon:
        """Factory function constructing a new turretWeapon object from a dictionary serialised representation -
        the opposite of turretWeapon.serialize.

        :param dict turretDict: A dictionary containing all information needed to construct the desired turretWeapon
        :return: A new turretWeapon object as described in turretDict
        :rtype: turretWeapon
        """
        if turretDict.get("builtIn", False):
            return bbData.builtInTurretObjs[turretDict["name"]]
        else:
            return TurretWeapon(**cls._makeDefaults(turretDict, ("type",),
                                                    emoji=lib.emojis.BasedEmoji.fromStr(turretDict["emoji"]) \
                                                            if "emoji" in turretDict else lib.emojis.BasedEmoji.EMPTY))
