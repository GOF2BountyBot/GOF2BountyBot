from typing import Any, Generic, List, Optional, TypeVar, cast

from sqlalchemy.orm import Mapped, DeclarativeBase

from discord import User

from .criminal_json import SerializedCriminal
from ...cfg import bbData
from ...baseClasses.aliasable import AliasableMixin
from ...baseClasses.aliasable_json import SerializedAliasable
from ...baseClasses.wikiEntity import SqlNamedWikiEntity
from ...baseClasses.embedFillable import embedField, embedThumbnailUrl, embedColour
from ...lib.discordUtil import ZWSP

class Base(DeclarativeBase):
    pass


TSchema = TypeVar("TSchema", bound=SerializedCriminal)

class Criminal(Base, AliasableMixin[TSchema], SqlNamedWikiEntity, Generic[TSchema]):
    """A criminal to be wanted in bounties.

    :var int id: The id of the criminal
    :var str name: The name of the criminal
    :var Collection[str] aliases: A list of alternative names
    :var str faction: the faction that this criminal is wanted by
    :var str iconUrl: A URL pointing to an image to use as the criminal's icon
    :var bool isPlayer: Whether this criminal represents a real player, rather than an NPC
    """
    id: Mapped[int]
    name: Mapped[str]
    isPlayer: Mapped[bool]
    faction: Mapped[str]
    iconUrl: Mapped[str]

    def __init__(self, name: str, aliases: Optional[List[str]] = None, isPlayer: bool = False, id: Optional[int] = None, *args: Any, forceAllowEmpty: bool = False, **kwargs: Any):
        if isPlayer:
            if id is None:
                raise ValueError("id is required for player criminals")
            idStr = str(id)
            if not aliases or idStr not in aliases:
                aliases = (aliases or []) + [idStr]

        super().__init__(name, aliases or [], *args, forceAllowEmpty=forceAllowEmpty, **kwargs)


    @embedThumbnailUrl
    @property
    def formattedIconUrl(self): return self.iconUrl


    @embedField("Wanted By")
    @property
    def formattedFaction(self): return self.faction.title() + "s"


    @embedColour
    def filledEmbedColour(self): return bbData.factionColours.get(self.faction, None)


    @embedField(fieldName=ZWSP, showInline=False, showLast=True, hideWhenNone=True, uniqueFieldName=False)
    @property
    def wikiNamedHyperlink(self) -> Optional[str]:
        """Override the wiki embed field to remove it for players (they have no wiki)
        """
        return None if self.isPlayer else super().wikiNamedHyperlink


    async def serialize(self, **kwargs: Any) -> TSchema:
        """Serialize this criminal into dictionary format, for saving to file.

        :return: A dictionary containing all data necessary to replicate this object
        :rtype: dict
        """
        aliasableData: SerializedAliasable = await super().serialize(**kwargs)
        data: SerializedCriminal = {
            **aliasableData,
            "id": self.id, "isPlayer": self.isPlayer, "iconUrl": self.iconUrl,
            "faction": self.faction
        }
        return cast(TSchema, data)


    @classmethod
    async def deserialize(cls, data: TSchema, **kwargs: Any) -> "Criminal[TSchema]":
        """Factory function that will construct a new criminal object from the provided data.

        :param dict crimDict: A dictionary containing all data necessary to construct the desired criminal.
        :return: The requested criminal
        :rtype: criminal
        """
        return Criminal(**cls._makeDefaults(data, ("type",),))
    

    @classmethod
    def forUser(cls, dcUser: User, faction: str):
        return AnyCriminal(name=dcUser.name, id=dcUser.id, isPlayer=True, faction=faction, iconUrl=dcUser.display_avatar.url)


AnyCriminal = Criminal[SerializedCriminal]
