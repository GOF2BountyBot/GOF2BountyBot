from .logging import Logger
from aiohttp import ClientSession
from datetime import datetime, timedelta
from github import Github
from github.Repository import Repository
from typing import Optional, cast
from enum import Enum

from typing import TYPE_CHECKING, cast
if TYPE_CHECKING:
    from .databases import userDB, guildDB, reactionMenuDB
    from .scheduling import timedTask, timedTaskHeap
    from . import logging
    from .client import BasedClient

class ShutDownState(Enum):
    restart = 0
    shutdown = 1
    update = 2


client = cast("BasedClient", None)
shutdown = ShutDownState.restart
httpClient: ClientSession = None
githubClient = cast(Github, None)
githubRepo = cast(Repository, None)

usersDB = cast("userDB.UserDB", None)
guildsDB = cast("guildDB.GuildDB", None)
reactionMenusDB = cast("reactionMenuDB.ReactionMenuDB", None)

shopRefreshTT = cast("timedTask.TimedTask", None)

taskScheduler = cast("timedTaskHeap.TimedTaskHeap", None)
logger = cast("logging.Logger", None)

dbSaveTT = cast("timedTask.TimedTask", None)
updatesCheckTT = cast("timedTask.TimedTask", None)

temperatureDecayTT = cast("timedTask.TimedTask", None)

# Scheduling overrides
newBountyFixedDeltaChanged = False


# Names of ships currently being rendered
currentRenders = []

# timedelta representing the system's offset from UTC time
utcOffset: timedelta = None

# The time at which $cmd_drink_premium can be used next. None if no cooldown as been set
premiumCooldownEnd: Optional[datetime] = None
