from enum import Enum, EnumMeta
from typing import Any

class _BasedEnumMeta(EnumMeta):
    """This metaclass should only be applied to enums, or it will break.
    """
    @classmethod
    def hasValue(cls, value: Any) -> bool:
        """Decide whether this enum has a member with the given value

        :param value: value to look up
        :type value: Any
        :return: `True` if at least one member with value `value`, `False` otherwise
        :rtype: bool
        """
        # Ignoring a warning: Enums do have __iter__
        return any(i.value == value for i in cls) # type: ignore[reportGeneralTypeIssues]


class BasedEnum(Enum, metaclass=_BasedEnumMeta):
    pass
