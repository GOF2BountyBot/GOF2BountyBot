from typing import Dict, Optional, Type, TypeVar
from types import TracebackType

from contextlib import AbstractAsyncContextManager

from sqlalchemy.ext.asyncio import AsyncSession

from ..baseClasses.dbSnowflake import DbSnowflake
from ..repositories.snowflakeRepository import SnowflakeRepository

TModel = TypeVar("TModel", bound=DbSnowflake)

class UnitOfWork(AbstractAsyncContextManager[None]):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repositories: Dict[Type[DbSnowflake], SnowflakeRepository[DbSnowflake]] = {}


    def repository(self, T: Type[TModel]) -> SnowflakeRepository[TModel]:
        repo = self.repositories.get(T, None)
        if repo is None:
            repo = 


    async def __aenter__(self):
        return None
    

    async def __aexit__(self, __exc_type: Optional[Type[BaseException]], __exc_value: Optional[BaseException], __traceback: Optional[TracebackType]) -> Optional[bool]:
        return None
