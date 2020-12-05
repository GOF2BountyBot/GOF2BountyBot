from ..commandsManager import HeirarchicalCommandsDB
from ..cfg import cfg
import importlib

commandsDB = HeirarchicalCommandsDB.HeirarchicalCommandsDB(len(cfg.userAccessLevels))

def loadCommands():
    global commandsDB
    commandsDB.clear()

    for modName in cfg.includedCommandModules:
        try:
            importlib.import_module(("" if modName.startswith(".") else ".") + modName, "bot.commands")
        except ImportError:
            raise ImportError("Unrecognised commands module in cfg.includedCommandModules. Please ensure the file exists, and spelling/capitalization are correct: '" + modName + "'")
    
    return commandsDB