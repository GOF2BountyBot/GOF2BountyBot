from carica.models import SerializableDataClass, SerializableTimedelta, SerializablePath # type: ignore[import]
from dataclasses import dataclass
import os
from typing import Dict, List, Set, Tuple, TypeVar, Union, Any, cast
from pathlib import PosixPath, WindowsPath, Path

from ..lib.emojis import IBasedEmoji, UninitializedBasedEmoji


class UnpackableSerializableTimedelta(SerializableTimedelta):
    def keys(self):
        return ["weeks", "days", "hours", "minutes", "seconds", "milliseconds", "microseconds"]

    def __getitem__(self, key):
        return self.serialize()[key]

T = TypeVar("T", bound=Path)

class ConcatenatableSerializablePath(SerializablePath):
    def __new__(cls, *args, **kwargs):
        if cls is ConcatenatableSerializablePath:
            cls = ConcatenatableSerializableWindowsPath if os.name == 'nt' else ConcatenatableSerializablePosixPath
        self = cls._from_parts(args, init=False)
        if not self._flavour.is_supported:
            raise NotImplementedError("cannot instantiate %r on your system"
                                      % (cls.__name__,))
        self._init()
        return self

    def __add__(self, o: T) -> Union[T, str]:
        if isinstance(o, Path):
            return self.joinpath(o)
        elif isinstance(o, str):
            return str(self) + o
        raise TypeError(f"Can only add Path or str to {type(self).__name__}, not {type(o).__name__}")


    def __radd__(self, o: T) -> Union[T, str]:
        if isinstance(o, Path):
            return o.joinpath(self)
        elif isinstance(o, str):
            return o + str(self)
        raise TypeError(f"Can only add Path or str to {type(self).__name__}, not {type(o).__name__}")


    def __iadd__(self, o: T):
        raise ValueError(f"Cannot extend the contents of a {type(self).__name__}")

class ConcatenatableSerializableWindowsPath(ConcatenatableSerializablePath, WindowsPath):
    pass

class ConcatenatableSerializablePosixPath(ConcatenatableSerializablePath, PosixPath):
    pass


EmojisFieldType = Union[IBasedEmoji, List["EmojisFieldType"], Set["EmojisFieldType"], Tuple["EmojisFieldType"], Dict[Any, "EmojisFieldType"]] # type: ignore

def convertEmoji(o) -> EmojisFieldType:
    if isinstance(o, UninitializedBasedEmoji):
        return o.initialize()
    elif isinstance(o, (list, set, tuple)):
        return cast(EmojisFieldType, type(o)(convertEmoji(x) for x in o))
    elif isinstance(o, dict):
        return {k: convertEmoji(v) for k, v in o.items()}
    else:
        raise TypeError(f"Found non-UninitializedBasedEmoji object, type {type(o).__name__}: {o}")


@dataclass
class EmojisConfig(SerializableDataClass):
    # The emoji that will be used when attempting to display an emoji which the bot cannot access. Make sure this is accessible.
    unrecognisedEmoji: Union[UninitializedBasedEmoji, IBasedEmoji]
    longProcess: Union[UninitializedBasedEmoji, IBasedEmoji]
    # When a user message prompts a DM to be sent, this emoji will be added to the message reactions.
    dmSent: Union[UninitializedBasedEmoji, IBasedEmoji]
    cancel: Union[UninitializedBasedEmoji, IBasedEmoji]
    submit: Union[UninitializedBasedEmoji, IBasedEmoji]
    spiral: Union[UninitializedBasedEmoji, IBasedEmoji]
    error: Union[UninitializedBasedEmoji, IBasedEmoji]
    accept: Union[UninitializedBasedEmoji, IBasedEmoji]
    reject: Union[UninitializedBasedEmoji, IBasedEmoji]
    next: Union[UninitializedBasedEmoji, IBasedEmoji]
    previous: Union[UninitializedBasedEmoji, IBasedEmoji]
    numbers: List[Union[UninitializedBasedEmoji, IBasedEmoji]]
    # The default emojis to list in a reaction menu
    menuOptions: List[Union[UninitializedBasedEmoji, IBasedEmoji]]

    # Default emoji to assign to shipSkinTool items
    shipSkinTool: Union[UninitializedBasedEmoji, IBasedEmoji]

    # Default emoji to assign to bbCrates containing shipSkinTools
    skinCrate: Union[UninitializedBasedEmoji, IBasedEmoji]

    # Default emoji to assign to all other crates
    defaultCrate: Union[UninitializedBasedEmoji, IBasedEmoji]
    
    # Emoji sent with new bounty listings
    newBounty: Union[UninitializedBasedEmoji, IBasedEmoji]

    bountyRespawn: Union[UninitializedBasedEmoji, IBasedEmoji]

    newIssue: Union[UninitializedBasedEmoji, IBasedEmoji]
    issueClosed: Union[UninitializedBasedEmoji, IBasedEmoji]
    bug: Union[UninitializedBasedEmoji, IBasedEmoji]
    feature: Union[UninitializedBasedEmoji, IBasedEmoji]
    gameBalance: Union[UninitializedBasedEmoji, IBasedEmoji]
    optimisation: Union[UninitializedBasedEmoji, IBasedEmoji]

    cropImage: Union[UninitializedBasedEmoji, IBasedEmoji]
    stretchImage: Union[UninitializedBasedEmoji, IBasedEmoji]

    classicMode: Union[UninitializedBasedEmoji, IBasedEmoji]

    money: Union[UninitializedBasedEmoji, IBasedEmoji]

    rarity_common: Union[UninitializedBasedEmoji, IBasedEmoji]
    rarity_uncommon: Union[UninitializedBasedEmoji, IBasedEmoji]
    rarity_rare: Union[UninitializedBasedEmoji, IBasedEmoji]
    rarity_epic: Union[UninitializedBasedEmoji, IBasedEmoji]

    divUpUnlocked: Union[UninitializedBasedEmoji, IBasedEmoji]
    prestigeUnlocked: Union[UninitializedBasedEmoji, IBasedEmoji]


    def initializeEmojis(self):
        """Converts all fields from UninitializedBasedEmoji to BasedEmoji.
        Throws errors if initialization of any emoji failed.
        """
        for varname in self._fieldNames():
            setattr(self, varname, convertEmoji(getattr(self, varname)))


@dataclass
class TimeoutsConfig(SerializableDataClass):
    helpMenu: UnpackableSerializableTimedelta
    BASED_updateCheckFrequency: UnpackableSerializableTimedelta
    dataSaveFrequency: UnpackableSerializableTimedelta

    # Amount of time before a duel request expires
    duelRequest: UnpackableSerializableTimedelta

    # Amount of time to wait between refreshing stock of all shops
    shopRefresh: UnpackableSerializableTimedelta

    # time to put users on cooldown between using !bb check
    checkCooldown: UnpackableSerializableTimedelta

    # Default amount of time reaction menus should be active for
    roleMenuExpiry: UnpackableSerializableTimedelta
    duelChallengeMenuExpiry: UnpackableSerializableTimedelta
    pollMenuExpiry: UnpackableSerializableTimedelta

    # The time between decrements to the guild activity temperatures of each tech level
    guildActivityDecay: UnpackableSerializableTimedelta

    # when using random bounty delay generation, use these min and max points
    # when using random-routeScale generation, use these min and max points for bounties of route length 1
    newBountyDelayRandomMin: UnpackableSerializableTimedelta
    newBountyDelayRandomMax: UnpackableSerializableTimedelta

    # The amount of time a user must wait before they are allowed to submit a new github issue
    githubIssueSubmitDelay: UnpackableSerializableTimedelta

    # Time allowed to select 'crop' or 'stretch' for incorrectly shaped autoskin input images
    selectImageSizeHandling: UnpackableSerializableTimedelta

    toggleClassicMode: UnpackableSerializableTimedelta

    # The termination signal checking period.
    shutdownCheckPeriod: UnpackableSerializableTimedelta

    # The cooldown between uses of the transfer command.
    homeGuildTransferCooldown: UnpackableSerializableTimedelta

    # time to wait inbetween spawning bounties, when newBountyDelayType starts with 'fixed'
    # when using fixed-routeScale generation, use this for bounties of route length 1
    newBountyFixedDelta: UnpackableSerializableTimedelta


def _fixPath(val: str) -> str:
    # Normalize path
    normalized = os.path.normpath(val)
    
    # If the path is a file, get the path to the parent directory
    pathSplit = os.path.splitext(normalized)
    pathDir = os.path.dirname(pathSplit[0]) if pathSplit[1] else pathSplit[0]
    
    # Create missing directories
    if pathDir and not os.path.isdir(pathDir):
        os.makedirs(pathDir)

    return normalized


@dataclass
class PathsConfig(SerializableDataClass):
    # path to JSON files for database saves
    usersDB: ConcatenatableSerializablePath
    guildsDB: ConcatenatableSerializablePath
    reactionMenusDB: ConcatenatableSerializablePath
    # path to folder to save log txts to
    logsFolder: ConcatenatableSerializablePath

    # folders containing game objects to load into the game
    CriminalMETAFolder: ConcatenatableSerializablePath
    shipSkinMETAFolder: ConcatenatableSerializablePath
    bbShipUpgradesMETAFolder: ConcatenatableSerializablePath
    SolarSystemMETAFolder: ConcatenatableSerializablePath
    bbCommodityMETAFolder: ConcatenatableSerializablePath
    bbModuleMETAFolder: ConcatenatableSerializablePath
    bbSecondaryMETAFolder: ConcatenatableSerializablePath
    bbShipMETAFolder: ConcatenatableSerializablePath
    bbWeaponMETAFolder: ConcatenatableSerializablePath
    bbTurretMETAFolder: ConcatenatableSerializablePath
    bbToolMETAFolder: ConcatenatableSerializablePath
    bbMedalsMETAFolder: ConcatenatableSerializablePath
    
    # Temporary folder for autoskin renders
    tempRenders: ConcatenatableSerializablePath
    
    # snowball images to use in ThrowSnowballTool
    snowballImages: ConcatenatableSerializablePath
    
    # map image used in bounty route renders
    mapImage: ConcatenatableSerializablePath

    # The image to display behind the XP bar during cmd_stats
    userProfileBackground: ConcatenatableSerializablePath

    # Font to use for user profiles in the stats command.
    userProfileFont: ConcatenatableSerializablePath

    # Background images to display behind duel results. Images are selected at random. Give [] to disable
    duelResultsBackgrounds: List[ConcatenatableSerializablePath]
    # Image to display between the background and content. Give "" to disable
    duelResultsUnderlay: ConcatenatableSerializablePath
    # Image to display on top of all other graphics. Give "" to disable
    duelResultsOverlay: ConcatenatableSerializablePath
    duelResultsRightWinner: ConcatenatableSerializablePath
    duelResultsLeftWinner: ConcatenatableSerializablePath
    duelResultsDraw: ConcatenatableSerializablePath

    # Font to use for duel statistics, e.g time to kill
    duelResultsFont: ConcatenatableSerializablePath


    def createMissingDirectories(self):
        # Normalize all paths and create missing directories
        for varname, varvalue in self._fieldItems().items():
            if isinstance(varvalue, Path):
                newVal = _fixPath()
            elif isinstance(varvalue, list):
                newVal = [_fixPath(p) for p in varvalue]
            setattr(self, varname, newVal)


@dataclass
class BasicAccessLevelNames(SerializableDataClass):
    user: str
    serverAdmin: str
    developer: str
