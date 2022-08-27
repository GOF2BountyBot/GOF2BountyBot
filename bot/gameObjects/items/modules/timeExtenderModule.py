from . import moduleItem
from ....cfg import bbData
from .... import lib
from typing import List, Union, cast
from ..gameItem import spawnableItem, BuiltInSerializedGameItem

class SerializedTimeExtenderModule(moduleItem.SerializedModuleItem):
    effect: float
    duration: float

class TypedSerializedTimeExtenderModule(SerializedTimeExtenderModule, moduleItem.TypedSerializedModuleItem): ...

CustomSerializedTimeExtenderModuleUnion = Union[SerializedTimeExtenderModule, TypedSerializedTimeExtenderModule]
SerializedTimeExtenderModuleUnion = Union[SerializedTimeExtenderModule, TypedSerializedTimeExtenderModule, BuiltInSerializedGameItem]


@spawnableItem
class TimeExtenderModule(moduleItem.ModuleItem):
    """A module that will slow down time around the ship. The ship remains unaffected.

    :var effect: The amount to slow down time as a multiplier
    :vartype effect: float
    :var duration: The perceived duration in seconds of the effect from the perspective of the pilot
    :vartype duration: float
    """

    def __init__(self, name: str, aliases: List[str], effect: float = 1, duration: float = 0, value: int = 0,
            wiki: str = "", manufacturer: str = "", icon: str = "",
            emoji: lib.emojis.BasedEmoji = lib.emojis.BasedEmoji.EMPTY, techLevel: int = -1,
            builtIn: bool = False):
        """
        :param str name: The name of the module. Must be unique.
        :param list[str] aliases: Alternative names by which this module may be referred to
        :param float effect: The amount to slow down time as a multiplier (Default 1)
        :param float duration: The perceived duration in seconds of the effect from the perspective of the pilot (Default 0)
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
        super(TimeExtenderModule, self).__init__(name, aliases, value=value, wiki=wiki, manufacturer=manufacturer, icon=icon,
                                                    emoji=emoji, techLevel=techLevel, builtIn=builtIn)

        self.effect = effect
        self.duration = duration


    def statsStringShort(self):
        return "*Effect: " + moduleItem.lib.stringTyping.formatMultiplier(self.effect) \
                + ", Duration: " + moduleItem.lib.stringTyping.formatAdditive(self.duration) + "s*"


    def serialize(self, **kwargs) -> SerializedTimeExtenderModuleUnion:
        """Serialize this module into dictionary format, to be saved to file. Uses the base moduleItem
        serialize method as a starting point, and adds extra attributes implemented by this specific module.

        :return: A dictionary containing all information needed to reconstruct this module
        :rtype: dict
        """
        itemDict = super(TimeExtenderModule, self).serialize(**kwargs)
        if not self.builtIn:
            # Casting here to remove the possibility of builtIn due to the above check
            itemDict = cast(CustomSerializedTimeExtenderModuleUnion, itemDict)
            itemDict["effect"] = self.effect
            itemDict["duration"] = self.duration
        return itemDict


    @classmethod
    def deserialize(cls, moduleDict: SerializedTimeExtenderModuleUnion, **kwargs):
        """Factory function building a new module object from the information in the provided dictionary.
        The opposite of this class's serialize function.

        :param moduleDict: A dictionary containing all information needed to construct the requested module
        :return: The new module object as described in moduleDict
        :rtype: dict
        """
        if moduleDict.get("builtIn", False):
            return bbData.builtInModuleObjs[moduleDict["name"]]

        # Casting here because due to the above check, we know that the module is not builtIn
        moduleDict = cast(CustomSerializedTimeExtenderModuleUnion, moduleDict)
        return TimeExtenderModule(**cls._makeDefaults(moduleDict, ignores=("type",),
                                                emoji=lib.emojis.BasedEmoji.fromStr(moduleDict["emoji"]) \
                                                        if "emoji" in moduleDict else lib.emojis.BasedEmoji.EMPTY))
