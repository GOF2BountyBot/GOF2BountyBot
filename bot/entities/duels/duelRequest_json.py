from typing import TypedDict
from datetime import datetime

class SerializedDuelRequest(TypedDict):
    sourceUserId: int
    targetUserId: int
    stakes: int
    expiryTime: datetime
