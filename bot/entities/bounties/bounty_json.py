

from typing import Dict, List, TypedDict, Union
from typing_extensions import NotRequired

from .criminal_json import SerializedCriminalUnion
from ..items.ship_json import SerializedShipUnion


class SerializedBounty(TypedDict):
    faction: str
    route: List[str]
    answer: str
    checked: Dict[str, int]
    reward: int
    issueTime: float
    endTime: float
    isEscaped: bool
    criminal: SerializedCriminalUnion
    rewardPerSys: int
    techLevel: int
    activeShip: NotRequired[SerializedShipUnion]


class SerializedEscapedBounty(SerializedBounty):
    respawnTime: float


SerializedBountyUnion = Union[SerializedBounty, SerializedEscapedBounty]
