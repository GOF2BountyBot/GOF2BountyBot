from typing import Any, Optional, TypeVar
from sqlalchemy.orm import DeclarativeBase, Mapped
from sqlalchemy.ext.hybrid import hybrid_property

from ...baseClasses.serializable import SerializesToSchema
from .workshopable_json import SerializedWorkshopableUnion, SerializedUserSubmittedWorkshopable, SerializedBuiltInWorkshopable
from ...lib.sql import EmbedFillableSqlTableMeta
from ...baseClasses.embedFillable import EmbedFillableMixin, embedTitle, embedField
from ...lib.discordUtil import ZWSP


class Base(DeclarativeBase):
    pass

TSchema = TypeVar("TSchema", bound=SerializedWorkshopableUnion)

class Workshopable(Base, EmbedFillableMixin, SerializesToSchema[TSchema], metaclass=EmbedFillableSqlTableMeta):
    name: Mapped[str]
    workshopListingId: Mapped[int]# = mapped_column(ForeignKey(TableNames.WorkshopListing))


    @hybrid_property
    def fromWorkshop(self):
        return self.workshopListingId != 0
    

    @embedTitle
    @property
    def formattedName(self): return self.name.title()


    @embedField(ZWSP, showLast=True, showInline=False)
    @property
    def formattedWorkshopListing(self) -> Optional[str]:
        return f"*Workshop listing #{self.workshopListingId}*" if self.fromWorkshop else None
    

    async def serialize(self, **kwargs: Any) -> TSchema:
        data = await super().serialize(**kwargs)

        if self.fromWorkshop:
            workshopData: SerializedUserSubmittedWorkshopable = {"name": self.name, "fromWorkshop": True, "workshopListingId": self.workshopListingId}
            data.update(workshopData) # type: ignore[reportGeneralTypeIssues]
        else:
            builtInData: SerializedBuiltInWorkshopable = {"name": self.name, "fromWorkshop": False}
            data.update(builtInData) # type: ignore[reportGeneralTypeIssues]
        
        return data
