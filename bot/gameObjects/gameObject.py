from typing import Optional, TypeVar, Type
from typing_extensions import NotRequired, TypedDict
from abc import abstractmethod

from bot.baseClasses.serializable import SerializesToSchema
from bot.baseClasses.embedFillable import EmbedFillableMixin, embedField

from bot.lib.discordUtil import ZWSP

TSelf = TypeVar("TSelf", bound="LoadedObject")

class SerializedLoadedObject(TypedDict):
    name: str
    builtIn: bool
    wiki: NotRequired[Optional[str]]


class LoadedObject(EmbedFillableMixin, SerializesToSchema[SerializedLoadedObject]):
    """ABC for objects that were loaded into the game from file.
    To allow for loading from config files, this must be serializable to JSON, and have a `builtIn` bool
    to indicate whether the object is BB official or custom.

    Also comes with `EmbedFillableMixin`, and an optional `wiki` property as an embed field.
    This field will always show last in the embed. It will have a non-unique ZWSP field name, and will only show if the object has a wiki.
    """
    def __init__(self, name: str, builtIn: bool = False, wiki: Optional[str] = None):
        self.builtIn = builtIn
        self.wiki = wiki
        self.name = name


    @embedField(fieldName=ZWSP, showInline=False, showLast=True, hideWhenNone=True, uniqueFieldName=False)
    @property
    def wikiNamedHyperlink(self):
        """A markdown hyperlink for this object's wiki, if it has one.
        """
        return f"[Wiki]({self.wiki})" if self.hasWiki else None


    @property
    def hasWiki(self): return self.wiki is not None and self.wiki != ""


    @abstractmethod
    def serialize(self, **kwargs) -> SerializedLoadedObject:
        data: SerializedLoadedObject = {"builtIn": self.builtIn, "name": self.name}
        if self.hasWiki:
            data["wiki"] = self.wiki
        return data


    @classmethod
    @abstractmethod
    def deserialize(cls: Type[TSelf], data: SerializedLoadedObject, **kwargs) -> TSelf: ...
