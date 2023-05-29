from . import moduleItem
from ....cfg import bbData
from .... import lib
from typing import List, Union, cast
from ..gameItem import spawnableItem, BuiltInSerializedGameItem
from ....baseClasses.serializable import SerializesToSchema
from ....baseClasses.embedFillable import EmbedFillableMixin, embedField

class SerializedRepairBeamModule(moduleItem.CustomSerializedModuleItem):
    effect: float
    count: int

class TypedSerializedRepairBeamModule(SerializedRepairBeamModule, moduleItem.TypedCustomSerializedModuleItem): ...

CustomSerializedRepairBeamModuleUnion = Union[SerializedRepairBeamModule, TypedSerializedRepairBeamModule]
SerializedRepairBeamModuleUnion = Union[SerializedRepairBeamModule, TypedSerializedRepairBeamModule, BuiltInSerializedGameItem]


@spawnableItem
class RepairBeamModule(moduleItem.ModuleItem, EmbedFillableMixin, SerializesToSchema[SerializedRepairBeamModuleUnion]):
    """A module providing a ship with the ability to slowly add health points to nearby friendly ships

    :var effect: The amount of health added to nearby ships per time quantum
    :vartype effect: float
    :var count: The number of nearby ships that can be healed simultaneously
    :vartype count: int
    """

    def __init__(self, name: str, aliases: List[str], effect: float = 0, count: int = 0, value: int = 0,
            wiki: str = "", manufacturer: str = "", icon: str = "",
            emoji: lib.emojis.BasedEmoji = lib.emojis.BasedEmoji.EMPTY, techLevel: int = -1,
            builtIn: bool = False):
        """
        :param str name: The name of the module. Must be unique.
        :param list[str] aliases: Alternative names by which this module may be referred to
        :param float effect: The amount of health added to nearby ships per time quantum (Default 0)
        :param int count: The number of nearby ships that can be healed simultaneously (Default 0)
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
        super(RepairBeamModule, self).__init__(name, aliases, value=value, wiki=wiki, manufacturer=manufacturer, icon=icon,
                                                emoji=emoji, techLevel=techLevel, builtIn=builtIn)

        self.effect = effect
        self.count = count

#region embed fields

    @embedField("Effect")
    def formattedEffect(self): return f"{self.effect*100}%"
    
    @embedField("Count")
    def formattedCount(self): return self.count

#endregion

    def statsStringShort(self):
        return "*Effect: " + moduleItem.lib.stringTyping.formatMultiplier(self.effect) \
                + ", Count: " + lib.stringTyping.formatAdditive(self.count) + "*"


    def serialize(self, **kwargs) -> SerializedRepairBeamModuleUnion:
        """Serialize this module into dictionary format, to be saved to file. Uses the base moduleItem
        serialize method as a starting point, and adds extra attributes implemented by this specific module.

        :return: A dictionary containing all information needed to reconstruct this module
        :rtype: dict
        """
        itemDict = super(RepairBeamModule, self).serialize(**kwargs)
        if not self.builtIn:
            # Casting here to remove the possibility of builtIn due to the above check
            itemDict = cast(CustomSerializedRepairBeamModuleUnion, itemDict)
            itemDict["effect"] = self.effect
            itemDict["count"] = self.count
        return itemDict


    @classmethod
    def deserialize(cls, moduleDict: SerializedRepairBeamModuleUnion, **kwargs):
        """Factory function building a new module object from the information in the provided dictionary.
        The opposite of this class's serialize function.

        :param moduleDict: A dictionary containing all information needed to construct the requested module
        :return: The new module object as described in moduleDict
        :rtype: dict
        """
        if moduleDict.get("builtIn", False):
            return bbData.builtInModuleObjs[moduleDict["name"]]

        # Casting here because due to the above check, we know that the module is not builtIn
        moduleDict = cast(CustomSerializedRepairBeamModuleUnion, moduleDict)
        return RepairBeamModule(**cls._makeDefaults(moduleDict, ignores=("type",),
                                                emoji=lib.emojis.BasedEmoji.fromStr(moduleDict["emoji"]) \
                                                        if "emoji" in moduleDict else lib.emojis.BasedEmoji.EMPTY))
