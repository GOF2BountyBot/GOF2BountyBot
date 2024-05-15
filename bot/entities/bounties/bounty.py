# Typing imports
from __future__ import annotations

from typing import Any, Collection, Dict, Optional, TypeVar, cast

from datetime import datetime
from enum import Enum

from sqlalchemy.orm import DeclarativeBase, Mapped, relationship, mapped_column, attribute_keyed_dict
from sqlalchemy import ForeignKey
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession

from . import criminal
from .bountyConfig import GeneratedBountyConfigBase
from ...baseClasses.serializable import SerializesToSchema
from ..items.ship.shipInstance import ShipInstance
from .bounty_json import SerializedBountyUnion, SerializedEscapedBounty
from .bountyRouteEntry import BountyRouteEntry
from ...database.tables import TableNames
from . import bountyDivision
from ...serialization.serializable import SqlSerializableMixin, JsonSchema


TSchema = TypeVar("TSchema", bound=SerializedBountyUnion)


class CheckResult(Enum):
    """Indicate the result of a check. Does not indicate the result of the following duel.
    
    0 => This system is not in the bounty route.
    1 => this system has already been checked.
    2 => The system was unchecked, but is not the answer.
    3 => answer found.
    """
    NOT_FOUND = 0
    ALREADY_CHECKED = 1
    INCORRECT = 2
    CORRECT = 3


class Base(AsyncAttrs, DeclarativeBase):
    pass


json = JsonSchema()
class Bounty(Base, SqlSerializableMixin):
    """A bounty listing for a criminal, to be hunted down by players.

    :var criminal: The criminal who is being hunted
    :vartype criminal: criminal
    :var issueTime: The time at which the bounty was created
    :vartype issueTime: datetime.datetime
    :var route: the names of systems that are in the route
    :vartype route: list[str]
    :var reward: the number of credits available to contributing players
    :vartype reward: int
    :var endTime: the time at which the bounty should automatically expire
    :vartype endTime: datetime.datetime
    :var faction: the faction to which this bounty belongs
    :vartype faction: str
    :var checked: A dictionary tracking which player checked each system. Keys are system names, values are user ids.
                    values for unchecked systems are -1.
    :vartype checked: dict[str, int]
    :var answer: The name of the system where the criminal is located
    :vartype answer: str
    :var activeShip: The ship equipped by this criminal
    :vartype activeShip: shipItem
    :var hasShip: Whether this criminal has a ship equipped or not
    :vartype hasShip: bool
    :var techLevel: The current difficulty level of the bounty
    :vartype techLevel: int
    :var expiryTT: The timedtask responsible for expiring this bounty.
    :vartype expiryTT: TimedTask
    """
    __tablename__ = TableNames.Bounty.value
    _jsonSchema = json

    id: Mapped[int]
    divisionId: Mapped[int] = mapped_column(ForeignKey(f"{TableNames.BountyDivision}.id"))
    techLevel: Mapped[int] = mapped_column()
    isEscaped: Mapped[bool] = mapped_column()
    criminalId: Mapped[int] = mapped_column(ForeignKey(f"{TableNames.Criminal}.id"))
    shipId: Mapped[int] = mapped_column(ForeignKey(f"{TableNames.ShipInstance}.id"))
    isPlayer: Mapped[bool] = mapped_column()

    faction: Mapped[str] = mapped_column()
    json.field(faction)
    
    answerSystemId: Mapped[int] = mapped_column(ForeignKey(f"{TableNames.SolarSystem}.id"))
    reward: Mapped[int] = mapped_column()
    issueTime: Mapped[datetime] = mapped_column()
    endTime: Mapped[datetime] = mapped_column()
    rewardPerSys: Mapped[int] = mapped_column()
    respawnTime: Mapped[Optional[datetime]] = mapped_column()

    # This attribute is loaded eagerly, so no need for asyncAttrs
    route: Mapped[Dict[int, BountyRouteEntry]] = relationship(
        lazy="joined", collection_class=attribute_keyed_dict("systemId") # type: ignore[reportUnknownArgumentType]
    )

    @json.field()
    @property
    def _route_json(self):
        return [e.system.id for e in self.route.values()]

    _division: Mapped["bountyDivision.BountyDivision[Any]"] = relationship(back_populates="_allBounties")
    _criminal: Mapped["criminal.Criminal[Any]"] = relationship()
    _ship: Mapped["ShipInstance[Any]"] = relationship()

    @property
    async def division(self) -> "bountyDivision.BountyDivision[Any]":
        return await self.awaitable_attrs._division
    

    @property
    async def criminal(self) -> "criminal.Criminal[Any]":
        return await self.awaitable_attrs._criminal


    @property
    async def ship(self) -> "ShipInstance[Any]":
        return await self.awaitable_attrs._ship
    

    @property
    def orderedRoute(self) -> Collection[BountyRouteEntry]:
        return sorted(self.route.values(), key=lambda e: e.index)
    

    def __init__(self,
                 config: Optional[GeneratedBountyConfigBase] = None,
                 route: Optional[Dict[int, BountyRouteEntry]] = None,
                 division: Optional["bountyDivision.BountyDivision[Any]"] = None,
                 criminal: Optional["criminal.Criminal[Any]"] = None,
                 ship: Optional["ShipInstance[Any]"] = None,
                 **kwargs: Any):
        if config is not None:
            self.techLevel = config.techLevel
            self.criminalId = config.criminal.id
            self.shipId = config.activeShip.id
            self.isPlayer = config.isPlayer
            self.faction = config.faction
            self.answerSystemId = config.answer
            self.reward = config.reward
            self.issueTime = config.issueTime
            self.endTime = config.endTime
            self.rewardPerSys = config.rewardPerSys
            self.route = {s: BountyRouteEntry(index=i, bountyId=self.id, systemId=s, checkedByUserId=None)
                          for i, s in enumerate(config.route)}
            
        super().__init__(route=route, _division=division, _criminal=criminal, _ship=ship, **kwargs)


    def check(self, systemId: int, userID: int) -> CheckResult:
        """Check a system along the route.

        :param int systemId: The id of the system to check
        :param int userID: The id of the user checking the system
        :return: An enum representing the result of the check
        :rtype: int
        """
        if systemId not in self.route:
            return CheckResult.NOT_FOUND
        
        if self.systemChecked(systemId):
            return CheckResult.ALREADY_CHECKED

        self.route[systemId].checkedByUserId = userID
        return CheckResult.CORRECT if self.answerSystemId == systemId else CheckResult.INCORRECT


    def systemChecked(self, systemId: int) -> bool:
        """Decide whether or not a system has been checked.

        :param int system: The system id to inspect for checking
        :return: True if system has been checked yet, False otherwise
        :rtype: bool
        """
        return self.route[systemId].checkedByUserId != -1


    async def serialize(self, **kwargs: Any) -> TSchema:
        """Serialize this bounty to dictionary, to be saved to file.

        :return: A dictionary representation of this bounty.
        :rtype: dict
        """
        data = await super().serialize(**kwargs)
        
        data["faction"] = self.faction
        data["route"] = [e.system.id for e in self.route.values()]
        data["answer"] = self.answerSystemId
        data["checked"] = {k: v.checkedByUserId for k, v in self.route.items()}
        data["reward"] = self.reward
        data["issueTime"] = self.issueTime.timestamp()
        data["endTime"] = self.endTime.timestamp()
        data["isEscaped"] = self.isEscaped
        data["criminal"] = self.criminalId
        data["rewardPerSys"] = self.rewardPerSys
        data["techLevel"] = self.techLevel
        data["activeShip"] = await (await self.ship).serialize()
        
        if self.isEscaped and self.respawnTime is not None:
            # Casting here because we know the bounty is escaped
            data = cast(SerializedEscapedBounty, data)
            data["respawnTime"] = self.respawnTime.timestamp()
            data = cast(TSchema, data)

        return data

    
    @classmethod
    async def deserialize(cls, data: TSchema, session: Optional[AsyncSession] = None, **kwargs: Any) -> Bounty[TSchema]:
        """Factory function constructing a new bounty from a dictionary serialized description - the opposite of bounty.serialize

        :param dict bounty: Dictionary containing all information needed to construct the desired bounty
        :param bool dbReload: Give True if this bounty is being created during bot bootup, False otherwise.
                                This currently toggles whether the passed bounty is checked for existence or not.
                                (Default False)
        """
        if session is None:
            raise ValueError(f"Cannot deserialize {cls.__name__} without database session access")
        
        activeShip = await ShipInstance.deserialize(data["activeShip"])

        crim = await criminal.AnyCriminal.deserialize()

        if data["criminal"]["isPlayer"]
        newCfg = BountyConfig(faction=data["faction"], route=data["route"],
                              answer=data["answer"], checked=data["checked"], reward=data["reward"],
                              issueTime=data["issueTime"], endTime=data["endTime"],
                              rewardPerSys=data["rewardPerSys"], activeShip=activeShip,
                              techLevel=techLevel)
                                            
        newBounty: Bounty[SerializedBountyUnion] = \
            Bounty(dbReload=dbReload, config=newCfg, division=owningDB.divisionForLevel(techLevel),
                    criminalObj=criminal.Criminal.deserialize(data["criminal"]))

        if data.get("isEscaped", False):
            # casting because we know the bounty is escaped
            data = cast(SerializedEscapedBounty, data)
            if "respawnTime" not in data:
                raise ValueError("Not given respawnTime for escaped criminal " + data["criminal"]["name"])

            respawnTT = TimedTask(issueTime=utcfromtimestamp(data["issueTime"]),
                                    expiryTime=utcfromtimestamp(data["respawnTime"]), 
                                    expiryFunction=newBounty._respawn,
                                    rescheduleOnExpiryFuncFailure=True)
            newBounty.escape(respawnTT=respawnTT, dbReload=dbReload)

        return newBounty

AnyBounty = Bounty[SerializedBountyUnion]
