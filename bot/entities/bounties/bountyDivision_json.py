from typing import Dict, List, TypedDict
from typing_extensions import NotRequired

from .bounty_json import SerializedBounty, SerializedEscapedBounty
from .bountyBoardChannel_json import SerializedBountyBoardChannel


class SerializedBountyDivision(TypedDict):
    temperature: float
    minLevel: int
    maxLevel: int
    bounties: Dict[int, List[SerializedBounty]]
    escapedBounties: Dict[int, List[SerializedEscapedBounty]]
    bountyBoardChannel: NotRequired[SerializedBountyBoardChannel]
