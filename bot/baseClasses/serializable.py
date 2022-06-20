from datetime import datetime
from typing import Iterable, Mapping, Optional, Union
from carica import ISerializable, SerializesToType
from .defaultable import DefaultableMixin
from .simpleHash import SimpleHashMixin

# This currently reflects carica.PrimativeType, but I'm making my own in case Carica decides to allow more primatives.
JsonPrimatives = Optional[Union[int, float, str, bool, datetime, Iterable["JsonPrimatives"], Mapping[str, "JsonPrimatives"]]]
# Make sure it is a dict at its base.
JsonType = Mapping[str, JsonPrimatives]


class Serializable(ISerializable, DefaultableMixin, SimpleHashMixin):
    """BountyBot DefaultableMixin for shorthanding deserializer implementations in most serializable classes,
    and SimpleHashMixin for using game objects as dict keys,
    so just include both by default.
    """
    pass


class SerializesToJson(SerializesToType[JsonType], Serializable):
    """Helper to declare a Serializable, including DefaultableMixin and SimpleHashMixin, as serializing to/from dict.
    """
    pass
