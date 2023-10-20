from typing import TypedDict

class SerializedWithRarity(TypedDict):
    """HasRarityMixin does not require the type to be serializable, but I'm
    including this here to help write contracts for serializable items with rarities
    """
    rarityLevel: int
