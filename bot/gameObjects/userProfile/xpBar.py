from ...baseClasses.serializable import Serializable
from ...cfg import bbData
from ... import lib
import os
from os.path import join

class XPBarFill(Serializable):
    def __init__(self, name: str, path: str, designer: str, wiki: str = ""):
        self.name = name
        self.path = path
        self.designer = designer
        self.wiki = wiki
        self.hasWiki = wiki != ""

    
    def _updateItemMETA(self, **kwargs):
        lib.jsonHandler.writeJSON(join(self.path, "META.json"), self.serialize(**kwargs), prettyPrint=True)

    
    def serialize(self, **kwargs):
        data = {"name": self.name, "designer": self.designer}
        if self.hasWiki:
            data["wiki"] = self.wiki
        return data


    @classmethod
    def deserialize(cls, data: dict, **kwargs):
        if data["name"] in bbData.builtInXPBars:
            return bbData.builtInXPBars[data["name"]]
        return XPBarFill(**cls._makeDefaults(data))