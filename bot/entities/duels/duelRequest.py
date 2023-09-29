from dataclasses import dataclass
from datetime import datetime
from typing import TypeVar
from carica.models.dataclasses import SerializableDataClass

from sqlalchemy.orm import DeclarativeBase, Mapped, relationship, mapped_column
from sqlalchemy import ForeignKey

from .duelRequest_json import SerializedDuelRequest
from ...lib.sql import AbcSqlTableMeta
from ...baseClasses.serializable import SerializesToSchema
from ...database.tables import TableNames
from ..users import basedUser


class Base(DeclarativeBase): pass

TSchema = TypeVar("TSchema", bound=SerializedDuelRequest)

@dataclass
class DuelRequest(Base, SerializableDataClass, SerializesToSchema[TSchema], metaclass=AbcSqlTableMeta):
    """A duel challenge for stakes credits, issued by sourceBasedUser to targetBasedUser in sourceBasedGuild,
    and expiring with duelTimeoutTask.

    :var int sourceUserId: The BasedUser that issued this challenge
    :var int targetUserId: The BasedUser that this challenge was targetted towards
    :var int stakes: The amount of credits to award the winner of the duel, and take from the loser
    :var datetime expiryTime: The datetime at which this duel request expires
    """
    __tablename__ = TableNames.DuelRequest.value

    stakes: Mapped[int]
    expiryTime: Mapped[datetime]
    sourceUserId: Mapped[int] = mapped_column(ForeignKey(f"{TableNames.User.value}.id"))
    targetUserId: Mapped[int] = mapped_column(ForeignKey(f"{TableNames.User.value}.id"))
    sourceUser: Mapped["basedUser.BasedUser"] = relationship(back_populates="duelRequests")
    targetUser: Mapped["basedUser.BasedUser"] = relationship(back_populates="receivedDuelRequests")
