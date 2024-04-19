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
MIN_PYTHON = (3, 7)
MAX_PYTHON = (3, 11)
if sys.version_info < MIN_PYTHON:
    sys.exit("Python %s.%s or later is required.\n" % MIN_PYTHON)

if sys.version_info > MAX_PYTHON:
    sys.exit("Python %s.%s or earlier is required.\n" % MAX_PYTHON)

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
