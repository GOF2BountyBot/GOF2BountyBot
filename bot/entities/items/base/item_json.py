from typing import Union
from typing_extensions import NotRequired

from .... import lib
from ....baseClasses.aliasable_json import SerializedAliasable


class SerializedItem(SerializedAliasable):
    id: int
    value: int
    manufacturer: NotRequired[str]
    wikiUrl: NotRequired[str]
    iconUrl: str
    emoji: NotRequired[lib.emojis.SerializedBasedEmoji]
    techLevel: NotRequired[int]


class TypedSerializedItem(SerializedItem):
    type: str


class AnySerializedItem(SerializedItem):
    type: NotRequired[str]


SerializedItemUnion = Union[SerializedItem, TypedSerializedItem]
