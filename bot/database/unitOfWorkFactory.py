from sqlalchemy.ext.asyncio import async_sessionmaker

from .unitOfWork import UnitOfWork


class UnitOfWorkFactory:
    def __init__(self, sessionMaker: async_sessionmaker) -> None:
        self.sessionMaker = sessionMaker


    def begin(self):
        session = self.sessionMaker()
        return UnitOfWork(session)
