from typing import Union, TYPE_CHECKING, cast
from .logging import Logger
from aiohttp import ClientSession
from datetime import timedelta
if TYPE_CHECKING:
    from .databases import userDB, guildDB, reactionMenuDB
    from .scheduling import timedTask, timedTaskHeap

class ShutDownState:
    restart = 0
    shutdown = 1
    update = 2

client = None # type: ignore[var-annotated]
shutdown = ShutDownState.restart
httpClient = cast("ClientSession", None)

usersDB = cast("userDB.UserDB", None)
guildsDB = cast("guildDB.GuildDB", None)
reactionMenusDB = cast("reactionMenuDB.ReactionMenuDB", None)

shopRefreshTT = cast("timedTask.TimedTask", None)

taskScheduler = cast("timedTaskHeap.TimedTaskHeap", None)
logger: Logger = None

dbSaveTT = None
updatesCheckTT = None

temperatureDecayTT = None

# Scheduling overrides
newBountyFixedDeltaChanged = False


# Names of ships currently being rendered
currentRenders = []

# timedelta representing the system's offset from UTC time
utcOffset: timedelta = None
