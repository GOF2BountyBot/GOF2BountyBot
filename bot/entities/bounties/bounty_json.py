from typing import Dict, List, Optional, TypedDict, Union
from typing_extensions import NotRequired

from ..items.ship.shipInstance_json import SerializedShipInstanceUnion


class SerializedActiveBounty(TypedDict):
    faction: str
    route: List[int]
    answer: int
    checked: Dict[int, Optional[int]]
    reward: int
    issueTime: float
    endTime: float
    isEscaped: bool
    criminal: int
    rewardPerSys: int
    techLevel: int
    activeShip: NotRequired[SerializedShipInstanceUnion]


class SerializedEscapedBounty(SerializedActiveBounty):
    respawnTime: float


SerializedBountyUnion = Union[SerializedActiveBounty, SerializedEscapedBounty]
