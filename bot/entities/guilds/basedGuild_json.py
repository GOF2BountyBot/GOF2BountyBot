from typing import List, Optional, TypedDict, Dict

from ..bounties.bountyDivision_json import SerializedBountyDivision
from ..shops.guildShop import SerializedTechLeveledShop

class SerializedBasedGuild(TypedDict):
    id: int
    alertRoles: Dict[str, Optional[int]]
    bountiesDisabled: bool
    shopsDisabled: bool
    gameChannels: Dict[str, Optional[int]]
    activeRoleMenusCount: int
    divisions: List[SerializedBountyDivision]
    divisionShops: Dict[int, SerializedTechLeveledShop]
