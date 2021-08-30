from typing import Union, TYPE_CHECKING
from .logging import Logger
from aiohttp import ClientSession
from datetime import timedelta
if TYPE_CHECKING:
    from .databases import userDB, guildDB, reactionMenuDB

class ShutDownState:
    restart = 0
    shutdown = 1
    update = 2

client = None # type: ignore[var-annotated]
shutdown = ShutDownState.restart
httpClient: Union[ClientSession, None] = None

usersDB: Union["userDB.UserDB", None] = None
guildsDB: Union["guildDB.GuildDB", None] = None
reactionMenusDB: Union["reactionMenuDB.ReactionMenuDB", None] = None

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
