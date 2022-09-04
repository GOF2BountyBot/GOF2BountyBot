from typing import TypedDict
from typing_extensions import NotRequired
from ...baseClasses.serializable import SerializesToSchema
from ...cfg import bbData
from ... import lib
from os.path import join

class SerializedXPBarFill(TypedDict):
    name: str
    designer: str
    wiki: NotRequired[str]


class XPBarFill(SerializesToSchema[SerializedXPBarFill]):
    def __init__(self, name: str, path: str, designer: str, wiki: str = ""):
        self.name = name
        self.path = path
        self.designer = designer
        self.wiki = wiki
        self.hasWiki = wiki != ""

    
    def _updateItemMETA(self, **kwargs):
        lib.jsonHandler.writeJSON(join(self.path, "META.json"),
                                    # TODO: SerializedXPBarFill is incompatible with JsonType
                                    self.serialize(**kwargs), # type: ignore[reportGeneralTypeIssues]
                                    prettyPrint=True)

    
    def serialize(self, **kwargs) -> SerializedXPBarFill:
        data = {"name": self.name, "designer": self.designer}
        if self.hasWiki:
            data["wiki"] = self.wiki
        # TODO: I can't figure out what's going on here. Apparently Dict[str, str] isn't primative!?
        return data # type: ignore[reportGeneralTypeIssues]


    @classmethod
    def deserialize(cls, data: SerializedXPBarFill, **kwargs):
        if data["name"] in bbData.builtInXPBars:
            return bbData.builtInXPBars[data["name"]]
        return XPBarFill(**cls._makeDefaults(data))
