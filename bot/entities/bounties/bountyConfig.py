from typing import List, Dict, Optional, Any, Protocol, cast, overload, TypeVar, runtime_checkable

from dataclasses import dataclass, field
import random
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

from discord.utils import utcnow

from ...cfg import bbData, cfg
from ... import lib
from ...lib import gameMaths
from ...lib.timeUtil import utcfromtimestamp
from ..items.ship import shipInstance
from ...repositories.bountyRepository import BountyRepository
from ...repositories.criminalRepository import CriminalRepository
from ...repositories.solarSystemRepository import SolarSystemRepository
from ...repositories.shipSpecRepository import ShipSpecRepository
from ...repositories.shipInstanceRepository import ShipInstanceRepository
from ...repositories.primaryWeaponRepository import PrimaryWeaponRepository
from ...repositories.userRepository import UserRepository
from ...repositories.discordUserRepository import DiscordUserRepository
from ...repositories.itemRepository import ItemRepository
from ..bounties import criminal, bounty
from . import bountyDivision
from ...serialization.jsonSerializer import JsonSerializer
from ..items.ship.shipInstanceFactory import ShipInstanceFactory

@runtime_checkable
class GeneratedBountyConfigBase(Protocol):
    """Data class describing all attributes needed for a bounty.

    :var str faction: The faction owning this bounty
    :var str name: The name of the wanted criminal. If this is a player bounty, name should be the player mention.
    :var bool isPlayer: Whether or not the target criminal is a player or an npc
    :var List[int] route: the IDs of systems in this bounty's route
    :var int start: The ID of the system at the start of the route
    :var int end: The ID of the system at the end of the route
    :var int answer: The ID of the system where the criminal is located
    :var checked: Dictionary of system IDs to user IDs, where the id corresponds to the user who checked that system,
                    or -1 if the system is unchecked.
    :vartype checked: dict[str, int]
    :var int reward: Prize pool of credits to award to contributing users
    :var datetime issueTime: A utc timestamp representing the time at which the bounty was issued
    :var datetime endTime: A utc timestamp representing the time at which the bounty should automatically expire
    :var str icon: A URL directly linking to an image to use as the criminal's icon
    :var List[str] aliases: Aliases that can be used to refer to this criminal
    :var str wiki: The page to link to as the criminal's wiki, in their info embed
    :var bool generated: whether or not this config is ready to be used. The config must verify and generate its attributes before
                    they can be used in a bounty.
    :var ShipInstance activeShip: The ship this criminal should equip
    :var bool generated: Whether or not this config has been populated yet by the config factory
    """
    isPlayer: bool
    criminal: "criminal.AnyCriminal"
    faction: str
    route: List[int]
    start: int
    end: int
    answer: int
    checked: Dict[int, int]
    reward: int
    issueTime: datetime
    endTime: datetime
    icon: str
    aliases: List[str]
    wiki: str
    activeShip: shipInstance.AnyShipInstance
    techLevel: int
    rewardPerSys: int
    generated: bool = True

    def __instancecheck__(self, __instance: Any) -> bool:
        return isinstance(__instance, BountyConfigBase) \
            and __instance.generated == True \
            and isinstance(__instance.criminal, criminal.Criminal) \
            and isinstance(__instance.faction, str) \
            and isinstance(__instance.route, list) and len(__instance.route) != 0 \
            and isinstance(__instance.start, int) \
            and isinstance(__instance.end, int) \
            and isinstance(__instance.answer, int) \
            and len(__instance.checked) != 0 \
            and isinstance(__instance.reward, int) \
            and isinstance(__instance.issueTime, float) \
            and isinstance(__instance.endTime, float) \
            and isinstance(__instance.icon, str) \
            and isinstance(__instance.aliases, list) \
            and isinstance(__instance.activeShip, shipInstance.ShipInstance) \
            and isinstance(__instance.techLevel, int) \
            and isinstance(__instance.rewardPerSys, int)


@runtime_checkable
class GeneratedPlayerBountyConfig(GeneratedBountyConfigBase, Protocol):
    isPlayer: bool = True
    playerId: int

    def __instancecheck__(self, __instance: Any) -> bool:
        return isinstance(__instance, GeneratedBountyConfigBase) \
            and __instance.isPlayer == True \
            and hasattr(__instance, "playerId") and isinstance(getattr(__instance, "playerId"), int)


@runtime_checkable
class GeneratedNpcBountyConfig(GeneratedBountyConfigBase, Protocol):
    isPlayer: bool = False

    def __instancecheck__(self, __instance: Any) -> bool:
        return isinstance(__instance, GeneratedBountyConfigBase) \
            and __instance.isPlayer == False


@runtime_checkable
class WithCriminal(Protocol):
    criminal: "criminal.AnyCriminal"

    def __instancecheck__(self, __instance: Any) -> bool:
        return hasattr(__instance, "criminal") and isinstance(getattr(__instance, "criminal"), criminal.Criminal)


TConfig = TypeVar("TConfig", bound="BountyConfigBase")

@dataclass
class BountyConfigBase(ABC):
    """Data class describing all attributes needed for a bounty.
    All parameters are optional. If one is not given, it will be randomly generated.

    :var Optional[str] faction: The faction owning this bounty
    :var Optional[str] name: The name of the wanted criminal. If this is a player bounty, name should be the player mention.
    :var Optional[bool] isPlayer: Whether or not the target criminal is a player or an npc
    :var Optional[List[int]] route: the IDs of systems in this bounty's route
    :var Optional[int] start: The ID of the system at the start of the route
    :var Optional[int] end: The ID of the system at the end of the route
    :var Optional[int] answer: The ID of the system where the criminal is located
    :var checked: Dictionary of system IDs to user IDs, where the id corresponds to the user who checked that system,
                    or -1 if the system is unchecked.
    :vartype checked: Optional[dict[str, int]]
    :var Optional[int] reward: Prize pool of credits to award to contributing users
    :var Optional[datetime] issueTime: A utc timestamp representing the time at which the bounty was issued
    :var Optional[datetime] endTime: A utc timestamp representing the time at which the bounty should automatically expire
    :var Optional[str] icon: A URL directly linking to an image to use as the criminal's icon
    :var Optional[List[str]] aliases: Aliases that can be used to refer to this criminal
    :var Optional[str] wiki: The page to link to as the criminal's wiki, in their info embed
    :var Optional[bool] generated: whether or not this config is ready to be used. The config must verify and generate its attributes before
                    they can be used in a bounty.
    :var Optional[ShipInstance] activeShip: The ship this criminal should equip
    :var bool generated: Whether or not this config has been populated yet by the config factory
    """
    isPlayer: bool = False
    criminal: Optional["criminal.AnyCriminal"] = None
    faction: Optional[str] = None
    route: Optional[List[int]] = None
    start: Optional[int] = None
    end: Optional[int] = None
    answer: Optional[int] = None
    checked: Dict[int, int] = field(default_factory=lambda: {})
    reward: Optional[int] = None
    issueTime: Optional[datetime] = None
    endTime: Optional[datetime] = None
    icon: Optional[str] = None
    aliases: Optional[List[str]] = None
    activeShip: Optional[shipInstance.AnyShipInstance] = None
    techLevel: Optional[int] = None
    rewardPerSys: Optional[int] = None
    generated: bool = False

    @abstractmethod
    def shallowCopy(self: TConfig) -> TConfig:
        """Make a shallow copy with the same attributes as this instance.
        If this instance has not yet been generated, neither will the copy.

        :return: A shallow copy of this object
        :rtype: BountyConfigBase
        """
        raise NotImplementedError()


@dataclass
class PlayerBountyConfig(BountyConfigBase):
    isPlayer = True
    playerId: int = -1

    def shallowCopy(self):
        return PlayerBountyConfig(isPlayer=True, playerId=self.playerId, criminal=self.criminal, faction=self.faction, route=self.route, start=self.start, end=self.end, answer=self.answer, checked=self.checked, reward=self.reward, issueTime=self.issueTime, endTime=self.endTime, icon=self.icon, aliases=self.aliases, wiki=self.wiki, activeShip=self.activeShip, techLevel=self.techLevel, rewardPerSys=self.rewardPerSys, generated=self.generated)


@dataclass
class NpcBountyConfig(BountyConfigBase):
    isPlayer = False

    def shallowCopy(self):
        return NpcBountyConfig(isPlayer=False, criminal=self.criminal, faction=self.faction, route=self.route, start=self.start, end=self.end, answer=self.answer, checked=self.checked, reward=self.reward, issueTime=self.issueTime, endTime=self.endTime, icon=self.icon, aliases=self.aliases, wiki=self.wiki, activeShip=self.activeShip, techLevel=self.techLevel, rewardPerSys=self.rewardPerSys, generated=self.generated)


class BountyConfigFactory:
    def __init__(self,
            criminalRepository: CriminalRepository,
            bountyRepository: BountyRepository,
            solarSystemRepository: SolarSystemRepository,
            serializer: JsonSerializer,
            shipSpecRepository: ShipSpecRepository,
            shipInstanceRepository: ShipInstanceRepository,
            primaryWeaponRepository: PrimaryWeaponRepository,
            shipInstanceFactory: ShipInstanceFactory,
            itemRepository: ItemRepository,
            userRepository: UserRepository,
            discordUserRepository: DiscordUserRepository):
        self.criminalRepository = criminalRepository
        self.bountyRepository = bountyRepository
        self.solarSystemRepository = solarSystemRepository
        self.serializer = serializer
        self.shipSpecRepository = shipSpecRepository
        self.shipInstanceRepository = shipInstanceRepository
        self.primaryWeaponRepository = primaryWeaponRepository
        self.shipInstanceFactory = shipInstanceFactory
        self.itemRepository = itemRepository
        self.userRepository = userRepository
        self.discordUserRepository = discordUserRepository
        
    @overload
    async def generate(self, config: PlayerBountyConfig,
                       division: "bountyDivision.BountyDivision[Any]", noCriminal: bool = True,
                       forceKeepChecked: bool = False,
                       forceNoDBCheck: bool = False) -> GeneratedPlayerBountyConfig: ...
        
    @overload
    async def generate(self, config: NpcBountyConfig,
                       division: "bountyDivision.BountyDivision[Any]", noCriminal: bool = True,
                       forceKeepChecked: bool = False,
                       forceNoDBCheck: bool = False) -> GeneratedNpcBountyConfig: ...
    
    @overload
    async def generate(self, config: BountyConfigBase,
                       division: "bountyDivision.BountyDivision[Any]", noCriminal: bool = True,
                       forceKeepChecked: bool = False,
                       forceNoDBCheck: bool = False) -> GeneratedBountyConfigBase: ...
    
    async def generate(self, config: BountyConfigBase,
                       division: "bountyDivision.BountyDivision[Any]", noCriminal: bool = True,
                       forceKeepChecked: bool = False,
                       forceNoDBCheck: bool = False) -> GeneratedBountyConfigBase:
        """Validate all given config data, and randomly generate missing data.

        :param BountyDivision division: Division to which this bounty should belong. When forceNoDBCheck is True,
                                        this is ignored.
        :param bool noCriminal: If this is True, randomly generate a criminal object. (Default True)
        :param bool forceKeepChecked: If this is False, a blank checked dictionary will be used.
                                        This should only be set to be True when using a pre-made checked dictionary;
                                        e.g for custom bounties or for bounties loaded from file. (Default False)
        :param bool forceNoDBCheck: If this is False, do not check if the bounty already exists.
                                    This should only be used as a performance and compatibility measure when
                                    loading in a bounty from file. (Default False)
        :return: This BountyConfig object for chaining
        :rtype: BountyConfig
        :raise ValueError: When requesting an invalid faction, or when requesting an invalid reward amount
        :raise KeyError: When the requested criminal already exists in a bounty or when requesting an unknown system
        :raise OverflowError: When attempting to spawn a bounty into a full division
        """
        doDBCheck = not forceNoDBCheck

        if doDBCheck and await division.isFull() and (await division.hasMinTLBounty() or \
                (not await division.hasMinTLBounty() and config.techLevel not in [division.minLevel, -1])):
            raise OverflowError(f"The given division is full: {division.name}")
        
        if isinstance(config, PlayerBountyConfig):
            config = await self._generatePlayerCriminal(config, division, doDBCheck)
        elif isinstance(config, NpcBountyConfig):
            config = await self._generateNpcCriminal(config, division, doDBCheck)
        else:
            raise ValueError(f"Unsupported config type: {type(config).__name__}")

        # invalid techLevels are silently ignored
        if config.techLevel is None or config.techLevel < division.minLevel or config.techLevel > division.maxLevel:
            config.techLevel = await division.pickNewTL()
            # config.techLevel = gameMaths.pickRandomCriminalTL()

        if config.route is None or config.route == []:
            config.route = await self._generateRoute(config)
        else:
            await self._validateRoute(config)
                
        if config.answer is None:
            config.answer = random.choice(config.route)
        else:
            if config.answer not in config.route:
                raise ValueError(f"Answer system with id {config.answer} is not in the bounty's route")
            if not await self.solarSystemRepository.exists(config.answer):
                raise KeyError(f"Answer system with id {config.answer} does not exist")
        
        if config.activeShip is None:
            if config.isPlayer:
                raise ValueError("Attempted to generate a player bounty without providing the activeShip")

            # tech level 0 = guaranteed lowest difficulty loadout
            if config.techLevel == 0:
                config.activeShip = await self.serializer.deserialize(shipInstance.AnyShipInstance, cfg.level0CrimLoadout)
            # Otherwise, generate one based on difficulty
            else:
                config.activeShip = await self.shipInstanceFactory.generateLoadoutForLevel(config.techLevel - 1) # TODO: why -1?
                
        if config.reward is None or config.reward == -1:
            config.rewardPerSys = gameMaths.rewardPerSysCheck(config.techLevel, await config.activeShip.getValue())
            config.reward = config.rewardPerSys * len(config.route)
        elif config.reward < 0:
            raise ValueError(f"Invalid reward requested {config.reward}")
        
        if config.issueTime is None or config.issueTime == -1.0:
            config.issueTime = utcnow().replace(microsecond=0)
        if config.endTime == -1.0:
            config.endTime = (config.issueTime + timedelta(days=len(config.route)))

        if not forceKeepChecked:
            config.checked = {}
        for station in config.route:
            if not forceKeepChecked or station not in config.checked:
                config.checked[station] = -1

        config.generated = True
        return cast(GeneratedBountyConfigBase, config)


    async def getRespawnConfig(self, bounty: "bounty.AnyBounty") -> BountyConfigBase:
        """Create a new, partially configured, ungenerated BountyConfig object, to be used in the respawning of this bounty.

        :return: A new BountyConfig with the right attributes left ungenerated, to be populated on bounty respawn
        :rtype: BountyConfig
        """
        crim = await bounty.criminal
        
        if bounty.isPlayer:
            return PlayerBountyConfig(
                playerId=crim.playerId,
                criminal=crim,
                faction=bounty.faction,
                endTime=bounty.endTime,
                issueTime=bounty.issueTime,
                icon=crim.iconUrl,
                aliases=await crim.aliases,
                activeShip=await bounty.ship,
                techLevel=bounty.techLevel
            )
        
        return NpcBountyConfig(
            criminal=crim,
            faction=bounty.faction,
            endTime=bounty.endTime,
            issueTime=bounty.issueTime,
            icon=crim.iconUrl,
            aliases=await crim.aliases,
            activeShip=await bounty.ship,
            techLevel=bounty.techLevel
        )
    
    
    async def _generatePlayerCriminal(self, config: PlayerBountyConfig, division: "bountyDivision.BountyDivision[Any]", doDbCheck: bool):
        if config.criminal is not None:
            if doDbCheck and await self.bountyRepository.getBountyByCrim(division.guildId, config.playerId, allowEscaped=True):
                raise KeyError(f"BountyConfig: attempted to create config for already wanted bounty: {config.playerId}")

        dcUser = await self.discordUserRepository.get(config.playerId)
        if doDbCheck and dcUser is None:
            raise KeyError(f"Discord user id does not exist: {config.playerId}")
        
        if config.faction is None:
            config.faction = random.choice(bbData.bountyFactions)

        elif config.faction not in bbData.bountyFactions:
            raise ValueError(f"BOUCONF_CONS_INVFAC: Invalid faction requested '{config.faction}'")

        if config.criminal is None:
            if dcUser is None:
                raise KeyError(f"Discord user id does not exist: {config.playerId}")
            config.criminal = criminal.AnyCriminal.forUser(dcUser, config.faction)
        
        if config.activeShip is None or config.techLevel is None or config.techLevel == -1:
            user = await self.userRepository.get(config.playerId)
            if user is not None:
                if config.activeShip is None:
                    config.activeShip = await user.activeShip.copy(self.serializer)
                if config.techLevel is None or config.techLevel == -1:
                    config.techLevel = user.bountyHuntingLevel

        if not isinstance(config, WithCriminal):
            raise RuntimeError("Failed to generate player criminal")

        config.icon = config.icon or config.criminal.iconUrl or bbData.rocketIcon
        
        return config
    

    async def _generateNpcCriminal(self, config: NpcBountyConfig, division: "bountyDivision.BountyDivision[Any]", doDbCheck: bool):
        if config.criminal is not None:
            if doDbCheck and await self.bountyRepository.getBountyByCrim(division.guildId, config.criminal.id, allowEscaped=True):
                raise KeyError(f"BountyConfig: attempted to create config for already wanted bounty: {config.criminal.id}")

        if config.icon == "":
            config.icon = bbData.rocketIcon

        if config.faction is None:
            config.faction = random.choice(bbData.bountyFactions)

        elif config.faction not in bbData.bountyFactions:
            raise ValueError(f"BOUCONF_CONS_INVFAC: Invalid faction requested '{config.faction}'")

        if config.criminal is None:
            config.criminal = await self.criminalRepository.randomCriminal(forGuild=division.guildId, forFaction=config.faction)

        if not isinstance(config, WithCriminal):
            raise RuntimeError("Failed to generate NPC criminal")
        
        return config


    async def _validateRoute(self, config: BountyConfigBase):
        if not config.route:
            raise ValueError("route not provided")
        
        systems = await self.solarSystemRepository.getMany(config.route)
        try:
            lastSystem = next(s for s in systems if s.id == config.route[0])
        except StopIteration:
            raise KeyError(f"System 0 with id {config.route[0]} does not exist")
        
        for i, systemId in enumerate(config.route):
            if i == 0: continue
            
            if not any(True for s in lastSystem.neighbours if s.id == systemId):
                raise KeyError(f"Invalid route: system {i} with id {systemId} is not a neighbour of system {i - 1} with id {config.route[i - 1]}")
            
            try:
                lastSystem = next(s for s in systems if s.id == systemId)
            except StopIteration:
                raise KeyError(f"System {i} with id {systemId} does not exist")


    async def _generateRoute(self, config: BountyConfigBase) -> List[int]:
        tries = 3
        while tries:
            if config.start is None or config.start == -1:
                startAttempt = await self.solarSystemRepository.getRandom(withJumpGate=True)
                if startAttempt is None:
                    raise ValueError(f"Unable to pick start system. No systems exist with jumpgates.")
            else:
                startAttempt = await self.solarSystemRepository.get(config.start)
                if startAttempt is None:
                    raise ValueError(f"Requested start system does not exist: {config.start}")
                if not startAttempt.hasJumpGate:
                    raise ValueError(f"Requested start system does not have a jump gate: {config.start}")

            if config.end is None or config.end == -1:
                endAttempt = await self.solarSystemRepository.getRandom(withJumpGate=True)
                if endAttempt is None:
                    raise ValueError(f"Unable to pick end system. No systems exist with jumpgates.")
            else:
                endAttempt = await self.solarSystemRepository.get(config.end)
                if endAttempt is None:
                    raise ValueError(f"Requested end system does not exist: {config.end}")
                if not endAttempt.hasJumpGate:
                    raise ValueError(f"Requested end system does not have a jump gate: {config.end}")

            routeAttempt = lib.pathfinding.bbAStar(startAttempt, endAttempt)
            if not isinstance(routeAttempt, lib.pathfinding.PathfindingError):
                return routeAttempt
            tries -= 1

        raise ValueError(f"Unable to generate route. Start: {str(config.start) if config.start != -1 else '<auto>'} -> End: {str(config.end) if config.end != -1 else '<auto>'}")
