from typing import Dict, List
from carica.models import SerializableDataClass, SerializablePath # type: ignore[import]
from dataclasses import dataclass
from ..lib.emojis import BasedEmoji

TimedeltaDict = Dict[str, int]


@dataclass
class EmojisConfig(SerializableDataClass):
    unrecognisedEmoji: BasedEmoji
    longProcess: BasedEmoji
    dmSent: BasedEmoji
    cancel: BasedEmoji
    submit: BasedEmoji
    spiral: BasedEmoji
    error: BasedEmoji
    accept: BasedEmoji
    reject: BasedEmoji
    next: BasedEmoji
    previous: BasedEmoji
    numbers: List[BasedEmoji]
    menuOptions: List[BasedEmoji]
    shipSkinTool: BasedEmoji
    skinCrate: BasedEmoji
    defaultCrate: BasedEmoji
    newBounty: BasedEmoji


@dataclass
class TimeoutsConfig(SerializableDataClass):
    helpMenu: TimedeltaDict
    BASED_updateCheckFrequency: TimedeltaDict
    dataSaveFrequency: TimedeltaDict
    duelRequest: TimedeltaDict
    shopRefresh: TimedeltaDict
    checkCooldown: TimedeltaDict
    roleMenuExpiry: TimedeltaDict
    duelChallengeMenuExpiry: TimedeltaDict
    pollMenuExpiry: TimedeltaDict
    guildActivityDecay: TimedeltaDict
    newBountyDelayRandomMin: TimedeltaDict
    newBountyDelayRandomMax: TimedeltaDict
    githubIssueSubmitDelay: TimedeltaDict


@dataclass
class PathsConfig(SerializableDataClass):
    usersDB: SerializablePath
    guildsDB: SerializablePath
    reactionMenusDB: SerializablePath
    logsFolder: SerializablePath
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
