from __future__ import annotations
from ..gameItem import GameItem
from .... import lib
from typing import List


class Weapon(GameItem):
    """An abstract class representing weapons that can be equipped onto a bbShip for use in duels.

    :var dps: The weapon's damage per second to a target ship.
    :vartype dps: float
    """

    def __init__(self, name : str, aliases : List[str], dps : float = 0.0, value : int = 0,
            wiki : str = "", manufacturer : str = "", icon : str = "",
            emoji : lib.emojis.BasedEmoji = lib.emojis.BasedEmoji.EMPTY, techLevel : int = -1, builtIn : bool = False):
        """
        :param str name: The name of the weapon. Must be unique. (a model number is a good starting point)
        :param list[str] aliases: A list of alternative names this weapon may be referred to by.
        :param int valie: The amount of credits that this weapon can be bought/sold for at a shop. (Default 0)
        :param float dps: The weapon's damage per second to a target ship. (Default 0)
        :param str wiki: A web page that is displayed as the wiki page for this weapon. (Default "")
        :param str manufacturer: The name of the manufacturer of this weapon (Default "")
        :param str icon: A URL pointing to an image to use for this weapon's icon (Default "")
        :param lib.emojis.BasedEmoji emoji: The emoji to use for the weapon's small icon (Default lib.emojis.BasedEmoji.EMPTY)
        :param int techLevel: A rating from 1 to 10 of this weapon's technical advancement. Used as a measure for its
                                effectiveness compared to other weapons of the same type (Default -1)
        :param bool builtIn: Whether this is a BountyBot standard weapon (loaded in from bbData) or a
                                custom spawned weapon (Default False)
        """
        super(Weapon, self).__init__(name, aliases, value=value, wiki=wiki, manufacturer=manufacturer, icon=icon,
                                            emoji=emoji, techLevel=techLevel, builtIn=builtIn)

        self.dps = dps


    def statsStringShort(self) -> str:
        """Get a short string summary of the weapon. This currently only includes the DPS.

        :return: a short string summary of the weapon's statistics
        :rtype: str
        """
        return "*Dps: " + str(self.dps) + "*"


    def toDict(self, **kwargs) -> dict:
        """Serialize this item into dictionary format, for saving to file.

        :param bool saveType: When true, include the string name of the object type in the output.
        :return: A dictionary containing all information needed to reconstruct this weapon.
                    If the weapon is builtIn, this is only its name.
        :rtype: dict
        """
        itemDict = super(Weapon, self).toDict(**kwargs)
        if not self.builtIn:
            itemDict["dps"] = self.dps
        return itemDict
