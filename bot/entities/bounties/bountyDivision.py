from __future__ import annotations
from typing import Any, Collection, Dict, List, Optional, Tuple, cast, TypeVar, Protocol, runtime_checkable
from typing_extensions import TypeGuard

from datetime import datetime
from itertools import chain

from sqlalchemy.orm import Mapped, relationship, mapped_column, DeclarativeBase
from sqlalchemy import ForeignKey
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy.ext.asyncio import AsyncAttrs

from .bountyDivision_json import SerializedBountyDivision
from .bountyBoardChannel import BountyBoardChannel, AnyBountyBoardChannel, SerializedBountyBoardChannel
from ...cfg import cfg
from ...lib import gameMaths
from ...lib.timeUtil import MinMaxDict
from ...baseClasses.serializable import SerializesToSchema
from ...database.constants import BountyDivisionTier
from ...database.tables import TableNames
from ..guilds import basedGuild
from . import bounty
from .bounty_json import SerializedActiveBounty, SerializedEscapedBounty

BOUNTY_SPAWN_DELAY_RAND_RANGE: MinMaxDict = {
    "min": cfg.timeouts.newBountyDelayRandomMin,
    "max": cfg.timeouts.newBountyDelayRandomMax
}

def divisionNameLevels() -> Dict[str, Tuple[int, int]]:
    return {k: cfg.bountyDivisionLevels[i] for i, k in enumerate(cfg.bountyDivisionNames)}


TSchema = TypeVar("TSchema", bound=SerializedBountyDivision)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class BountyDivision(Base, SerializesToSchema[TSchema]):
    """A guild-level container of Bounties for a range of tech levels.
    The maximum capacity and spawning rates of bounties are based on the "temperature" of the division - an estimate for the
    level of player activity.

    :var temperature: A measure of the level of player activity in this division.
    :vartype temperature: float
    :var minLevel: The lowest level of bounties available in this division
    :varype minLevel: int
    :var maxLevel: The highest level of bounties available in this division
    :varype maxLevel: int
    :var bounties: A record of all currently active bounties, with tech levels as keys
    :vartype bounties: Dict[int, AliasableDict[Criminal, Bounty]]
    :var latestBounty: The most recent bounty to be added to this division. As of writing,
                        this is only used when scaling new bounty delays by the most recent length
    :vartype latestBounty: Union[Bounty, None]
    :var escapedBounties: A record of all currently escaped, inactive bounties, with tech levels as keys
    :vartype escapedBounties: Dict[int, AliasableDict[Criminal, Bounty]]
    :var isActive: True if there is any player activity in this division currently, False otherwise
    :vartype isActive: bool
    :var delayRandRange: A dictionary containing boundary timedeltas for use in random bounty delay generators
    :vartype delayRandRange: Dict[str, timedelta]
    :var bountyBoardChannel: A BountyBoardChannel object implementing this division's bounty board channel if it has one,
                                None otherwise.
    :vartype bountyBoardChannel: BountyBoardChannel
    :var alertRoleID: The ID of the role to ping when new bounties are spawned into this division. -1 if no role is set.
    :vartype alertRoleID: int
    :var newBountyTT: The timedtask responsible for spawning this division's bounties. If the division is full, this is None.
    :vartype newBountyTT: Union[None, TimedTask]
    """
    __tablename__ = TableNames.BountyDivision.value

    id: Mapped[int] = mapped_column(primary_key=True)
    tier: Mapped[BountyDivisionTier]
    temperature: Mapped[float] = mapped_column(default=cfg.minGuildActivity)
    lastSpawnedRouteLength: Mapped[Optional[int]]
    bountyBoardChannelId: Mapped[Optional[int]] = mapped_column(ForeignKey(f"{TableNames.BountyBoardChannel.value}.id"))
    spawnAlertRoleId: Mapped[Optional[int]]
    guildId: Mapped[int] = mapped_column(ForeignKey(f"{TableNames.Guild.value}.id"))
    nextBounty: Mapped[Optional[datetime]]
    
    _guild: Mapped["basedGuild.AnyBasedGuild"] = relationship(back_populates="_divisions")
    _bountyBoardChannel: Mapped[Optional[BountyBoardChannel[SerializedBountyBoardChannel]]] = relationship()
    _allBounties: Mapped["bounty.AnyBounty"] = relationship(back_populates="_division")

    @property
    async def guild(self) -> "basedGuild.AnyBasedGuild":
        return await self.awaitable_attrs._guild
    

    @property
    async def bountyBoardChannel(self) -> Optional[BountyBoardChannel[SerializedBountyBoardChannel]]:
        return await self.awaitable_attrs._bountyBoardChannel
    

    @property
    async def allBounties(self) -> List["bounty.AnyBounty"]:
        return await self.awaitable_attrs._allBounties
    

    def setBountyBoardChannel(self, value: Optional[BountyBoardChannel[Any]]):
        self._bountyBoardChannel = value
    

    @hybrid_property
    def name(self) -> str:
        return cfg.bountyDivisionNames[cast(int, self.tier.value) - 1]
    

    @hybrid_property
    def minLevel(self) -> int:
        return cfg.bountyDivisionLevels[cast(int, self.tier.value) - 1][0]
    

    @hybrid_property
    def levelRange(self) -> Collection[int]:
        return range(self.minLevel, self.maxLevel + 1)
    

    @hybrid_property
    def maxLevel(self) -> int:
        return cfg.bountyDivisionLevels[cast(int, self.tier.value) - 1][1]
    

    @hybrid_property
    def isActive(self) -> bool:
        return self.temperature != cfg.minGuildActivity


    @classmethod
    def nameForLevel(cls, tl: int) -> str:
        """Get the name of the division which players and bounties of the given techlevel belong to.

        :param int tl: The techlevel whose division name to find
        :return: The name for divisions responsible for bounties of the given level
        :rtype: str
        :raise KeyError: When no division is found for bounties of the given level
        """
        try:
            return next(k for i, k in enumerate(cfg.bountyDivisionNames) \
                        if cfg.bountyDivisionLevels[i][0] <= tl <= cfg.bountyDivisionLevels[i][1])
        except StopIteration:
            raise KeyError(f"No division found for bounties of TL {tl}")


    @hybrid_method
    def maxBounties(self) -> int:
        """Decide the maximum number of bounties that the division can currently contain, based on the level of
        player activity.

        :return: The maximum number of bounties the division can currently contain
        :rtype: int
        """
        return min(cfg.maxBountiesPerDivision, max(1, int(self.temperature)))


    def setTemp(self, newTemp: float):
        """Directly set the division's activity temperature to a given number.

        :param float newTemp: The new temperature
        """
        # truncate to 2 decimal places and apply lower bound
        self.temperature = max(cfg.minGuildActivity, round(newTemp, 2))


    def decayTemp(self):
        """Multiplies the activity temperature by cfg.guildActivityDecayRate,
        with a lower temperature bound of cfg.minGuildActivity.
        """
        if self.isActive:
            self.setTemp(self.temperature * cfg.guildActivityDecayRate)


    def raiseTemp(self, amount: float):
        """Raise the activity temperature by a given amount. The operation is a simple addition.
        This operation always sets self.isActive to True.

        :param float amount: The amount to raise the temperature by
        """
        self.setTemp(self.temperature + amount)


    def xpToDivUp(self) -> int:
        """Decides the amount of xp a user must have in order to leave this division.

        :return: the amount of xp a user must have in order to leave this division
        :rtype: int
        """
        if self.maxLevel >= cfg.maxTechLevel:
            return gameMaths.bountyHuntingXPForLevel(self.maxLevel)
        return gameMaths.bountyHuntingXPForLevel(self.maxLevel + 1)


    async def serialize(self, **kwargs: Any) -> TSchema:
        """Serialize this division into dictionary format, to be recreated completely.

        :return: A dictionary containing all of the current bounties and the activity temperature
        :rtype: dict
        """
        baseData = await super().serialize(**kwargs)

        activeBounties: Dict[int, List[bounty.Bounty[SerializedActiveBounty]]] = \
            {l: [] for l in range(self.minLevel, self.maxLevel + 1)}
        
        escapedBounties: Dict[int, List[bounty.Bounty[SerializedEscapedBounty]]] = \
            {l: [] for l in range(self.minLevel, self.maxLevel + 1)}

        for b in await self.allBounties:
            if b.isEscaped:
                # Casting here because we know the bounty is escaped
                escapedBounties[b.techLevel].append(cast(bounty.Bounty[SerializedEscapedBounty], b))
            else:
                activeBounties[b.techLevel].append(b)

        data: SerializedBountyDivision = {
            "id": self.id,
            "tier": self.tier.name,
            "guildId": self.guildId,
            "temperature": self.temperature, "minLevel": self.minLevel, "maxLevel": self.maxLevel,
                                          
            "bounties": {level: [await b.serialize(**kwargs) for b in levelBounties]
                        for level, levelBounties in activeBounties.items()},

            "escapedBounties": {level: [await b.serialize(**kwargs) for b in levelBounties]
                        for level, levelBounties in escapedBounties.items()},
        }
        
        if self.spawnAlertRoleId is not None:
            data["spawnAlertRoleId"] = self.spawnAlertRoleId

        if hasBountyBoard(self):
            data["bountyBoardChannel"] = await (await self.bountyBoardChannel).serialize(**kwargs)

        return cast(TSchema, {**baseData, **data})


    @classmethod
    async def deserialize(cls, data: TSchema, **kwargs: Any) -> BountyDivision[TSchema]:
        bbcData = data.get("bountyBoardChannel", None)
        bbc = None if bbcData is None else await BountyBoardChannel.deserialize(bbcData)
        allBounties = [await bounty.Bounty.deserialize(b)
                       for levelBounties in chain(data["bounties"].values(), data["escapedBounties"].values())
                       for b in levelBounties]
        
        if not (tierStr := data.get("tier", None)) or not (tier := BountyDivisionTier.fromStr(tierStr)):
            levelRange = (data["minLevel"], data["maxLevel"])
            tierIndex = cfg.bountyDivisionLevels.index(levelRange)
            tier = BountyDivisionTier(tierIndex + 1)
        
        return BountyDivision(
            id=data["id"],
            guildId=data["guildId"],
            temperature=data["temperature"],
            tier=tier,
            bountyBoardChannelId=None if bbc is None else bbc.id,
            _bountyBoardChannel=bbc,
            _allBounties=allBounties)


AnyBountyDivision = BountyDivision[SerializedBountyDivision]


@runtime_checkable
class WithBountyBoard(Protocol):
    @property
    async def bountyBoardChannel(self) -> AnyBountyBoardChannel: ...

    def __instancecheck__(self, __instance: Any) -> bool:
        # If a division has a bountyBoardChannelId, then the bountyboardchannel *should*
        # exist - if not then this is an error state
        return isinstance(__instance, BountyDivision) and __instance.bountyBoardChannelId != None
    

def hasBountyBoard(division: BountyDivision[Any]) -> TypeGuard[WithBountyBoard]:
    return isinstance(division, WithBountyBoard)
