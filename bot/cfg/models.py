from typing import Dict, List
from carica.models import SerializableDataClass, SerializablePath # type: ignore[import]
from dataclasses import dataclass
from ..lib.emojis import BasedEmoji, UninitializedBasedEmoji

TimedeltaDict = Dict[str, int]

def _initBasedEmoji(varValue, rejectInvalid=True):
    # ensure single emoji vars are emojis
    if isinstance(varValue, UninitializedBasedEmoji):
        return BasedEmoji.fromUninitialized(varValue, rejectInvalid=rejectInvalid)

    # ensure list emoji vars only contain emojis
    elif any(isinstance(varValue, t) for t in (list, set, tuple)):
        return type(varValue)(_initBasedEmoji(v, rejectInvalid=rejectInvalid) for v in varValue)

    elif isinstance(varValue, dict):
        return {k: _initBasedEmoji(v, rejectInvalid=rejectInvalid) for k, v in varValue.items()}

    elif isinstance(varValue, EmojisConfig):
        varValue.initAll()
        return varValue
    
    else:
        # raise an error on unexpected types
        raise ValueError(f"Unexpected type {type(varValue)} in EmojisConfig: {varValue}")

@dataclass
class EmojisConfig(SerializableDataClass):
    unrecognisedEmoji: UninitializedBasedEmoji
    longProcess: UninitializedBasedEmoji
    dmSent: UninitializedBasedEmoji
    cancel: UninitializedBasedEmoji
    submit: UninitializedBasedEmoji
    spiral: UninitializedBasedEmoji
    error: UninitializedBasedEmoji
    accept: UninitializedBasedEmoji
    reject: UninitializedBasedEmoji
    next: UninitializedBasedEmoji
    previous: UninitializedBasedEmoji
    numbers: List[UninitializedBasedEmoji]
    menuOptions: List[UninitializedBasedEmoji]
    shipSkinTool: UninitializedBasedEmoji
    skinCrate: UninitializedBasedEmoji
    defaultCrate: UninitializedBasedEmoji
    newBounty: UninitializedBasedEmoji

    def initAll(self, rejectInvalid=True):
        for varName in self.__dataclass_fields__.keys():
            varValue = getattr(self, varName)
            setattr(self, varName, _initBasedEmoji(varValue, rejectInvalid=rejectInvalid))
            

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
