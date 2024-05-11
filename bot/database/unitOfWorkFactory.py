from typing import Dict, Optional, Type, TypeVar, cast, Callable

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from .unitOfWork import UnitOfWork
from ..baseClasses.dbSnowflake import DbSnowflake
from ..repositories.snowflakeRepository import SnowflakeRepository
from ..lib.typingUtil import isOpenGeneric, genericParamValue


DEFAULT_MOID_REPOSITORIES: Dict[Type[DbSnowflake], Type[SnowflakeRepository[DbSnowflake]]] = {}

TRepositoryClass = TypeVar("TRepositoryClass", bound=Type[SnowflakeRepository[DbSnowflake]])

def defaultRepository(cls: TRepositoryClass) -> TRepositoryClass:
    """Class decorator. Mark a repository class as the one to use for its record type in DefaultUnitOfWorkFactory.

    :param cls: The repository class
    :type cls: TRepositoryClass
    :raises ValueError: If `cls` has open generic type parameters
    :raises ValueError: If the record type cannot be determined
    :return: `cls` unchanged
    :rtype: TRepositoryClass
    """
    if isOpenGeneric(cls):
        raise ValueError(f"Type {cls.__name__} cannot be used by UnitOfWork, as it has open generic type parameters")

    recordType: Type[DbSnowflake] = genericParamValue(SnowflakeRepository[DbSnowflake], DbSnowflake, cls) # type: ignore[reportCallIssue]

    if recordType is None:
        raise ValueError(f"Unable to determine the record type for repository {cls.__name__}")
    
    DEFAULT_MOID_REPOSITORIES[recordType] = cls

    return cls


TMoid = TypeVar("TMoid", bound=DbSnowflake)

def getDefaultMoidRepositoryType(T: Type[TMoid]) -> Optional[Type[SnowflakeRepository[TMoid]]]:
    return cast(Optional[Type[SnowflakeRepository[TMoid]]], DEFAULT_MOID_REPOSITORIES.get(T, None))


class UnitOfWorkFactory:
    """A simple factory for `UnitOfWork`
    """
    def __init__(self, sessionMaker: async_sessionmaker[AsyncSession], moidRepositoryFactory: Callable[[Type[TMoid]], SnowflakeRepository[TMoid]]) -> None:
        self.sessionMaker = sessionMaker
        self.moidRepositoryFactory = moidRepositoryFactory


    def begin(self):
        session = self.sessionMaker()
        return UnitOfWork(session, self.moidRepositoryFactory)
    

class DefaultUnitOfWorkFactory(UnitOfWorkFactory):
    """A factory for `UnitOfWork` which uses the default repositories configured using `defaultRepository`.
    Make sure that all of your repositories have been imported before using this factory.
    """
    def __init__(self, sessionMaker: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(sessionMaker, self.repositoryFactory)


    def repositoryFactory(self, T: Type[TMoid]) -> SnowflakeRepository[TMoid]:
        repoType = getDefaultMoidRepositoryType(T)
        if repoType is None:
            raise ValueError(f"No default repository is registered for type {T.__name__}")

        return repoType(T, self.sessionMaker())
    