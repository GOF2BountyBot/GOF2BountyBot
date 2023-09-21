from typing import Union
from typing_extensions import NotRequired

from .... import lib
from ....baseClasses.aliasable_json import SerializedAliasable


class SerializedItemBase(SerializedAliasable):
    id: int
    value: int
    manufacturer: NotRequired[str]
    wikiUrl: NotRequired[str]
    iconUrl: str
    emoji: NotRequired[lib.emojis.SerializedBasedEmoji]
    techLevel: NotRequired[int]


class TypedSerializedItemBase(SerializedItemBase):
    type: str


class AnySerializedItemBase(SerializedItemBase):
    type: NotRequired[str]


SerializedItemBaseUnion = Union[SerializedItemBase, TypedSerializedItemBase]
