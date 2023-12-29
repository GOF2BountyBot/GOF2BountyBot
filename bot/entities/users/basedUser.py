from __future__ import annotations

from typing import List, MutableSet, Optional
from datetime import datetime

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Column, Table, ForeignKey, Integer
from sqlalchemy.ext.hybrid import hybrid_property

from ...baseClasses.serializable import SerializesToSchema
from .basedUser_json import SerializedBasedUser
from ...lib.sql import AbcSqlTableMeta
from ...lib.gameMaths import calculateUserBountyHuntingLevel
from ...database.tables import TableNames
from ..userProfile.medal import Medal
from ..inventories.userHangar import UserHangar
from ..duels.duelRequest import DuelRequest
from ..items.ship.shipInstance import ShipInstance, AnyShipInstance


class Base(DeclarativeBase):
    pass


UserHasMedal = Table(
    TableNames.UserHasMedal.value,
    Base.metadata,
    Column("userId", Integer, ForeignKey(f"{TableNames.User.value}.id"), primary_key=True),
    Column("medalId", Integer, ForeignKey(f"{TableNames.Medal.value}.id"), primary_key=True),
)


class BasedUser(Base, SerializesToSchema[SerializedBasedUser], metaclass=AbcSqlTableMeta):
    """A user of the bot. There is currently no guarantee that user still shares any guilds with the bot,
    though this is planned to change in the future.

    :var id: The user's unique ID. The same as their unique discord ID.
    :vartype id: int
    """
    __tablename__ = TableNames.User.value
    id: Mapped[int] = mapped_column(primary_key=True)
    credits: Mapped[int]
    lifetimeBountyCreditsWon: Mapped[int]
    bountyCooldownEnd: Mapped[datetime]
    systemsChecked: Mapped[int]
    bountyWins: Mapped[int]
    duelWins: Mapped[int]
    duelLosses: Mapped[int]
    duelCreditsWins: Mapped[int]
    duelCreditsLosses: Mapped[int]
    bountyHuntingXP: Mapped[int]
    homeGuildId: Mapped[Optional[int]]
    guildTransferCooldownEnd: Mapped[datetime]
    prestiges: Mapped[int]
    prestigeTokens: Mapped[int]
    stateUserAlerts: Mapped[int]
    classicModeEnabled: Mapped[bool]
    bountyHuntingXpSurplus: Mapped[int]
    kaamo: Mapped[KaamoShop] = relationship(back_populates="user")
    loma: Mapped[LomaShop] = relationship(back_populates="user")
    hangar: Mapped[UserHangar] = relationship(back_populates="user")
    activeShip: Mapped[AnyShipInstance] = relationship()
    medals: Mapped[MutableSet[Medal]] = relationship(secondary=UserHasMedal)
    sentDuelRequests: Mapped[List[DuelRequest]] = relationship(back_populates="sourceUser")
    receivedDuelRequests: Mapped[List[DuelRequest]] = relationship(back_populates="targetUser")

    def __init__(self,
                id: int,
                activeShip: ShipInstance,
                **kw
    ):
        super().__init__(**kw)

        self.id = id
        self.activeShip = activeShip


    @hybrid_property
    def bountyHuntingLevel(self):
        return 1 if self.classicModeEnabled else calculateUserBountyHuntingLevel(self.bountyHuntingXP)


    @classmethod
    def defaultUser(cls, id: int):
        return BasedUser(id)


    def __str__(self) -> str:
        """Get a short string summary of this BasedUser. Currently only contains the user ID and home guild ID.

        :return: A string summar of the user, containing the user ID and home guild ID.
        :rtype: str
        """
        return f"<{type(self).__name__} #" + str(self.id) + ">"
