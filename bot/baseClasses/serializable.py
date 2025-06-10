from abc import abstractmethod
from datetime import datetime
from typing import Generic, Iterable, Dict, Optional, Protocol, Type, TypeVar, Union, cast
from typing_extensions import TypedDict
import carica
from carica import ISerializable, SerializesToType, PrimativeType
from bot.baseClasses.defaultable import DefaultableMixin
from bot.baseClasses.simpleHash import SimpleHashMixin

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

# https://stackoverflow.com/a/78520322
class AnyTypedDict(TypedDict):
    pass

# TODO: Really SerializedSchema should be bound to JsonType, but this isn't supported:
# https://github.com/microsoft/pyright/issues/3870
SerializedSchema = TypeVar("SerializedSchema", bound=AnyTypedDict)
TSelf = TypeVar("TSelf", bound="Serializable")

class SerializesToSchema(Serializable, Generic[SerializedSchema]):
    """Helper to declare a Serializable, including DefaultableMixin and SimpleHashMixin, as serializing to/from a Json-compliant TypedDict schema.
    """
    @abstractmethod
    def serialize(self, **kwargs) -> SerializedSchema: return cast(SerializedSchema, {})

    @classmethod
    @abstractmethod
    def deserialize(cls: Type[TSelf], data: SerializedSchema, **kwargs) -> TSelf: raise NotImplementedError()

SerializesToJson = SerializesToType[JsonType]


TDeserialized = TypeVar("TDeserialized", bound=Serializable, covariant=True)
TSerialized = TypeVar("TSerialized", bound=Union[PrimativeType, AnyTypedDict], contravariant=True)

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
