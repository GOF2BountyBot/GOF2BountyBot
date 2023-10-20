from typing import Dict, List, TypedDict, Union
from typing_extensions import NotRequired

from .criminal_json import SerializedCriminal
from ..items.ship.shipInstance_json import SerializedShipInstanceUnion


class SerializedBounty(TypedDict):
    faction: str
    route: List[str]
    answer: str
    checked: Dict[str, int]
    reward: int
    issueTime: float
    endTime: float
    isEscaped: bool
    criminal: SerializedCriminal
    rewardPerSys: int
    techLevel: int
    activeShip: NotRequired[SerializedShipInstanceUnion]


class SerializedEscapedBounty(SerializedBounty):
    respawnTime: float


SerializedBountyUnion = Union[SerializedBounty, SerializedEscapedBounty]
