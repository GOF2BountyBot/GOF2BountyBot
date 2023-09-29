from typing import Any, TypeVar
from sqlalchemy.orm import DeclarativeBase, Mapped

from .embedFillable import EmbedFillableMixin, embedField
from ..cfg import cfg
from ..lib.sql import EmbedFillableSqlTableMeta
from .hasRarity_json import SerializedWithRarity
from .serializable import SerializesToSchema


class Base(DeclarativeBase): pass


TSchema = TypeVar("TSchema", bound=SerializedWithRarity)


class HasRarityMixin(Base, EmbedFillableMixin, SerializesToSchema[TSchema], metaclass=EmbedFillableSqlTableMeta):
    """A mixin that simply ensures the existence of the `rarityLevel` column.
    Also comes with EmbedFillableMixin, and `rarityLevel` as a field.
    """
    rarityLevel: Mapped[int]

    def __init__(self, rarityLevel: int, *args, **kwargs):
        self.rarityLevel = rarityLevel
        super().__init__(*args, **kwargs)

    
    @embedField("Rarity")
    @property
    def rarityLevelName(self):
        """The name of this object's rarity level
        """
        rarityName = cfg.itemRarities[self.rarityLevel]
        rarityEmoji = getattr(cfg.defaultEmojis, f'rarity_{rarityName}').sendable
        return f"{rarityEmoji} {rarityName.title()}"
    

    async def serialize(self, **kwargs: Any) -> TSchema:
        data = await super().serialize()
        return {**data, "rarityLevel": self.rarityLevel}
