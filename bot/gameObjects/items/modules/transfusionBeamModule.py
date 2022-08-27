from . import moduleItem
from ....cfg import bbData
from .... import lib
from typing import List, Union, cast
from ..gameItem import spawnableItem, BuiltInSerializedGameItem

class SerializedTransfusionBeamModule(moduleItem.SerializedModuleItem):
    HPps: int
    count: int

class TypedSerializedTransfusionBeamModule(SerializedTransfusionBeamModule, moduleItem.TypedSerializedModuleItem): ...

CustomSerializedTransfusionBeamModuleUnion = Union[SerializedTransfusionBeamModule, TypedSerializedTransfusionBeamModule]
SerializedTransfusionBeamModuleUnion = Union[SerializedTransfusionBeamModule, TypedSerializedTransfusionBeamModule, BuiltInSerializedGameItem]


@spawnableItem
class TransfusionBeamModule(moduleItem.ModuleItem):
    """A module that slowly steals health from nearby ships, and adds the stolen heath to this ship's health.

    :var HPps: The amount of health points per second to steal
    :vartype HPps: int
    :var count: The number of ships from which health may be stolen simultaneously
    :vartype count: int
    """

    def __init__(self, name: str, aliases: List[str], HPps: int = 0, count: int = 0,
            value: int = 0, wiki: str = "", manufacturer: str = "", icon: str = "",
            emoji: lib.emojis.BasedEmoji = lib.emojis.BasedEmoji.EMPTY, techLevel: int = -1,
            builtIn: bool = False):
        """
        :param str name: The name of the module. Must be unique.
        :param list[str] aliases: Alternative names by which this module may be referred to
        :param int HPps: The amount of health points per second to steal (Default 0)
        :param int count: The number of ships from which health may be stolen simultaneously (Default 0)
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
        super(TransfusionBeamModule, self).__init__(name, aliases, value=value, wiki=wiki, manufacturer=manufacturer,
                                                    icon=icon, emoji=emoji, techLevel=techLevel, builtIn=builtIn)

        self.HPps = HPps
        self.count = count


    def statsStringShort(self):
        return "*HP/s: " + str(self.HPps) + ", Count: " + str(self.count) + "*"


    def serialize(self, **kwargs) -> SerializedTransfusionBeamModuleUnion:
        """Serialize this module into dictionary format, to be saved to file. Uses the base moduleItem
        serialize method as a starting point, and adds extra attributes implemented by this specific module.

        :return: A dictionary containing all information needed to reconstruct this module
        :rtype: dict
        """
        itemDict = super(TransfusionBeamModule, self).serialize(**kwargs)
        if not self.builtIn:
            # Casting here to remove the possibility of builtIn due to the above check
            itemDict = cast(CustomSerializedTransfusionBeamModuleUnion, itemDict)
            itemDict["HPps"] = self.HPps
            itemDict["count"] = self.count
        return itemDict


    @classmethod
    def deserialize(cls, moduleDict: SerializedTransfusionBeamModuleUnion, **kwargs):
        """Factory function building a new module object from the information in the provided dictionary.
        The opposite of this class's serialize function.

        :param moduleDict: A dictionary containing all information needed to construct the requested module
        :return: The new module object as described in moduleDict
        :rtype: dict
        """
        if moduleDict.get("builtIn", False):
            return bbData.builtInModuleObjs[moduleDict["name"]]

        # Casting here because due to the above check, we know that the module is not builtIn
        moduleDict = cast(CustomSerializedTransfusionBeamModuleUnion, moduleDict)
        return TransfusionBeamModule(**cls._makeDefaults(moduleDict, ignores=("type",),
                                                emoji=lib.emojis.BasedEmoji.fromStr(moduleDict["emoji"]) \
                                                        if "emoji" in moduleDict else lib.emojis.BasedEmoji.EMPTY))
