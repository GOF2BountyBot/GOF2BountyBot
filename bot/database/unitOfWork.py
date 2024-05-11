from typing import Callable, Dict, Optional, Type, TypeVar, cast
from types import TracebackType

from contextlib import AbstractAsyncContextManager

from sqlalchemy.ext.asyncio import AsyncSession

from ..baseClasses.dbSnowflake import DbSnowflake
from ..repositories.snowflakeRepository import SnowflakeRepository

TModel = TypeVar("TModel", bound=DbSnowflake)

class UnitOfWork(AbstractAsyncContextManager[None]):
    def __init__(self, session: AsyncSession, moidRepositoryFactory: Callable[[Type[TModel]], SnowflakeRepository[TModel]]) -> None:
        self.session = session
        self.repositories: Dict[Type[DbSnowflake], SnowflakeRepository[DbSnowflake]] = {}
        self.moidRepositoryFactory = moidRepositoryFactory


    def repository(self, T: Type[TModel]) -> SnowflakeRepository[TModel]:
        repo = cast(Optional[SnowflakeRepository[TModel]], self.repositories.get(T, None))
        if repo is None:
            repo = cast(SnowflakeRepository[TModel], self.moidRepositoryFactory(T)) # type: ignore[reportArgumentType]
            self.repositories[T] = repo
        return repo

    async def __aenter__(self):
        return None
    

    async def __aexit__(self, __exc_type: Optional[Type[BaseException]], __exc_value: Optional[BaseException], __traceback: Optional[TracebackType]) -> Optional[bool]:
        return None
