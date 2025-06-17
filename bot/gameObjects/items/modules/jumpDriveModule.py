from bot.gameObjects.items.modules import moduleItem
from bot.cfg import bbData
from bot import lib
from typing import List, cast
from bot.gameObjects.items.gameItem import spawnableItem


@spawnableItem
class JumpDriveModule(moduleItem.ModuleItem):
    """"A module providing a ship with the ability to jump anywhere within the galaxy, without the need to use jumpgates
    """

    def __init__(self, name: str, aliases: List[str], value: int = 0,
            wiki: str = "", manufacturer: str = "", icon: str = "",
            emoji: lib.emojis.BasedEmoji = lib.emojis.BasedEmoji.EMPTY, techLevel: int = -1,
            builtIn: bool = False):
        """
        :param str name: The name of the module. Must be unique.
        :param list[str] aliases: Alternative names by which this module may be referred to
        :param int value: The number of credits this module may be sold or bought or at a shop (Default 0)
        :param str wiki: A web page that is displayed as the wiki page for this module. (Default "")
        :param str manufacturer: The name of the manufacturer of this module (Default "")
        :param str icon: A URL pointing to an image to use for this module's icon (Default "")
        :param lib.emojis.BasedEmoji emoji: The emoji to use for the module's small icon (Default lib.emojis.BasedEmoji.EMPTY)
        :param int techLevel: A rating from 1 to 10 of this item's technical advancement. Used
                                as a measure for its effectiveness compared to other modules of the same type (Default -1)
        :param bool builtIn: Whether this is a BountyBot standard module (loaded in from bbData) or
                                a custom spawned module (Default False)
        """
        super(JumpDriveModule, self).__init__(name, aliases, value=value, wiki=wiki, manufacturer=manufacturer, icon=icon,
                                                emoji=emoji, techLevel=techLevel, builtIn=builtIn)


    @classmethod
    def deserialize(cls, moduleDict: moduleItem.SerializedModuleItemUnion, **kwargs):
        """Factory function building a new module object from the information in the provided dictionary.
        The opposite of this class's serialize function.

        :param moduleDict: A dictionary containing all information needed to construct the requested module
        :return: The new module object as described in moduleDict
        :rtype: dict
        """
        if moduleDict.get("builtIn", False):
            return bbData.builtInModuleObjs[moduleDict["name"]]

        # Casting here because due to the above check, we know that the module is not builtIn
        moduleDict = cast(moduleItem.CustomSerializedModuleItemUnion, moduleDict)
        return JumpDriveModule(**cls._makeDefaults(moduleDict, ignores=("type",),
                                                emoji=lib.emojis.BasedEmoji.fromStr(moduleDict["emoji"]) \
                                                        if "emoji" in moduleDict else lib.emojis.BasedEmoji.EMPTY))
