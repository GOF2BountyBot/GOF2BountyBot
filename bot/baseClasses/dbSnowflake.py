from typing import Protocol

from sqlalchemy.orm import Mapped

from ..lib.sql import DeclarativeBaseProtocol

class DbSnowflake(DeclarativeBaseProtocol, Protocol):
    """A sqlalchemy.orm.DeclarativeBase that has an integer `id` column.
    """
    id: Mapped[int]
