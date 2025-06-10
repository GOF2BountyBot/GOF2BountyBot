from typing_extensions import NotRequired
from bot.baseClasses.serializable import SerializesToSchema
from bot.cfg import bbData
from bot import lib, botState
from os.path import join
from bot.baseClasses.embedFillable import EmbedFillableMixin, embedField, embedImageFile, embedTitle
from ..gameObject import LoadedObject, SerializedLoadedObject

class SerializedXPBarFill(SerializedLoadedObject):
    designer: str


class XPBarFill(LoadedObject, EmbedFillableMixin, SerializesToSchema[SerializedXPBarFill]):
    def __init__(self, name: str, path: str, designer: str, designerId: int, wiki: str = "", builtIn: bool = False):
        super().__init__(builtIn=builtIn, wiki=wiki, name=name)
        self._path = path
        self.designer = designer
        self.designerId = designerId
    
    @embedTitle
    @property
    def formattedName(self): return self.name.title()

    @embedField("Designed By")
    @property
    def formattedDesigner(self):
        user = botState.client.get_user(self.designerId)
        return self.designer if user is None else f"{user.name}#{user.discriminator}"

    @embedImageFile
    @property
    def path(self): return self._path

    
    def _updateItemMETA(self, **kwargs):
        lib.jsonHandler.writeJSON(join(self._path, "META.json"),
                                    # TODO: SerializedXPBarFill is incompatible with JsonType
                                    self.serialize(**kwargs), # type: ignore[reportGeneralTypeIssues]
                                    prettyPrint=True)

    
    def serialize(self, **kwargs) -> SerializedXPBarFill:
        data: SerializedXPBarFill = {"name": self.name, "designer": self.designer, "builtIn": self.builtIn}
        if self.hasWiki:
            data["wiki"] = self.wiki
        # TODO: I can't figure out what's going on here. Apparently Dict[str, str] isn't primative!?
        return data # type: ignore[reportGeneralTypeIssues]


    @classmethod
    def deserialize(cls, data: SerializedXPBarFill, **kwargs):
        if data.get("builtIn", False) and data["name"] in bbData.builtInXPBars:
            return bbData.builtInXPBars[data["name"]]
        return XPBarFill(**cls._makeDefaults(data))
