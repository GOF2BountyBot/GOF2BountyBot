from typing import TypedDict

class SerializedValueAugment(TypedDict):
    """The serialized form does not include the augment id or listing id.
    It's assumed that a serialized value augment will never be used outside of the context of a serialized inventory listing.
    """
    multiplier: float
    description: str
