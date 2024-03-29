from typing import Dict, List, TypedDict
from typing_extensions import NotRequired

from .bounty_json import SerializedActiveBounty, SerializedEscapedBounty
from .bountyBoardChannel_json import SerializedBountyBoardChannel


class SerializedBountyDivision(TypedDict):
    id: int
    tier: str
    guildId: int
    spawnAlertRoleId: NotRequired[int]
    temperature: float
    minLevel: int
    maxLevel: int
    bounties: Dict[int, List[SerializedActiveBounty]]
    escapedBounties: Dict[int, List[SerializedEscapedBounty]]
    bountyBoardChannel: NotRequired[SerializedBountyBoardChannel]
