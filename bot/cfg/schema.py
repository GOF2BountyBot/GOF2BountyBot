from carica.models import SerializableDataClass, SerializableTimedelta, SerializablePath
from carica.typeChecking import TypeOverride, _DeserializedTypeOverrideProxy
from dataclasses import dataclass, field
import os
from typing import Dict, List, Literal, Set, Tuple, TypeVar, Union, Any, cast
from pathlib import PosixPath, WindowsPath, Path

from ..lib.emojis import IBasedEmoji, UninitializedBasedEmoji, BasedEmoji

T = TypeVar("T", bound=Path)

class ConcatenatableSerializablePath(SerializablePath):
    def __new__(cls, *args, **kwargs):
        if cls is ConcatenatableSerializablePath:
            cls = ConcatenatableSerializableWindowsPath if os.name == 'nt' else ConcatenatableSerializablePosixPath
        # Ignoring a warning here because pyright can't see the private member _from_parts. It's there if you look at the class
        self = cls._from_parts(args) # type: ignore[reportGeneralTypeIssues]
        if not self._flavour.is_supported:
            raise NotImplementedError("cannot instantiate %r on your system"
                                      % (cls.__name__,))
        return self

    def __add__(self, o: T) -> Union[T, str]:
        if isinstance(o, Path):
            # Ignoring a warning here because pyright thinks that joinpath takes a StrPath, but if you look inside
            # of the source, the args are parsed with os.fspath which takes any PathLike.
            return self.joinpath(o) # type: ignore[reportGeneralTypeIssues]
        elif isinstance(o, str):
            return str(self) + o
        raise TypeError(f"Can only add Path or str to {type(self).__name__}, not {type(o).__name__}")


    def __radd__(self, o: T) -> Union[T, str]:
        if isinstance(o, Path):
            return o.joinpath(self)
        elif isinstance(o, str):
            return o + str(self)
        raise TypeError(f"Can only add Path or str to {type(self).__name__}, not {type(o).__name__}")


    def __iadd__(self, o: T) -> T:
        raise ValueError(f"Cannot extend the contents of a {type(self).__name__}")

class ConcatenatableSerializableWindowsPath(ConcatenatableSerializablePath, WindowsPath):
    pass

class ConcatenatableSerializablePosixPath(ConcatenatableSerializablePath, PosixPath):
    pass


EmojisFieldType = Union[IBasedEmoji, List["EmojisFieldType"], Set["EmojisFieldType"], Tuple["EmojisFieldType"], Dict[Any, "EmojisFieldType"]] # type: ignore

def convertEmoji(o) -> EmojisFieldType:
    if isinstance(o, _DeserializedTypeOverrideProxy):
        o = o.__wrapped__

    if isinstance(o, BasedEmoji):
        return o
    elif isinstance(o, UninitializedBasedEmoji):
        return o.initialize()
    elif isinstance(o, (list, set, tuple)):
        return cast(EmojisFieldType, type(o)(convertEmoji(x) for x in o))
    elif isinstance(o, dict):
        return {k: convertEmoji(v) for k, v in o.items()}
    else:
        raise TypeError(f"Found non-UninitializedBasedEmoji object, type {type(o).__name__}: {o}")


@dataclass
class EmojisConfig(SerializableDataClass):
    longProcess: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    # The emoji that will be used when attempting to display an emoji which the bot cannot access. Make sure this is accessible.
    unrecognisedEmoji: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    # When a user message prompts a DM to be sent, this emoji will be added to the message reactions.
    dmSent: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    cancel: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    submit: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    delete: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    spiral: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    error: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    accept: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    reject: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    next: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    previous: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    numbers: List[BasedEmoji] = field(default_factory=TypeOverride(List[UninitializedBasedEmoji], list))
    # The default emojis to list in a reaction menu
    menuOptions: List[BasedEmoji] = field(default_factory=TypeOverride(List[UninitializedBasedEmoji], list))

    # Default emoji to assign to shipSkinTool items
    shipSkinTool: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)

    # Default emoji to assign to bbCrates containing shipSkinTools
    skinCrate: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)

    # Default emoji to assign to all other crates
    defaultCrate: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    
    # Emoji sent with new bounty listings
    newBounty: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)

    bountyRespawn: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)

    newIssue: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    issueClosed: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    bug: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    feature: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    gameBalance: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    optimisation: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)

    cropImage: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    stretchImage: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)

    classicMode: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)

    money: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)

    rarity_common: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    rarity_uncommon: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    rarity_rare: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    rarity_epic: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)

    divUpUnlocked: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)
    prestigeUnlocked: BasedEmoji = TypeOverride(UninitializedBasedEmoji, BasedEmoji.EMPTY)


    def initializeEmojis(self):
        """Converts all fields from UninitializedBasedEmoji to BasedEmoji.
        Throws errors if initialization of any emoji failed.
        """
        for varname in self._fieldNames():
            setattr(self, varname, convertEmoji(getattr(self, varname)))


@dataclass
class TimeoutsConfig(SerializableDataClass):
    # A generic timeout used as the default for menu interactions
    menuInteractionDefault: SerializableTimedelta

    helpMenu: SerializableTimedelta
    BASED_updateCheckFrequency: SerializableTimedelta
    dataSaveFrequency: SerializableTimedelta

    # Amount of time before a duel request expires
    duelRequest: SerializableTimedelta

    # Amount of time to wait between refreshing stock of all shops
    shopRefresh: SerializableTimedelta

    # time to put users on cooldown between using !bb check
    checkCooldown: SerializableTimedelta

    # Default amount of time reaction menus should be active for
    roleMenuExpiry: SerializableTimedelta
    duelChallengeMenuExpiry: SerializableTimedelta
    pollMenuExpiry: SerializableTimedelta

    # The time between decrements to the guild activity temperatures of each tech level
    guildActivityDecay: SerializableTimedelta

    # when using random bounty delay generation, use these min and max points
    # when using random-routeScale generation, use these min and max points for bounties of route length 1
    newBountyDelayRandomMin: SerializableTimedelta
    newBountyDelayRandomMax: SerializableTimedelta

    # The amount of time a user must wait before they are allowed to submit a new github issue
    githubIssueSubmitDelay: SerializableTimedelta

    # Time allowed to select 'crop' or 'stretch' for incorrectly shaped autoskin input images
    selectImageSizeHandling: SerializableTimedelta

    toggleClassicMode: SerializableTimedelta

    # The termination signal checking period.
    shutdownCheckPeriod: SerializableTimedelta

    # The cooldown between uses of the transfer command.
    homeGuildTransferCooldown: SerializableTimedelta

    # time to wait inbetween spawning bounties, when newBountyDelayType starts with 'fixed'
    # when using fixed-routeScale generation, use this for bounties of route length 1
    newBountyFixedDelta: SerializableTimedelta


def _fixPath(val: Union[str, Path]) -> str:
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
        for varname, varvalue in self._fieldItems():
            if isinstance(varvalue, Path):
                newVal = _fixPath(varvalue)
            elif isinstance(varvalue, list):
                newVal = [_fixPath(p) for p in varvalue]
            else:
                raise TypeError(f"Unsupported type in config for path {varname}: {type(varvalue).__name__}")
            setattr(self, varname, newVal)


@dataclass
class BasicAccessLevelNames(SerializableDataClass):
    user: str
    serverAdmin: str
    developer: str

GitHubIssueType = Literal["Bug report", "Feature request", "New item alias"]
# Pass these into lib.ids.indexToId for the encoded ID.
gitHubIssueIdTypes: Dict[int, GitHubIssueType] = {
    0: "Bug report",
    1: "Feature request",
    2: "New item alias"
}
gitHubIssueTypeIds: Dict[GitHubIssueType, int] = {v: k for k, v in gitHubIssueIdTypes.items()}

def gitHubIssueTypeLabelsDict() -> Dict[GitHubIssueType, List[str]]:
    return {"Bug report": [], "Feature request": [], "New item alias": []}