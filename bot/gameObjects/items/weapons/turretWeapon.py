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
    def fromDict(cls, turretDict : dict, **kwargs) -> TurretWeapon:
        """Factory function constructing a new turretWeapon object from a dictionary serialised representation -
        the opposite of turretWeapon.toDict.

        :param dict turretDict: A dictionary containing all information needed to construct the desired turretWeapon
        :return: A new turretWeapon object as described in turretDict
        :rtype: turretWeapon
        """
        if turretDict["builtIn"]:
            return bbData.builtInTurretObjs[turretDict["name"]]
        else:
            return TurretWeapon(turretDict["name"], turretDict["aliases"], dps=turretDict["dps"], value=turretDict["value"],
                                wiki=turretDict["wiki"] if "wiki" in turretDict else "",
                                manufacturer=turretDict["manufacturer"] if "manufacturer" in turretDict else "",
                                icon=turretDict["icon"] if "icon" in turretDict else bbData.rocketIcon,
                                emoji=lib.emojis.BasedEmoji.fromStr(turretDict["emoji"]) \
                                        if "emoji" in turretDict else lib.emojis.BasedEmoji.EMPTY,
                                techLevel=turretDict["techLevel"] if "techLevel" in turretDict else -1, builtIn=False)
