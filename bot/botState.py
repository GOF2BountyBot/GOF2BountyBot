from datetime import datetime, timedelta
from typing import List, Optional, cast
from enum import Enum

from typing import TYPE_CHECKING, cast
if TYPE_CHECKING:
    from bot.scheduling import timedTask
    from bot.client import BasedClient

class ShutDownState(Enum):
    restart = 0
    shutdown = 1
    update = 2


client = cast("BasedClient", None)

shopRefreshTT = cast("timedTask.TimedTask", None)

dbSaveTT = cast("timedTask.TimedTask", None)
updatesCheckTT = cast("timedTask.TimedTask", None)

temperatureDecayTT = cast("timedTask.TimedTask", None)

# Scheduling overrides
newBountyFixedDeltaChanged = False


# Names of ships currently being rendered
currentRenders: List[str] = []

# timedelta representing the system's offset from UTC time
utcOffset = cast(timedelta, None)

# The time at which $cmd_drink_premium can be used next. None if no cooldown as been set
premiumCooldownEnd: Optional[datetime] = None
