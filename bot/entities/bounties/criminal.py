# Typing imports
from __future__ import annotations
from typing import Any, TypeVar, cast

from sqlalchemy.orm import Mapped

from .criminal_json import SerializedCriminal
from ...cfg import bbData
from ...baseClasses.aliasable import AliasableMixin
from ...baseClasses.aliasable_json import SerializedAliasable
from ...baseClasses.wikiEntity import NamedWikiEntity
from ...baseClasses.embedFillable import embedField, embedThumbnailUrl, embedColour

TSchema = TypeVar("TSchema", bound=SerializedCriminal)

class Criminal(AliasableMixin[TSchema], NamedWikiEntity):
    """A criminal to be wanted in bounties.

    :var int id: The id of the criminal
    :var str name: The name of the criminal
    :var Collection[str] aliases: A list of alternative names
    :var str faction: the faction that this criminal is wanted by
    :var str iconUrl: A URL pointing to an image to use as the criminal's icon
    :var bool isPlayer: Whether this criminal represents a real player, rather than an NPC
    """
    id: Mapped[int]
    isPlayer: Mapped[bool]
    faction: Mapped[str]
    iconUrl: Mapped[str]


    @embedThumbnailUrl
    @property
    def formattedIconUrl(self): return self.iconUrl


    @embedField("Wanted By")
    @property
    def formattedFaction(self): return self.faction.title() + "s"


    @embedColour
    def filledEmbedColour(self): return bbData.factionColours.get(self.faction, None)


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
    async def deserialize(cls, data: TSchema, **kwargs: Any) -> Criminal[TSchema]:
        """Factory function that will construct a new criminal object from the provided data.

        :param dict crimDict: A dictionary containing all data necessary to construct the desired criminal.
        :return: The requested criminal
        :rtype: criminal
        """
        return Criminal(**cls._makeDefaults(data, ("type",),))
