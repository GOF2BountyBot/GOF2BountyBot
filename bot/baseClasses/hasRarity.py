from typing import TypedDict

class SerializedWithRarity(TypedDict):
    """HasRarityMixin does not require the type to be serializable, but I'm including this here to help write contracts for serializable items with rarities
    """
    rarityLevel: int

class HasRarityMixin:
    """A mixin that simply ensures the existence of the `rarityLevel` attribute.
    """

    def __init__(self, rarityLevel: int, *args, **kwargs):
        self.rarityLevel = rarityLevel
        super().__init__(*args, **kwargs)
