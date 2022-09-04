from __future__ import annotations
from typing import TypedDict, cast
from ..baseClasses.serializable import SerializesToSchema
from ..baseClasses.simpleHash import simpleHash

class SerializedItemDiscount(TypedDict):
    mult: float
    desc: str

'https://stackoverflow.com/a/53519136'
@simpleHash
class ItemDiscount(SerializesToSchema[SerializedItemDiscount]):
    """A temporary modification to an item's value, potentially increasing or decreasing it,
    accompanied by a short description of the discount.
    ItemDiscount comparison operators directly compare multiplier attributes. This allows for sorting a list
    of ItemDiscount instances by the discount that they offer.

    :var mult: Scalar to multiply the discounted item's value by. E.g 0.5 to decrease the item's value (discount) by 50%
    :vartype mult: float
    :var desc: A short description of the discount.
    :vartype desc: str
    """
    def __init__(self, mult: float, desc: str):
        """
        :param float mult: Scalar to multiply the discounted item's value by. E.g 0.5 to decrease the item's value (discount) by 50%
        :param str desc: A short description of the discount.
        """
        self.mult = mult
        self.desc = desc


    def __eq__(self, o: ItemDiscount) -> bool:
        if not isinstance(o, ItemDiscount):
            raise TypeError(f"Cannot compare {ItemDiscount.__name__} to {type(o).__name__}")
        return self.mult == o.mult


    def __ne__(self, o: ItemDiscount) -> bool:
        if not isinstance(o, ItemDiscount):
            raise TypeError(f"Cannot compare {ItemDiscount.__name__} to {type(o).__name__}")
        return self.mult != o.mult


    def __lt__(self, o: ItemDiscount) -> bool:
        if not isinstance(o, ItemDiscount):
            raise TypeError(f"Cannot compare {ItemDiscount.__name__} to {type(o).__name__}")
        return self.mult > o.mult


    def __gt__(self, o: ItemDiscount) -> bool:
        if not isinstance(o, ItemDiscount):
            raise TypeError(f"Cannot compare {ItemDiscount.__name__} to {type(o).__name__}")
        return self.mult < o.mult


    def __le__(self, o: ItemDiscount) -> bool:
        if not isinstance(o, ItemDiscount):
            raise TypeError(f"Cannot compare {ItemDiscount.__name__} to {type(o).__name__}")
        return self.mult >= o.mult


    def __ge__(self, o: ItemDiscount) -> bool:
        if not isinstance(o, ItemDiscount):
            raise TypeError(f"Cannot compare {ItemDiscount.__name__} to {type(o).__name__}")
        return self.mult <= o.mult


    def serialize(self, **kwargs) -> SerializedItemDiscount:
        # Casting so I can add the new fields
        data = cast(SerializedItemDiscount, super().serialize(**kwargs))
        data["mult"] = self.mult
        data["desc"] = self.desc
        return data


    @classmethod
    def deserialize(cls, data: SerializedItemDiscount, **kwargs) -> ItemDiscount:
        return ItemDiscount(data["mult"], data["desc"])