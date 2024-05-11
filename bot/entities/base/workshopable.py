from typing import Any, Optional

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property

from ...lib.sql import EmbedFillableSerializableSqlTableMeta
from ...baseClasses.embedFillable import EmbedFillableMixin, embedTitle, embedField
from ...lib.discordUtil import ZWSP
from ...serialization.serializable import SqlSerializableMixin, JsonSchema


class Base(DeclarativeBase):
    pass


json = JsonSchema()
class Workshopable(Base, EmbedFillableMixin, SqlSerializableMixin, metaclass=EmbedFillableSerializableSqlTableMeta):
    _jsonSchema = json
    name: Mapped[str] = mapped_column()
    json.field(name)

    workshopListingId: Mapped[int] = mapped_column() # = mapped_column(ForeignKey(TableNames.WorkshopListing))
    json.field(workshopListingId)

    def __init__(self, name: Optional[str] = None, workshopListingId: Optional[int] = None, **kw: Any):
        super().__init__(name=name, workshopListingId=workshopListingId, **kw)


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
