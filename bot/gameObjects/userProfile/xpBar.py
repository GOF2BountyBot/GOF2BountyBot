from ...baseClasses.serializable import SerializesToJson, JsonType
from ...cfg import bbData
from ... import lib
import os
from os.path import join

class XPBarFill(SerializesToJson):
    def __init__(self, name: str, path: str, designer: str, wiki: str = ""):
        self.name = name
        self.path = path
        self.designer = designer
        self.wiki = wiki
        self.hasWiki = wiki != ""

    
    def _updateItemMETA(self, **kwargs):
        lib.jsonHandler.writeJSON(join(self.path, "META.json"), self.serialize(**kwargs), prettyPrint=True)

    
    def serialize(self, **kwargs) -> JsonType:
        data = {"name": self.name, "designer": self.designer}
        if self.hasWiki:
            data["wiki"] = self.wiki
        # TODO: I can't figure out what's going on here. Apparently Dict[str, str] isn't primative!?
        return data # type: ignore[reportGeneralTypeIssues]


    @classmethod
    def deserialize(cls, data: dict, **kwargs):
        if data["name"] in bbData.builtInXPBars:
            return bbData.builtInXPBars[data["name"]]
        return XPBarFill(**cls._makeDefaults(data))
