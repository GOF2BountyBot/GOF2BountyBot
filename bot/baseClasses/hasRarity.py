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
    def rarityLevelStr(self) -> str:
        """The emoji, follow by the name, of this object's rarity level
        """
        return f"{self.rarityLevelEmoji} {self.rarityLevelName.title()}"
    

    @property
    def rarityLevelName(self) -> str:
        """The name of this object's rarity level, as defined in cfg
        """
        return cfg.itemRarities[self.rarityLevel]

        
    @property
    def rarityLevelEmoji(self) -> str:
        """The emoji for this object's rarity level, as defined in cfg
        """
        return getattr(cfg.defaultEmojis, f'rarity_{self.rarityLevelName}').sendable
    

    async def serialize(self, **kwargs: Any) -> TSchema:
        data = await super().serialize()
        data["rarityLevel"] = self.rarityLevel
        return data
