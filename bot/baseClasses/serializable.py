from abc import abstractmethod
from datetime import datetime
from typing import Generic, Iterable, Dict, Optional, Protocol, Type, TypeVar, TypedDict, Union
from collections.abc import Mapping
import carica
from carica import ISerializable, SerializesToType, PrimativeType
from .defaultable import DefaultableMixin
from .simpleHash import SimpleHashMixin

# This currently reflects carica.PrimativeType, but I'm making my own in case Carica decides to allow more primatives.
# I'm also using Dict instead of Mapping to ensure that the data is mutable.
JsonPrimatives = Optional[Union[int, float, str, bool, datetime, Iterable["JsonPrimatives"], Dict[str, "JsonPrimatives"]]]
# Make sure it is a dict at its base.
JsonType = Dict[str, JsonPrimatives]

class Serializable(ISerializable, DefaultableMixin, SimpleHashMixin):
    """BountyBot uses DefaultableMixin for shorthanding deserializer implementations in most serializable classes,
    and SimpleHashMixin for using game objects as dict keys,
    so just include both by default.
    """
    @abstractmethod
    def serialize(self, **kwargs) -> JsonPrimatives:
        return {}


# TODO: Really SerializedSchema should be bound to JsonType, but this isn't supported:
# https://github.com/microsoft/pyright/issues/3870
SerializedSchema = TypeVar("SerializedSchema", bound=TypedDict)
TSelf = TypeVar("TSelf", bound="Serializable")

class SerializesToSchema(SerializesToType[JsonType], Serializable, Generic[SerializedSchema]):
    """Helper to declare a Serializable, including DefaultableMixin and SimpleHashMixin, as serializing to/from a Json-compliant TypedDict schema.
    """
    @abstractmethod
    def serialize(self, **kwargs) -> SerializedSchema: return {}

    @abstractmethod
    @classmethod
    def deserialize(cls: Type[TSelf], data: SerializedSchema, **kwargs) -> TSelf: raise NotImplementedError()

SerializesToJson = SerializesToType[JsonType]


TDeserialized = TypeVar("TDeserialized", bound=carica.SerializableType, covariant=True)
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
    @classmethod
    @abstractmethod
    def deserialize(cls, data: TSerialized, **kwargs) -> TDeserialized: ...

FromPrimativeFactory = Factory[PrimativeType, TDeserialized]

TJsonDeserialized = TypeVar("TJsonDeserialized", bound=SerializesToJson)
FromJsonFactory = Factory[JsonType, TJsonDeserialized]
