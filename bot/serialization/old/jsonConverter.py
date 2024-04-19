from typing import Any, Callable, Dict, Optional, Type, TypeVar, TypedDict, Protocol, overload, Generic

from ..baseClasses.serializable import TDeserialized, SerializedSchema

TDeserialized = TypeVar("TDeserialized", bound=object)

class JsonConverterProtocol(Protocol, Generic[TDeserialized, SerializedSchema]):
    async def serialize(self, o: TDeserialized, **kwargs: Any) -> SerializedSchema: ...

    async def deserialize(self, data: SerializedSchema, **kwargs: Any) -> TDeserialized: ...


class JsonConverterParameterlessConstructorProtocol(JsonConverterProtocol[TDeserialized, TypedDict], Protocol):
    def __init__(self) -> None: ...


_jsonConverters: Dict[Type[Any], JsonConverterProtocol[Any, TypedDict]] = {}

def setConverter(t: Type[TDeserialized], converter: JsonConverterProtocol[TDeserialized, TypedDict]):
    _jsonConverters[t] = converter # type: ignore[reportArgumentType]


def getConverter(t: Type[TDeserialized]) -> Optional[JsonConverterProtocol[TDeserialized, TypedDict]]:
    return _jsonConverters.get(t, None) # type: ignore[reportReturnType]


@overload
def addJsonConverter(t: Type[TDeserialized], handler: JsonConverterProtocol[TDeserialized, TypedDict], /) -> None:
    """Register a json converter instance for a given type.

    ```py
    class SerializedInt(TypedDict):
        ...

    class IntJsonConverter:
        async def serialize(self, o: int, **kwargs: Any) -> SerializedInt:
            ...
        
        async def deserialize(self, data: SerializedInt, **kwargs: Any) -> int:
            ...

    addJsonConverter(int, IntJsonConverter())
    ```

    :param t: The deserialized type
    :type t: Type[Any]
    :param handler: The json converter instance
    :type handler: JsonConverterProtocol[t, TypedDict]
    """

@overload
def addJsonConverter(t: Type[TDeserialized], /) -> Callable[[Type[JsonConverterParameterlessConstructorProtocol[TDeserialized]]], Type[JsonConverterParameterlessConstructorProtocol[TDeserialized]]]:
    """Class decorator, to register a json converter class for a given type.

    ```py
    class SerializedInt(TypedDict):
        ...

    @addJsonConverter(int)
    class IntJsonConverter:
        async def serialize(self, o: int, **kwargs: Any) -> SerializedInt:
            ...
        
        async def deserialize(self, data: SerializedInt, **kwargs: Any) -> int:
            ...
    ```

    :param t: The deserialized type
    :type t: Type[Any]
    """

def addJsonConverter(t: Type[TDeserialized], handlerInstance: Optional[JsonConverterProtocol[TDeserialized, TypedDict]] = None, /) -> Optional[Callable[[Type[JsonConverterParameterlessConstructorProtocol[TDeserialized]]], Type[JsonConverterParameterlessConstructorProtocol[TDeserialized]]]]:
    """Sadly the class decorator override of this method hides the type of the decorated class, because higher-kinded types are not supported in pyright.
    The wrapper function should really be generic, so that exactly the passed type is returned.

    The choice was either to type the wrapper as:
    - generic in the converter class, but lose the converter class's generic type parameters
    - non-generic, hiding the converter class

    JsonConverters are very unlikely to be called directly, so losing their type information probably won't be that impactful.
    I've therefore decided that keeping the static type validation of a converter actually deserializing the type
    it claims to is more important. If higher-kinded types are added, then changing this would be great.
    """
    def wrapper(handler: Type[JsonConverterParameterlessConstructorProtocol[TDeserialized]]):
        setConverter(t, handler())
        return handler
    
    if handlerInstance is None:
        return wrapper
    
    setConverter(t, handlerInstance)
    return None
