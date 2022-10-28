# Typing imports
from __future__ import annotations
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, cast

from ...baseClasses import aliasable, serializable
from ...baseClasses.embedFillable import EmbedFillableMixin, embedField, embedThumbnailUrl, embedColour
from abc import abstractmethod
from ... import lib
from ...lib import gameMaths
from ...lib.stringTyping import commaSplitNum
from ...cfg import bbData, cfg
from..gameObject import LoadedObject, SerializedLoadedObject


class BuiltInSerializedGameItem(SerializedLoadedObject, aliasable.SerializedAliasable): pass

class CustomSerializedGameItem(BuiltInSerializedGameItem):
    value: int
    manufacturer: str
    icon: str
    emoji: lib.emojis.SerializedBasedEmoji
    techLevel: int


class TypedCustomSerializedGameItem(CustomSerializedGameItem):
    type: str

class TypedBuiltInSerializedGameItem(BuiltInSerializedGameItem):
    type: str


CustomSerializedGameItemUnion = Union[CustomSerializedGameItem, TypedCustomSerializedGameItem]
BuiltInSerializedGameItemUnion = Union[BuiltInSerializedGameItem, TypedBuiltInSerializedGameItem]
SerializedGameItemUnion = Union[CustomSerializedGameItem, BuiltInSerializedGameItemUnion]

TypedSerializedGameItemUnion = Union[TypedCustomSerializedGameItem, TypedBuiltInSerializedGameItem]

subClassNames: Dict[str, Type["GameItem"]] = {}
nameSubClasses: Dict[Type["GameItem"], str] = {}


class GameItem(aliasable.AliasableMixin, LoadedObject, EmbedFillableMixin, serializable.SerializesToSchema[SerializedGameItemUnion]):
    """A game item, with a value, a manufacturer, a wiki page, an icon, an emoji, and a tech level.

    :var wiki: A web page to represent as the item's wikipedia article in its info page
    :vartype wiki: str
    :var hasWiki: Whether or not this item's wiki attribute is populated
    :vartype hasWiki: bool
    :var manufacturer: The manufacturer of this item
    :vartype manufacturer: str
    :var hasManufacturer: Whether or not this item has a manufacturer
    :vartype hasManufacturer: bool
    :var icon: A URL linking to an image to use as this item's icon
    :vartype icon: str
    :var hasIcon: Whether or not this item has an icon
    :vartype hasIcon: bool
    :var emoji: An emoji reference to use as this item's small icon
    :vartype emoji: bbUti.BasedEmoji
    :var hasEmoji: whether or not this item has an emoji
    :vartype hasEmoji: bool
    :var value: The number of credits this item can be bought/sold for at the shop
    :vartype value: int
    :var shopSpawnRate: A pre-calculated float indicating the highest spawn rate of this item
                        (i.e its spawn probability for a shop of the same techLevel)
    :vartype shopSpawnRate: float
    :var techLevel: A rating from 1 to 10 of this item's technological advancement.
                    Used as a reference to compare against other items of the same type.
    :vartype techLevel: int
    :var hasTechLevel: whether or not this item has a tech level
    :vartype hasTechLevel: bool
    :var builtIn: Whether this item is built into BountyBot (loaded in from bbData) or was custom spawned.
    :vartype builtIn: bool
    """

    def __init__(self, name: str, aliases: List[str], value: int = 0,
            wiki: str = "", manufacturer: str = "", icon: str = "",
            emoji: lib.emojis.BasedEmoji = lib.emojis.BasedEmoji.EMPTY, techLevel: int = -1,
            builtIn: bool = False):
        """
        :param str name: The name of the item. Must be unique. (a model number is a good starting point)
        :param list[str] aliases: A list of alternative names this item may be referred to by.
        :param int value: The number of credits that this item can be bought/sold for at a shop. (Default 0)
        :param str wiki: A web page that is displayed as the wiki page for this item. (Default "")
        :param str manufacturer: The name of the manufacturer of this item (Default "")
        :param str icon: A URL pointing to an image to use for this item's icon (Default "")
        :param lib.emojis.BasedEmoji emoji: The emoji to use for this item's small icon (Default lib.emojis.BasedEmoji.EMPTY)
        :param int techLevel: A rating from 1 to 10 of this item's technical advancement. Used as a measure for its
                                effectiveness compared to other items of the same type (Default -1)
        :param bool builtIn: Whether this is a BountyBot standard item (loaded in from bbData)
                                or a custom spawned item (Default False)
        """
        super(GameItem, self).__init__(name, aliases, builtIn=builtIn, wiki=wiki)

        self.manufacturer = manufacturer
        self.hasManufacturer = manufacturer != ""

        self.icon = icon
        self.hasIcon = icon != ""

        self.emoji = emoji
        self.hasEmoji = emoji is not None and emoji != lib.emojis.BasedEmoji.EMPTY

        self.value = value
        self.shopSpawnRate = 0

        self.techLevel = techLevel
        self.hasTechLevel = techLevel != -1

#region embed attributes

    @embedThumbnailUrl
    def iconOrNone(self): return self.icon if self.hasIcon else None

    @embedField("Manufacturer", hideWhenNone=True)
    def formattedManufacturer(self): return self.manufacturer.title() if self.hasManufacturer else None

    @embedField("Value")
    def formattedValue(self): return f"{commaSplitNum(self.value)} Credits"

    @embedField("Tech Level", hideWhenNone=True)
    def formattedTechLevel(self): return self.techLevel if self.hasTechLevel else None

    @embedColour
    def manufacturerColour(self): return bbData.factionColours.get(self.manufacturer, bbData.factionColours["neutral"])

#endregion


    @abstractmethod
    def statsStringShort(self) -> str:
        """Summarise all the statistics and functionality of this item as a string.

        :return: A string summarising the statistics and functionality of this item
        :rtype: str
        """
        return "*No effect*"


    def getValue(self) -> int:
        """Get the base value of this item with no additions or modifications.

        :return: The item's base value
        :rtype: int
        """
        return self.value


    @abstractmethod
    def serialize(self, saveType: Optional[bool] = False, **kwargs) -> SerializedGameItemUnion:
        """Serialize this item into dictionary format, for saving to file.
        This base implementation should be used in gameItem implementations, and custom attributes saved into it.

        :param bool saveType: When true, include the string name of the object type in the output.
        :return: A dictionary containing all information needed to reconstruct this item.
                    If the item is builtIn, this is only its name.
        :rtype: dict
        """
        if self.builtIn:
            data: BuiltInSerializedGameItem = {"name": self.name, "builtIn": True}
        else:
            data = cast(CustomSerializedGameItemUnion, super().serialize(**kwargs))
            data["value"] = self.value
            data["wiki"] = self.wiki
            data["manufacturer"] = self.manufacturer
            data["icon"] = self.icon
            data["emoji"] = self.emoji.serialize(**kwargs)
            data["techLevel"] = self.techLevel
            data["builtIn"] = False

        if saveType:
            data = cast(TypedSerializedGameItemUnion, data)
            data["type"] = type(self).__name__

        return data


TClass = TypeVar("TClass", bound=Type[GameItem])


def spawnableItem(cls: TClass) -> TClass:
    if not isinstance(cls, type):
        raise ValueError("spawnableItem can only be applied to classes")
    if not issubclass(cls, GameItem):
        raise TypeError("Invalid use of spawnableItem decorator: " + cls.__name__ + " is not a gameItem subtype")
    if cls not in nameSubClasses:
        nameSubClasses[cls] = cls.__name__
    if cls.__name__ not in subClassNames:
        subClassNames[cls.__name__] = cls
    return cast(TClass, cls)


def spawnItem(data: TypedCustomSerializedGameItem) -> GameItem:
    if "type" not in data or data["type"] == "":
        raise NameError("Not given a type")
    elif data["type"] not in subClassNames:
        raise KeyError("Unrecognised item type: " + str(data["type"]))

    return subClassNames[data["type"]].deserialize(data)


def isSpawnableItemClass(cls):
    return issubclass(cls, GameItem) and cls in nameSubClasses


def spawnableItemClassFromName(n: str) -> Type[GameItem]:
    return subClassNames[n]


def isSpawnableItemInstance(o):
    return isinstance(o, GameItem) and type(o) in nameSubClasses


def topThreeItemSpawnRates(item: GameItem, shopPool: List[List[Any]]) -> Optional[str]:
    """Get a string describing the top 3 spawn rates for an item with tech level `tl`.

    :param item: The item
    :type item: GameItem
    :param shopPool: The shop's techlevel-sorted pool of items
    :type shopPool: List[List[Any]]
    :return: A string describing the item's top 3 spawn rates, or None if `tl` is invalid
    :rtype: Optional[str]
    """
    if not item.hasTechLevel or item.techLevel < cfg.minTechLevel or item.techLevel > cfg.maxTechLevel:
        return None
    
    tlRange = range(max(item.techLevel - 1, cfg.minTechLevel), min(item.techLevel + 1, cfg.maxTechLevel) + 1)
    rates = [(tl, gameMaths.itemTLSpawnChanceForShopTL[tl - 1][item.techLevel - 1]) for tl in tlRange if shopPool[tl - 1]]
    return "\n".join(f"Level {tl} Shops: {round((rate/len(shopPool[tl - 1]))*100, 2)}%" for tl, rate in rates)