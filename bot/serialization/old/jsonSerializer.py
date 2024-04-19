from typing import Any, Optional, Type, TypeVar, TypedDict

from ..baseClasses.serializable import SerializesToSchema, JsonType
from ..database.unitOfWorkFactory import UnitOfWorkFactory, UnitOfWork
from .jsonConverter import getConverter

TSerialized = TypeVar("TSerialized", bound=TypedDict)
TDeserialized = TypeVar("TDeserialized")

class JsonSerializer:
    def __init__(self, unitOfWorkFactory: UnitOfWorkFactory) -> None:
        self.unitOfWorkFactory = unitOfWorkFactory


    async def serialize(self, o: SerializesToSchema[TSerialized], unitOfWork: Optional[UnitOfWork] = None, **kwargs: Any) -> TSerialized:
        converter = getConverter(type(o))
        if converter is None:
            raise ValueError(f"No json converter is registered for type {type(o).__name__}")
        
        if unitOfWork is not None:
            return await o.serialize(unitOfWork=unitOfWork, **kwargs)
        
        async with self.unitOfWorkFactory.begin() as newUOW:
            return await o.serialize(unitOfWork=newUOW, **kwargs)


    async def deserialize(self, T: Type[TDeserialized], data: JsonType, unitOfWork: Optional[UnitOfWork] = None, **kwargs: Any) -> TDeserialized:
        converter = getConverter(T)
        if converter is None:
            raise ValueError(f"No json converter is registered for type {T.__name__}")
        
        if unitOfWork is not None:
            return await converter.deserialize(data, unitOfWork=unitOfWork, **kwargs)
        
        async with self.unitOfWorkFactory.begin() as newUOW:
            return await converter.deserialize(data, unitOfWork=newUOW, **kwargs)
