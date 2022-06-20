from ..gameItem import spawnableItem
from ....cfg import bbData
from .... import lib
from .weapon import Weapon


@spawnableItem
class PrimaryWeapon(Weapon):
    """A primary weapon that can be equipped onto a bbShip for use in duels.
    """

    @classmethod
    def deserialize(cls, weaponDict, **kwargs):
        """Factory function constructing a new primaryWeapon object from a dictionary serialised
        representation - the opposite of primaryWeapon.serialize.

        :param dict weaponDict: A dictionary containing all information needed to construct the desired primaryWeapon
        :return: A new primaryWeapon object as described in weaponDict
        :rtype: primaryWeapon
        """
        if weaponDict.get("builtIn", False):
            return bbData.builtInWeaponObjs[weaponDict["name"]]
        else:
            return PrimaryWeapon(**cls._makeDefaults(weaponDict, ("type",),
                                emoji=lib.emojis.BasedEmoji.fromStr(weaponDict["emoji"]) \
                                        if "emoji" in weaponDict else lib.emojis.BasedEmoji.EMPTY))
