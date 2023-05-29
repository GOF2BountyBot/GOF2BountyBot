from . import moduleItem
from ....cfg import bbData
from .... import lib
from typing import List, Union, cast
from ..gameItem import spawnableItem, BuiltInSerializedGameItem
from ....baseClasses.serializable import SerializesToSchema
from ....baseClasses.embedFillable import EmbedFillableMixin, embedField

class SerializedMiningDrillModule(moduleItem.CustomSerializedModuleItem):
    oreYield: float
    drillHandling: float

class TypedSerializedMiningDrillModule(SerializedMiningDrillModule, moduleItem.TypedCustomSerializedModuleItem): ...

CustomSerializedMiningDrillModuleUnion = Union[SerializedMiningDrillModule, TypedSerializedMiningDrillModule]
SerializedMiningDrillModuleUnion = Union[SerializedMiningDrillModule, TypedSerializedMiningDrillModule, BuiltInSerializedGameItem]


@spawnableItem
class MiningDrillModule(moduleItem.ModuleItem, EmbedFillableMixin, SerializesToSchema[SerializedMiningDrillModuleUnion]):
    """"A module providing a ship with the ability to mine ore from asteroids

    :var oreYield: The percentage of the maximum ore this drill will receive from an asteroid
    :vartype oreYield: float
    :var drillHandling: The drill's ease of use
    :vartype drillHandling: float
    """

    def __init__(self, name: str, aliases: List[str], oreYield: float = 0, drillHandling: float = 0, value: int = 0,
            wiki: str = "", manufacturer: str = "", icon: str = "",
            emoji: lib.emojis.BasedEmoji = lib.emojis.BasedEmoji.EMPTY, techLevel: int = -1,
            builtIn: bool = False):
        """
        :param str name: The name of the module. Must be unique.
        :param list[str] aliases: Alternative names by which this module may be referred to
        :param float oreYield: The percentage of the maximum ore this drill will receive from an asteroid (Default 0)
        :param float drillHandling: The drill's ease of use (Default 0)
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
        super(MiningDrillModule, self).__init__(name, aliases, value=value, wiki=wiki, manufacturer=manufacturer, icon=icon,
                                                emoji=emoji, techLevel=techLevel, builtIn=builtIn)

        self.oreYield = oreYield
        self.drillHandling = drillHandling

#region embed fields

    @embedField("Ore Yield")
    def formattedYield(self): return f"{self.oreYield*100}%"
    
    @embedField("Handling")
    def formattedDrillHandling(self): return f"{self.drillHandling*100}%"

#endregion


    def statsStringShort(self):
        return "*Yield: " + moduleItem.lib.stringTyping.formatMultiplier(self.oreYield) \
                + ", Handling: " + lib.stringTyping.formatMultiplier(self.drillHandling) + "*"


    def serialize(self, **kwargs) -> SerializedMiningDrillModuleUnion:
        """Serialize this module into dictionary format, to be saved to file. Uses the base moduleItem serialize
        method as a starting point, and adds extra attributes implemented by this specific module.

        :return: A dictionary containing all information needed to reconstruct this module
        :rtype: dict
        """
        itemDict = super(MiningDrillModule, self).serialize(**kwargs)
        if not self.builtIn:
            # Casting here to remove the possibility of builtIn due to the above check
            itemDict = cast(CustomSerializedMiningDrillModuleUnion, itemDict)
            itemDict["oreYield"] = self.oreYield
            itemDict["drillHandling"] = self.drillHandling
        return itemDict


    @classmethod
    def deserialize(cls, moduleDict: SerializedMiningDrillModuleUnion, **kwargs):
        """Factory function building a new module object from the information in the provided dictionary.
        The opposite of this class's serialize function.

        :param moduleDict: A dictionary containing all information needed to construct the requested module
        :return: The new module object as described in moduleDict
        :rtype: dict
        """
        if moduleDict.get("builtIn", False):
            return bbData.builtInModuleObjs[moduleDict["name"]]

        # Casting here because due to the above check, we know that the module is not builtIn
        moduleDict = cast(CustomSerializedMiningDrillModuleUnion, moduleDict)
        return MiningDrillModule(**cls._makeDefaults(moduleDict, ignores=("type",),
                                                emoji=lib.emojis.BasedEmoji.fromStr(moduleDict["emoji"]) \
                                                        if "emoji" in moduleDict else lib.emojis.BasedEmoji.EMPTY))
