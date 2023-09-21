from os.path import join

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ...baseClasses.serializable import SerializesToSchema
from ...cfg import bbData
from ... import lib
from ...baseClasses.embedFillable import EmbedFillableMixin, embedImageFile
from ..base.workshopable import Workshopable
from .xpBarFill_json import SerializedXPBarFill


class Base(DeclarativeBase):
    pass


class XPBarFill(Workshopable, EmbedFillableMixin, SerializesToSchema[SerializedXPBarFill]):
    id: Mapped[int] = mapped_column(primary_key=True)
    imagePath: Mapped[str]

    @embedImageFile
    @property
    def embedImage(self): return self.imagePath

    
    async def _updateItemMETA(self, **kwargs):
        lib.jsonHandler.writeJSON(join(self.imagePath, "META.json"),
                                    # TODO: SerializedXPBarFill is incompatible with JsonType
                                    await self.serialize(**kwargs), # type: ignore[reportGeneralTypeIssues]
                                    prettyPrint=True)

    
    # async def serialize(self, **kwargs) -> SerializedXPBarFill:
    #     data = await super().serialize(**kwargs)
    #     return data


    @classmethod
    def deserialize(cls, data: SerializedXPBarFill, **kwargs):
        if (not data.get("fromWorkshop", False)) and data["name"] in bbData.builtInXPBars:
            return bbData.builtInXPBars[data["name"]]
        return XPBarFill(**cls._makeDefaults(data))
