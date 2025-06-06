import sys

# Require python 3.7, because:
# - bbData gameObject DBs should be sorted by name to allow for alphabetized command parameter auto-completion.
#   This could have been done with an OrderedDict, but they have been optimized for reorder efficiency, which is not needed.
# Require python 3.11, because:
# - all serializable classes now have a serialized schema as a dataclass. 3.11 adds NotRequired, and Generic TypedDicts
# Require python 3.8, because:
# - The json serializable models implementation uses typing.get_origin and typing.get_args, which were added in 3.8
# Require below python 3.12 because:
# - The json serializable models implementation looks explicitly for a typing.Generic base class, it does not yet support class type parameter syntax
AT_LEAST_PYTHON = (3, 11, 0)
BELOW_PYTHON = (3, 12, 0)

hostPython = (sys.version_info.major, sys.version_info.minor, sys.version_info.micro)

if sys.version_info < AT_LEAST_PYTHON:
    sys.exit(f"BountyBot requires at least Python {'.'.join(str(i) for i in AT_LEAST_PYTHON)}. See main.py for more information.\nExiting.")

if not sys.version_info < BELOW_PYTHON:
    sys.exit(f"BountyBot requires a Python version below {'.'.join(str(i) for i in BELOW_PYTHON)}. See main.py for more information.\nExiting.")

from bot.cfg import cfg
import carica

# Load config if one is given
if len(sys.argv) > 1:
    carica.loadCfg(cfg, sys.argv[1])

cfg.validateConfig()
# TODO: Need to fix carica
cfg.developmentGuilds = [cfg.SerializableDiscordObject(i) for i in cfg.developmentGuilds]

# load and run bot
from bot import bot
status = bot.run()

# return exit status code for bot restarting
sys.exit(status)
