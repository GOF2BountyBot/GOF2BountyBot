from .logging import Logger
from aiohttp import ClientSession
from datetime import datetime, timedelta
from github import Github
from github.Repository import Repository
from typing import Optional, cast
from datetime import datetime

class ShutDownState:
    restart = 0
    shutdown = 1
    update = 2

client = None # type: ignore[var-annotated]
shutdown = ShutDownState.restart
httpClient: ClientSession = None
githubClient = cast(Github, None)
githubRepo = cast(Repository, None)

usersDB = None
guildsDB = None
reactionMenusDB = None

shopRefreshTT = None

taskScheduler = None
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


# The time at which $cmd_drink_premium can be used next. None if no cooldown as been set
premiumCooldownEnd: Optional[datetime] = None
