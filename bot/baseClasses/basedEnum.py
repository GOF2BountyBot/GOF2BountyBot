import sys
from enum import Enum
from typing import Any, Optional, Type, TypeVar

TSelf = TypeVar("TSelf", bound="BasedEnum")

# Handle Python version compatibility
if sys.version_info >= (3, 11):
    try:
        from enum import EnumType
        _EnumMetaBase = EnumType
    except ImportError:
        from enum import EnumMeta
        _EnumMetaBase = EnumMeta
else:
    from enum import EnumMeta
    _EnumMetaBase = EnumMeta

class BasedEnumMeta(_EnumMetaBase):
    def __str__(self) -> str:
        return str(self.value)
    
    @classmethod
    def hasValue(cls, value: Any) -> bool:
        """Decide whether this enum has a member with the given value

        :param value: value to look up
        :type value: Any
        :return: `True` if at least one member with value `value`, `False` otherwise
        :rtype: bool
        """
        return any(i.value == value for i in cls)
    
    @classmethod
    def fromStr(cls: Type[TSelf], name: str) -> Optional[TSelf]:
        """Try to find a member of this enum with the given name, returning `None` if none exists.
        
        :param name: The name of the enum member to find
        :type name: str
        :return: The enum member if it exists, `None` otherwise
        :rtype: Optional[TSelf]
        """
        return cls[name] if name in cls else None
