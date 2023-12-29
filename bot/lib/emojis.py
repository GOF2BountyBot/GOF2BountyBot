from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Optional, Protocol, Type, TypeVar, Union, cast, ClassVar, TypedDict, Any
from typing_extensions import TypeGuard, NotRequired

import emoji
import traceback
from abc import ABC, abstractmethod
import random

from discord import PartialEmoji, Emoji

from .. import botState
from . import exceptions, stringUtil
from ..baseClasses.serializable import SerializesToSchema, SerializesToSchemaProtocol
from ..baseClasses.simpleHash import simpleHash
from ..cfg import cfg


# True to raise an UnrecognisedCustomEmoji exception when requesting an unknown custom emoji
raiseUnkownEmojis = False
logUnknownEmojis = True
# Assumption of the maximum number of unicode characters in an emoji, just to put a cap on the time complexity of
# strisUnicodeEmoji. 10 characters makes sense as a 5-long ZWJ sequence plus a variation selector.
MAX_EMOJI_LEN = 10
# Special character indicating the display mode of an emoji
VAR_SELECTOR = "️"
# Regional indicator characters. Not technically classed as emojis, so they have to be special-cased.
REGIONAL_INDICATORS = ('🇦', '🇧', '🇨', '🇩', '🇪', '🇫', '🇬', '🇭', '🇮', '🇯', '🇰', '🇱', '🇲', \
                        '🇳', '🇴', '🇵', '🇶', '🇷', '🇸', '🇹', '🇺', '🇻', '🇼', '🇽', '🇾', '🇿')


def customEmojiIdFromString(s):
        return int(s[s[s.index(":") + 1:].index(":") + 3:-1])


def strIsUnicodeEmoji(c: str) -> bool:
    """Decide whether a given string contrains a single unicode emoji.

    :param str c: The string to test
    :return: True if c contains exactly one character, and that character is a unicode emoji. False otherwise.
    :rtype: bool
    """
    return len(c) <= MAX_EMOJI_LEN and (emoji.emoji_count(c) == 1 or c.rstrip(VAR_SELECTOR) in REGIONAL_INDICATORS)


def strIsCustomEmoji(s: str) -> bool:
    """Decide whether the given string matches the formatting of a discord custom emoji,
    being <:NAME:ID> where NAME is the name of the emoji, and ID is the integer ID.

    :param str c: The string to test
    :return: True if s 'looks like' a discord custom emoji, matching their structure. False otherwise.
    :rtype: bool
    """
    if s.startswith("<") and s.endswith(">"):
        try:
            first = s.index(":")
            second = first + s[first + 1:].index(":") + 1
        except ValueError:
            return False
        return stringUtil.isInt(s[second + 1:-1])
    return False


class SerializedUnicodeBasedEmoji(TypedDict):
    unicode: str
    id: NotRequired[int]
    empty: NotRequired[Literal[False]]

class SerializedCustomBasedEmoji(TypedDict):
    id: int
    unicode: NotRequired[str]
    empty: NotRequired[Literal[False]]

class SerializedEmptyBasedEmoji(TypedDict):
    empty: Literal[True]
    unicode: NotRequired[str]
    id: NotRequired[int]

SerializedBasedEmoji = Union[SerializedUnicodeBasedEmoji, SerializedCustomBasedEmoji, SerializedEmptyBasedEmoji]

T = TypeVar("T")
TSelf = TypeVar("TSelf")

class IBasedEmoji(SerializesToSchemaProtocol[SerializedBasedEmoji], Protocol):
    id: Optional[int]
    unicode: Optional[str]

    isCustom: bool
    isUnicode: bool
    isEmpty: bool
    sendable: str

    def verifyCustom(self, raiseOnUnknown: bool = False) -> bool: ...

    @classmethod
    def fromPartial(cls: Type[TSelf], e: PartialEmoji, raiseOnUnknown: bool = False) -> TSelf: ...

    @classmethod
    def fromReaction(cls: Type[TSelf], e: Union[Emoji, PartialEmoji, str], raiseOnUnknown: bool = False) -> TSelf: ...
        
    @classmethod
    def fromStr(cls: Type[TSelf], s: str, raiseOnUnknown: bool = False) -> TSelf: ...


'https://stackoverflow.com/a/53519136'
@simpleHash
@dataclass
class BasedEmoji(IBasedEmoji, SerializesToSchema[SerializedBasedEmoji]):
    """Unify over custom and unicode emojis.

    :var id: The ID of the Emoji that this object represents, if isID
    :vartype id: int
    :var unicode: The string unicode emoji that this object represents, if isUnicode
    :vartype unicode:
    :var sendable: A string sendable in a discord message that discord will render an emoji over.
    :vartype sendable: str
    :var EMPTY: static class variable representing an empty emoji
    :vartype EMPTY: BasedEmoji
    """
    id: Optional[int]
    unicode: Optional[str]

#region class variables

    # Casting here because I set this field immediately after class definition
    EMPTY: ClassVar["BasedEmoji"] = cast("BasedEmoji", None)
    _UNKNOWN: ClassVar[Optional["BasedEmoji"]] = None

    @property
    @classmethod
    def UNKNOWN(cls) -> "BasedEmoji":
        """An emoji to use in error states, in place of unknown emojis.
        This emoji is defined by `cfg.defaultEmojis.unrecognisedEmoji`.
        """
        if cls._UNKNOWN is None:
            cls._UNKNOWN = cfg.defaultEmojis.unrecognisedEmoji
        return cls._UNKNOWN
    
#endregion class variables
#region constructors

    def __init__(self, id: Optional[int] = None, unicode: Optional[str] = None):
        """
        :param Optional[int] id: The ID of the custom emoji that this object should represent.
        :param Optional[str] unicode: The unicode emoji that this object should represent.
        :raises ValueError: If none or both of `id` and `unicode` are provided
        """
        if not id and not unicode:
            raise ValueError("At least one of id or unicode is required")
        elif id and unicode:
            raise ValueError("Can only accept one of id or unicode, not both")

        self._isCustom = bool(id)
        self._isUnicode = bool(unicode)
        self.id = id
        self.unicode = unicode


    @classmethod
    def fromPartial(cls, e: PartialEmoji) -> BasedEmoji:
        """Construct a new BasedEmoji object from a given discord.PartialEmoji.

        :return: A BasedEmoji representing e
        :rtype: BasedEmoji
        """
        if e.id is None:
            return BasedEmoji(unicode=e.name)
        else:
            return BasedEmoji(id=e.id)


    @classmethod
    def fromReaction(cls, e: Union[Emoji, PartialEmoji, str], raiseOnInvalid: bool = False) -> BasedEmoji:
        """Construct a new BasedEmoji object from a given discord.PartialEmoji, discord.Emoji, or string.

        :param e: The reaction emoji to convert to BasedEmoji
        :type e: Union[Emoji, PartialEmoji, str]
        :param bool raiseOnInvalid: If e is an `Emoji`, raise an exception if the emoji is not available for use by the bot. Otherwise, the resulting emoji's sendable will be BasedEmoji.UNKNOWN (default False)
        :return: A BasedEmoji representing e
        :rtype: BasedEmoji
        """
        if isinstance(e, str):
            if strIsUnicodeEmoji(e):
                return BasedEmoji(unicode=e)
            elif strIsCustomEmoji(e):
                return BasedEmoji.fromStr(e)
            else:
                # This should never happen
                raise exceptions.UnrecognisedEmojiFormat("Given a string that does not match any emoji format: " + e, e)
            
        if isinstance(e, PartialEmoji):
            return BasedEmoji.fromPartial(e)
        
        if not e.available and raiseOnInvalid:
            raise exceptions.UnrecognisedCustomEmoji(f"Unrecognised custom emoji ID in BasedEmoji constructor: {e.id}", e.id)

        return BasedEmoji(id=e.id)


    @classmethod
    def fromStr(cls, s: str, raiseOnInvalid: bool = False) -> BasedEmoji:
        """Construct a BasedEmoji object from a string containing either a unicode emoji or a discord custom emoji.
        
        s may also be a BasedEmoji (returns s), a dictionary-serialized BasedEmoji (returns BasedEmoji.deserialize(s)), or
        only an ID of a discord custom emoji (may be either str or int)

        :param str s: A string containing only one of: A unicode emoji, a discord custom emoji, or
                        the ID of a discord custom emoji.
        :param bool raiseOnInvalid: When true, an exception will be raised if an invalid emoji is requested (Default False)
        :raise TypeError: When given something other than str, dict or BasedEmoji
        :raise exceptions.UnrecognisedEmojiFormat: When raiseOnInvalid = True and a string is given that does not match known emoji formats.
        :return: A BasedEmoji representing the given string emoji
        :rtype: BasedEmoji
        """
        if strIsUnicodeEmoji(s):
            return BasedEmoji(unicode=s)
        
        if strIsCustomEmoji(s):
            return BasedEmoji(id=customEmojiIdFromString(s))
        
        if stringUtil.isInt(s):
            return BasedEmoji(id=int(s))
        
        if raiseOnInvalid:
            raise exceptions.UnrecognisedEmojiFormat(f"Does not match known emoji string formats: {s}", s)
        
        return BasedEmoji.UNKNOWN

#endregion constructors
#region properties
    
    @property
    def isCustom(self) -> bool:
        return self._isCustom
    

    @property
    def isUnicode(self) -> bool:
        return self._isUnicode
    

    @property
    def isEmpty(self) -> bool:
        return not self.isCustom and not self.isUnicode
    

    @property
    def sendable(self) -> str:
        """A string representation of the emoji which can be sent to discord.

        :return: A discord-compliant string representation of the emoji
        :rtype: str
        """
        if isUnicode(self):
            return self.unicode
        if isCustom(self):
            if not self.verifyCustom(raiseOnUnknown=False):
                return cfg.defaultEmojis.unrecognisedEmoji.sendable
            return f"<:_:{self.id}>"
        # Must be empty emoji
        return ""
    
#endregion properties
#region operators

    def __repr__(self) -> str:
        """Get a string uniquely identifying this object, specifying what type of emoji it represents and the emoji itself.

        :return: A string identifying this object.
        :rtype: str
        """
        if isEmpty(self):
            return "<BasedEmoji-EMPTY:>"
        return f"<BasedEmoji-{'custom' if isCustom(self) else 'unicode'}:{self.id if isCustom(self) else self.unicode}>"


    def __hash__(self) -> int:
        """Calculate a hash of this emoji, based on its repr string.
        Two BasedEmoji objects representing the same emoji will have the same repr and hash.

        :return: A hash of this emoji
        :rtype: int
        """
        return hash(repr(self))


    def __eq__(self, other) -> bool:
        """Decide if this BasedEmoji is equal to another.
        Two BasedEmojis are equal if they represent the same emoji (i.e ID/unicode) of the same type (custom/unicode)

        :param BasedEmoji other: the emoji to compare this one to
        :return: True of this emoji is semantically equal to the given emoji, False otherwise
        :rtype: bool
        """
        return isinstance(other, BasedEmoji) and self.sendable == other.sendable


    def __str__(self) -> str:
        """Get the object's 'sendable' string.

        :return: A string sendable to discord that will be translated into an emoji by the discord client.
        :rtype: str
        """
        return self.sendable
    

    def __add__(self, o: T) -> Union[T, str]:
        """Add the sendable of this emoji to a string or other emoji

        :param o: The object to concatenate this emoji's sendable with
        :type o: Union[IBasedEmoji, str]
        :raises TypeError: If `o` is neither `IBasedEmoji` nor `str`
        :return: `self.sendable + o` if `o` is `str`, otherwise `self.sendable + o.sendable`
        :rtype: Union[T, str]
        """
        if isinstance(o, str):
            return self.sendable + o
        elif isinstance(o, BasedEmoji):
            return self.sendable + o.sendable
        raise TypeError(f"Cannot add {type(self).__name__} to {type(o).__name__}")


    def __radd__(self, o: T) -> Union[T, str]:
        """Add the sendable of this emoji to a string or other emoji

        :param o: The object to concatenate this emoji's sendable with
        :type o: Union[IBasedEmoji, str]
        :raises TypeError: If `o` is neither `IBasedEmoji` nor `str`
        :return: `o + self.sendable` if `o` is `str`, otherwise `o.sendable + self.sendable`
        :rtype: Union[T, str]
        """
        if isinstance(o, str):
            return o + self.sendable
        elif isinstance(o, BasedEmoji):
            return o.sendable + self.sendable
        raise TypeError(f"Cannot add {type(o).__name__} to {type(self).__name__}")


    def __iadd__(self, o):
        """Invalid operation. Cannot extend the contents of a BasedEmoji.
        """
        raise ValueError(f"Cannot extend the contents of a {type(self).__name__}")
    
#endregion operators

    def verifyCustom(self, raiseOnUnknown: bool = False) -> bool:
        """Make sure that this emoji can be used by the bot.

        :param raiseOnUnknown: Whether to raise an exception if the emoji is not usable, defaults to False
        :type raiseOnUnknown: bool, optional
        :raises exceptions.UnrecognisedCustomEmoji: If `raiseOnUnknown` is `True`, and this emoji is a custom emoji that is not accessible to the bot
        :return: `True` if this emoji can be used by the bot, `False` otherwise
        :rtype: bool
        """
        if isCustom(self) and not botState.client.get_emoji(self.id):
            if raiseOnUnknown:
                raise exceptions.UnrecognisedCustomEmoji(f"Unrecognised custom emoji ID in BasedEmoji constructor: {self.id}", self.id)
            return False
        return True


    async def serialize(self, **kwargs) -> SerializedBasedEmoji:
        """Serialize this emoji to dictionary format for saving to file.

        :return: A dictionary containing all information needed to reconstruct this emoji.
        :rtype: dict
        """
        if isEmpty(self):
            return {"empty": True}
        if isUnicode(self):
            return {"unicode": cast(str, self.unicode)}
        return {"id": cast(int, self.id)}
    

    @classmethod
    async def deserialize(cls, emojiDict: SerializedBasedEmoji, raiseOnInvalid: bool = False, **kwargs: Any) -> BasedEmoji:
        """Construct a BasedEmoji object from its dictionary representation.
        If both an ID and a unicode representation are provided, the emoji ID will be used.

        :param dict emojiDict: A dictionary containing either an ID (for custom emojis) or
                                a unicode emoji string (for unicode emojis)
        :param bool raiseOnInvalid: When true, an exception will be raised if an invalid serialized BasedEmoji is provided. Otherwise, BasedEmoji.UNKNOWN is returned (Default False)
        :raise ValueError: When raiseOnInvalid=True is given, and an invalid serialized BasedEmoji is provided
        :return: A new BasedEmoji object as described in emojiDict
        :rtype: BasedEmoji
        """
        id = emojiDict.get("id", None)

        if id and id > 0:
            return BasedEmoji(id=id)
        
        unicode = emojiDict.get("unicode", None)
        if unicode:
            return BasedEmoji(unicode=unicode)
        
        if emojiDict.get("empty", False):
            return BasedEmoji.EMPTY
        
        if raiseOnInvalid:
            raise ValueError("Invalid serialized BasedEmoji. Dictionary does not describe a custom, unicode or empty emoji")
        
        return BasedEmoji.UNKNOWN


class _CustomBasedEmoji(IBasedEmoji, Protocol):
    id: int
    unicode: None


class _UnicodeBasedEmoji(IBasedEmoji, Protocol):
    unicode: str
    id: None


class _EmptyBasedEmoji(IBasedEmoji, Protocol):
    unicode: None
    id: None


def isCustom(e: IBasedEmoji) -> TypeGuard[_CustomBasedEmoji]:
    return e.isCustom


def isUnicode(e: IBasedEmoji) -> TypeGuard[_UnicodeBasedEmoji]:
    return e.isUnicode


def isEmpty(e: IBasedEmoji) -> TypeGuard[_EmptyBasedEmoji]:
    return e.isEmpty


# 'static' object representing an empty/lack of emoji
BasedEmoji.EMPTY = BasedEmoji(unicode=" ")
BasedEmoji.EMPTY.unicode = ""

def randomEmoji() -> BasedEmoji:
    """Create a random unicode emoji. Can be anything.

    :return: A random unicode emoji
    :rtype: BasedEmoji
    """
    return BasedEmoji(unicode=random.choice(list(emoji.EMOJI_DATA)))
