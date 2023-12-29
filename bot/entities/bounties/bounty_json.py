from typing import Dict, List, TypedDict, Union
from typing_extensions import NotRequired

from ..items.ship.shipInstance_json import SerializedShipInstanceUnion


class SerializedBounty(TypedDict):
    faction: str
    route: List[int]
    answer: int
    checked: Dict[int, int]
    reward: int
    issueTime: float
    endTime: float
    isEscaped: bool
    criminal: int
    rewardPerSys: int
    techLevel: int
    activeShip: NotRequired[SerializedShipInstanceUnion]


class SerializedEscapedBounty(SerializedBounty):
    respawnTime: float


SerializedBountyUnion = Union[SerializedBounty, SerializedEscapedBounty]
