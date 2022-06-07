from carica import ISerializable
from ...cfg import bbData
from ... import lib
import os

class XPBarFill(ISerializable):
    def __init__(self, name: str, path: str, designer: str, wiki: str = ""):
        self.name = name
        self.path = path
        self.designer = designer
        self.wiki = wiki
        self.hasWiki = wiki != ""

    
    def _updateItemMETA(self, **kwargs):
        lib.jsonHandler.writeJSON(self.path + os.sep + "META.json", self.toDict(**kwargs), prettyPrint=True)

    
    def toDict(self, **kwargs):
        data = {"name": self.name, "designer": self.designer}
        if self.hasWiki:
            data["wiki"] = self.wiki
        return data


    @classmethod
    def fromDict(cls, data: dict, **kwargs):
        if data["name"] in bbData.builtInXPBars:
            return bbData.builtInXPBars[data["name"]]
        return XPBarFill(**cls._makeDefaults(data))