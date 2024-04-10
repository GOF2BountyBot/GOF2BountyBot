from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from .unitOfWork import UnitOfWork


class UnitOfWorkFactory:
    def __init__(self, sessionMaker: async_sessionmaker[AsyncSession]) -> None:
        self.sessionMaker = sessionMaker


    def begin(self):
        session = self.sessionMaker()
        return UnitOfWork(session)
