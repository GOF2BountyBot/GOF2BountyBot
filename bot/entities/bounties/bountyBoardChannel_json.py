from typing import Dict, TypedDict

class SerializedBountyBoardChannel(TypedDict):
    listings: Dict[int, int]
    division: int
    channel: int
    noBountiesMsg: int
    escapedBountiesMsg: int
    