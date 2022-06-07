from carica.models import SerializableDataClass, SerializableTimedelta, SerializablePath # type: ignore[import]
from dataclasses import dataclass
import os
from typing import Dict, List, Set, Tuple, Union, Any, cast

from ..lib.emojis import IBasedEmoji, UninitializedBasedEmoji

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


@dataclass
class PathsConfig(SerializableDataClass):
    # path to JSON files for database saves
    usersDB: SerializablePath
    guildsDB: SerializablePath
    reactionMenusDB: SerializablePath
    # path to folder to save log txts to
    logsFolder: SerializablePath

    # folders containing game objects to load into the game
    CriminalMETAFolder: SerializablePath
    shipSkinMETAFolder: SerializablePath
    bbShipUpgradesMETAFolder: SerializablePath
    SolarSystemMETAFolder: SerializablePath
    bbCommodityMETAFolder: SerializablePath
    bbModuleMETAFolder: SerializablePath
    bbSecondaryMETAFolder: SerializablePath
    bbShipMETAFolder: SerializablePath
    bbWeaponMETAFolder: SerializablePath
    bbTurretMETAFolder: SerializablePath
    bbToolMETAFolder: SerializablePath
    bbMedalsMETAFolder: SerializablePath
    
    # Temporary folder for autoskin renders
    tempRenders: SerializablePath
    
    # snowball images to use in ThrowSnowballTool
    snowballImages: SerializablePath
    
    # map image used in bounty route renders
    mapImage: SerializablePath

    def createMissingDirectories(self):
        # Normalize all paths and create missing directories
        for varname in self._fieldNames():
            # Normalize path
            normalized = os.path.normpath(getattr(self, varname))
            setattr(self, varname, normalized)
            
            # If the path is a file, get the path to the parent directory
            pathSplit = os.path.splitext(normalized)
            pathDir = os.path.dirname(pathSplit[0]) if pathSplit[1] else pathSplit[0]
            
            # Create missing directories
            if pathDir and not os.path.isdir(pathDir):
                os.makedirs(pathDir)


@dataclass
class BasicAccessLevelNames(SerializableDataClass):
    user: str
    serverAdmin: str
    developer: str
