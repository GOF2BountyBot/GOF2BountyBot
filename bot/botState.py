from typing import List, TYPE_CHECKING, cast
if TYPE_CHECKING:
    from .databases import userDB, guildDB, reactionMenuDB
    from .scheduling import timedTask, timedTaskHeap
    from . import logging
    from aiohttp import ClientSession
    from datetime import timedelta

from aiohttp import ClientSession
from datetime import timedelta
from github import Github
from github.Repository import Repository
from typing import cast
from discord import Client # type: ignore[import]

class ShutDownState:
    restart = 0
    shutdown = 1
    update = 2

client = cast(Client, None)
shutdown = ShutDownState.restart
httpClient = cast("ClientSession", None)
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
currentRenders: List[str] = []

# timedelta representing the system's offset from UTC time
utcOffset = cast("timedelta", None)
