# Typing imports
from __future__ import annotations
from typing import List, Optional, Union

from ...cfg import bbData
from ...baseClasses import aliasable
from ..gameObject import LoadedObject, SerializedLoadedObject
from ...baseClasses.embedFillable import embedField, embedThumbnailUrl, embedColour, embedFooterUrl
from ...baseClasses.serializable import SerializesToSchema

class BuiltInSerializedCriminal(aliasable.SerializedAliasable, SerializedLoadedObject): pass

class TypedBuiltInSerializedCriminal(BuiltInSerializedCriminal):
    type: str

class CustomSerializedCriminal(BuiltInSerializedCriminal):
    isPlayer: bool
    icon: str
    faction: str
    aliases: List[str]

class TypedCustomSerializedCriminal(CustomSerializedCriminal, TypedBuiltInSerializedCriminal): pass

BuiltInSerializedCriminalUnion = Union[BuiltInSerializedCriminal, TypedBuiltInSerializedCriminal]
CustomSerializedCriminalUnion = Union[CustomSerializedCriminal, TypedCustomSerializedCriminal]
SerializedCriminalUnion = Union[BuiltInSerializedCriminal, TypedBuiltInSerializedCriminal, CustomSerializedCriminal, TypedCustomSerializedCriminal]


class Criminal(aliasable.AliasableMixin, LoadedObject, SerializesToSchema[SerializedCriminalUnion]):
    """A criminal to be wanted in bounties.

    :var name: The name of the criminal
    :vartype name: str
    :var faction: the faction that this criminal is wanted by
    :vartype faction: str
    :var icon: A URL pointing to an image to use as the criminal's icon
    :vartype icon: str
    :var wiki: A URL pointing to a web page to use as this criminal's wiki page in their info embed
    :vartype wiki: str
    :var hasWiki: Whether or not this criminal has a wiki page
    :vartype hasWiki: bool
    :var isPlayer: Whether this criminal is a player or an NPC
    :vartype isPlayer: bool
    :var builtIn: If this criminal is an NPC, are they built in or custom?
    :vartype builtIn: bool
    """

    def __init__(self, name: str, faction: str, icon: str, builtIn: bool = False,
                    isPlayer: bool = False, aliases: List[str] = [], wiki: Optional[str] = None):
        """
        :param str name: The name of the criminal
        :param str faction: the faction that this criminal is wanted by
        :param str icon: A URL pointing to an image to use as the criminal's icon
        :param str wiki: A URL pointing to a web page to use as this criminal's wiki page in their info embed
        :param bool isPlayer: Whether this criminal is a player or an NPC
        :param bool builtIn: If this criminal is an NPC, are they built in or custom?
        :param list[str] aliases: Alias names that can be used to refer to this criminal
        """
        super().__init__(name=name, aliases=aliases, wiki=wiki, builtIn=builtIn)
        if name == "":
            raise RuntimeError("CRIM_CONS_NONAM: Attempted to create a Criminal with an empty name")
        # if faction == "":
        #     raise RuntimeError("CRIM_CONS_NOFAC: Attempted to create a Criminal with an empty faction")
        if faction == "":
            raise RuntimeError("CRIM_CONS_NOICO: Attempted to create a Criminal with an empty icon")

        self.faction = faction
        self._icon = icon
        self.isPlayer = isPlayer


    @embedThumbnailUrl
    @property
    def icon(self): return self._icon


    @embedField("Wanted By")
    @property
    def formattedFaction(self): return self.faction.title() + "s"


    @embedColour
    def filledEmbedColour(self): return bbData.factionColours.get(self.faction, None)


    def serialize(self, **kwargs) -> SerializedCriminalUnion:
        """Serialize this criminal into dictionary format, for saving to file.

        :return: A dictionary containing all data necessary to replicate this object
        :rtype: dict
        """
        if self.builtIn:
            return {"builtIn":True, "name":self.name}
        else:
            return {"builtIn": False, "isPlayer": self.isPlayer, "name": self.name, "icon": self.icon,
                    "faction": self.faction, "aliases": self.aliases, "wiki": self.wiki}


    @classmethod
    def deserialize(cls, crimDict: SerializedCriminalUnion, **kwargs) -> Criminal:
        """Factory function that will either provide a reference to a builtIn criminal if a builtIn criminal is requested,
        or construct a new criminal object from the provided data.

        :param dict crimDict: A dictionary containing all data necessary to construct the desired criminal.
                                If the criminal is builtIn, this need only be their name and "builtIn": True.
        :return: The requested criminal object reference
        :rtype: criminal
        """
        if kwargs.get("builtIn", False) or crimDict.get("builtIn", False):
            return bbData.builtInCriminalObjs[crimDict["name"]]
        return Criminal(**cls._makeDefaults(crimDict, ("type",),))
