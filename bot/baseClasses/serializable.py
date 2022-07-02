from abc import abstractmethod
from datetime import datetime
from typing import Generic, Iterable, Dict, Optional, Protocol, TypeVar, Union
from carica import ISerializable, SerializesToType, PrimativeType
from .defaultable import DefaultableMixin
from .simpleHash import SimpleHashMixin

# This currently reflects carica.PrimativeType, but I'm making my own in case Carica decides to allow more primatives.
# I'm also using Dict instead of Mapping to ensure that the data is mutable.
JsonPrimatives = Optional[Union[int, float, str, bool, datetime, Iterable["JsonPrimatives"], Dict[str, "JsonPrimatives"]]]
# Make sure it is a dict at its base.
JsonType = Dict[str, JsonPrimatives]


class Serializable(ISerializable, DefaultableMixin, SimpleHashMixin):
    """BountyBot DefaultableMixin for shorthanding deserializer implementations in most serializable classes,
    and SimpleHashMixin for using game objects as dict keys,
    so just include both by default.
    """
    @abstractmethod
    def serialize(self, **kwargs) -> JsonType:
        return {}


class SerializesToJson(SerializesToType[JsonType], Serializable):
    """Helper to declare a Serializable, including DefaultableMixin and SimpleHashMixin, as serializing to/from dict.
    """
    pass


TDeserialized = TypeVar("TDeserialized", bound=ISerializable, covariant=True)
TSerialized = TypeVar("TSerialized", bound=PrimativeType, contravariant=True)

class Factory(Protocol, Generic[TSerialized, TDeserialized]):
    """Any class that can be deserialized, but cannot be serialized.
    The typical use case for this type is to hint for 'factory' classes - classes whose
    job is to instance other classes.

    The `TSerialized` parameter describes the datatype that the deserializer accepts.
    The `TDeserialized` parameter describes the datatype that the deserializer produces.

    Examples:
    - A `Factory[str, SerializesToJson]` deserializes strings into json-serializable types
    - A `FromPrimativeFactory[SerializesToJson]` deserializes any primative type into a json-serializable type
    - A `FromJsonFactory[MyJsonSerializableType]` deserializes a json-compliant `dict` into `MyJsonSerializableType`
    """
    @abstractmethod
    @classmethod
    def deserialize(cls, data: TSerialized, **kwargs) -> TDeserialized: ...

FromPrimativeFactory = Factory[PrimativeType, TDeserialized]

TJsonDeserialized = TypeVar("TJsonDeserialized", bound=SerializesToJson)
FromJsonFactory = Factory[JsonType, TJsonDeserialized]
