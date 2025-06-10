from typing_extensions import TypedDict
from bot.baseClasses.embedFillable import EmbedFillableMixin, embedField
from bot.cfg import cfg

class SerializedWithRarity(TypedDict):
    """HasRarityMixin does not require the type to be serializable, but I'm including this here to help write contracts for serializable items with rarities
    """
    rarityLevel: int

class HasRarityMixin(EmbedFillableMixin):
    """A mixin that simply ensures the existence of the `rarityLevel` attribute.
    Also comes with EmbedFillableMixin, and `rarityLevel` as a field.
    """
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
