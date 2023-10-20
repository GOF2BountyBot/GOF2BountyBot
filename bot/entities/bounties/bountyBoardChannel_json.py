from typing import Dict, TypedDict

from .criminal_json import SerializedCriminal


class SerializedBountyBoardChannel(TypedDict):
    listings: Dict[int, SerializedCriminal]
    channel: int
    noBountiesMsg: int
    escapedBountiesMsg: int
    