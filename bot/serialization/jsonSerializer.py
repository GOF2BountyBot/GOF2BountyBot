from typing import Any, Optional, Type, TypeVar, TypedDict

from sqlalchemy.ext.asyncio import AsyncSession

from ..baseClasses.serializable import SerializesToSchema
from ..lib.sql import SessionSharer, SessionFactory

TSerialized = TypeVar("TSerialized", bound=TypedDict)
TDeserialized = TypeVar("TDeserialized", bound=SerializesToSchema[Any])

class JsonSerializer:
    def __init__(self, sessionFactory: SessionFactory) -> None:
        self.sessionFactory = sessionFactory


    async def serialize(self, o: SerializesToSchema[TSerialized], session: Optional[AsyncSession] = None, **kwargs: Any) -> TSerialized:
        if "session" in kwargs:
            return await o.serialize(**kwargs)
        
        async with SessionSharer(session, self.sessionFactory) as s:
            return await o.serialize(session = s.session, **kwargs)


    async def deserialize(self, T: Type[TDeserialized], data: TypedDict, session: Optional[AsyncSession] = None, **kwargs: Any) -> TDeserialized:
        if "session" in kwargs:
            return await T.deserialize(data, **kwargs)
        
        async with SessionSharer(session, self.sessionFactory) as s:
            return await T.deserialize(data, session = s.session, **kwargs)
