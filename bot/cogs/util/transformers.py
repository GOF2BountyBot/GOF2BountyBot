from enum import Enum, EnumMeta
from typing import Protocol
from ...baseClasses.basedEnum import BasedEnum

class Equatable(Protocol):
    def __eq__(self, __o) -> bool: ...


# Workaround so that BoolTransformerBase is not validated by the BoolEnumMeta constructor
_first = [None]

class BoolEnumMeta(EnumMeta):
    def __new__(cls: type, clsName, bases, classdict, trueVal: Equatable = True, **kwds):
        o: "BoolTransformerBase" = super().__new__(cls, clsName, bases, classdict, **kwds)
        if _first:
            _first.clear()
        elif trueVal not in classdict._last_values:
            raise ValueError(f"trueVal {trueVal} is not a member value of enum {clsName}")
        o.trueVal = trueVal
        return o


class BoolTransformerBase(Enum, metaclass=BoolEnumMeta):
    """Base class for boolean transformers.
    ```py
    >>> class MyBool(BoolTransformerBase, trueVal="world"):
    ...    hello = "world"
    ...    foo = "bar"
    ...
    >>> x = MyBool.foo
    >>> bool(x)
    False

    :param trueVal: The Enum value which represents True. Must be the value of a member in your enum (Defaults to True)
    :type trueVal: Equatable
    """
    trueVal: Equatable

    def __bool__(self):
        return self.value == self.trueVal


class BoolEnableDisable(BoolTransformerBase, trueVal="Enable"):
    Enable = "Enable"
    Disable = "Disable"


class BoolYesNo(BoolTransformerBase, trueVal="Yes"):
    Yes = "Yes"
    No = "No"


class BoolTrueFalse(BoolTransformerBase, trueVal="True"):
    # lower cased here to avoid clashing with the reserved words
    true = "True"
    false = "False"


class PlayOrAnnounceChannel(BasedEnum):
    bountyPlay = "play"
    announcements = "announce"

