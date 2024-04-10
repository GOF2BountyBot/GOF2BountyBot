from typing import Optional, Type
from types import TracebackType

from contextlib import AbstractAsyncContextManager

from sqlalchemy.ext.asyncio import AsyncSession

class UnitOfWork(AbstractAsyncContextManager[None]):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session


    async def __aenter__(self):
        return None
    

    async def __aexit__(self, __exc_type: Optional[Type[BaseException]], __exc_value: Optional[BaseException], __traceback: Optional[TracebackType]) -> Optional[bool]:
        return None
