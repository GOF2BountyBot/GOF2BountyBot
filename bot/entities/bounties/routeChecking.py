from typing import Union

from enum import Enum
from dataclasses import dataclass

class RewardsMeta(Enum):
    """Binary flags representing special cases to apply to giving rewards for checking a bounty's route

    none: no flags
    prestige: user has since prestiged, so they dont get xp and their credits are shared to the other contributor(s)
    """
    NONE = 0b0
    USER_PRESTIGED = 0b1

    def __and__(self, other: Union[int, "RewardsMeta"]):
        if isinstance(other, RewardsMeta):
            return self.value & other.value
        else:
            return self.value & other

    
    def __or__(self, other: Union[int, "RewardsMeta"]):
        if isinstance(other, RewardsMeta):
            return self.value | other.value
        else:
            return self.value | other


@dataclass
class BountyUserRewards:
    reward: int
    checked: int
    won: bool
    xp: int
