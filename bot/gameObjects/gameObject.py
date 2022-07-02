from ..baseClasses.serializable import SerializesToJson

class LoadedObject(SerializesToJson):
    """ABC for objects that were loaded into the game from file.
    To allow for loading from config files, this must be serializable to JSON, and have a `builtIn` bool
    to indicate whether the object is BB official or custom.
    """
    def __init__(self, builtIn: bool = False):
        self.builtIn = builtIn
