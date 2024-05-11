from typing import Any, Callable, Optional, Tuple, Type, TypeVar, Union

from abc import ABCMeta
from contextlib import AbstractAsyncContextManager

from sqlalchemy.orm.decl_api import DeclarativeAttributeIntercept
from sqlalchemy.orm import object_session
from sqlalchemy.orm.exc import UnmappedInstanceError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import Select, func, select
# Ignoring because
from sqlalchemy.sql._typing import _ColumnsClauseArgument, _TypedColumnClauseArgument, _ColumnExpressionArgument # type: ignore[reportPrivateUsage]

from ..baseClasses.embedFillable import _EmbedFillableMeta # type: ignore[reportPrivateUsage]
from ..baseClasses.declarativeBaseProtocol import DeclarativeBaseProtocol
from ..serialization.serializable import _SerializableSqlMeta # type: ignore[reportPrivateUsage]

TRecord = TypeVar("TRecord", bound=DeclarativeBaseProtocol)
TColumn = TypeVar("TColumn", bound=Any)
SqlColumnExpression = _ColumnsClauseArgument[TColumn]
SqlTableExpression = _TypedColumnClauseArgument[TRecord]
SqlFilterExpression = _ColumnExpressionArgument[bool]

class AbcSqlTableMeta(ABCMeta, DeclarativeAttributeIntercept):
    """Metaclass intersecting the sqlalchemy declarative base and abstract base class metaclasses.
    """

class EmbedFillableSqlTableMeta(_EmbedFillableMeta, DeclarativeAttributeIntercept):
    """Metaclass intersecting the sqlalchemy declarative base and EmbedFillable metaclasses.
    """


class EmbedFillableSerializableSqlTableMeta(_EmbedFillableMeta, _SerializableSqlMeta):
    """Metaclass intersecting the BASED serializable sqlalchemy declarative base and EmbedFillable metaclasses.
    """


def getSession(instance: object) -> AsyncSession:
    """Get the database session in which `instance` was created.

    :param instance: The entity whose session to get
    :type instance: object
    :raises UnmappedInstanceError: If `instance` does not belong to a database session
    :return: The database session in which `instance` was created
    :rtype: AsyncSession
    """
    session = object_session(instance)
    if not isinstance(session, AsyncSession):
        raise UnmappedInstanceError(instance, f"This {type(instance).__name__} instance is not linked to a database session.")
    return session


def isMappedInstance(instance: object) -> bool:
    """Decide whether this instance belongs to a database session.

    :param instance: The object to check for session membership
    :type instance: object
    :return: True if `instance` has a database session, False otherwise
    :rtype: bool
    """
    return isinstance(object_session(instance), AsyncSession)


def count(table: Type[DeclarativeBaseProtocol]) -> Select[Tuple[int]]:
    """Count documents. Can be extended with the usual `where()` etc.

    ```py
    result: Optional[int] = await session.scalar(count(MyTable).where(MyTable.someField == someValue))
    ```

    sources:
    https://stackoverflow.com/a/65775282
    https://gist.github.com/hest/8798884

    :param table: The table in which to query
    :type table: Type[DeclarativeBase]
    :return: A selectable that retrieves a count
    :rtype: Select[Tuple[int]]
    """
    return select(table).order_by(None).with_only_columns(func.count())


def randomRows(table: Type[TRecord]) -> Select[Tuple[TRecord]]:
    """Get a random sequence of rows. Can be extended with the usual `where()` etc.
    
    ```py
    query = randomRows(MyTable).limit(1).where(MyTable.someField == someValue)
    result = await session.execute(query)
    ```

    This may not be the most efficient implementation.
    source:
    https://stackoverflow.com/questions/60805/getting-random-row-through-sqlalchemy

    :param table: The table in which to query
    :type table: Type[DeclarativeBase]
    :return: A selectable that retrieves a count
    :rtype: Select[Tuple[int]]
    """
    return select(table).order_by(func.random())


SessionFactory = Union[async_sessionmaker[AsyncSession], Callable[[], AsyncSession]]


class SessionSharer(AbstractAsyncContextManager["SessionSharer"]):
    """Create a new session and `with` it if one is not given.
    Always calls `.commit` on exit, on the active session.
    ```py
    session = sessionMaker()
    async with SessionSharer(session, sessionMaker) as s:
        ...
    ```
    This does nothing except call `session.commit` on exit.
    `session.__aenter__` and `session.__aexit__` are **not** called.
    
    --

    ```py
    async with SessionSharer(None, sessionMaker) as s:
        ...
    ```
    This creates a new session with sessionMaker, and calls `__aenter__`, `__aexit__`, and `commit` on the new session.
    """
    def __init__(self, session: Optional[AsyncSession], sessionMaker: SessionFactory) -> None:
        self._session = session
        self._sessionMaker = sessionMaker
        self._newSession = session is None


    async def __aenter__(self):
        if self._session is None:
            self._session = self._sessionMaker()
            await self._session.__aenter__()

        return self


    async def __aexit__(self, type_: Any, value: Any, traceback: Any) -> None:
        await self.session.commit()
        if self._newSession:
            await self.session.__aexit__(type_, value, traceback)


    @property
    def session(self):
        if self._session is None:
            raise RuntimeError("Cannot access session before __aenter__")
        return self._session
