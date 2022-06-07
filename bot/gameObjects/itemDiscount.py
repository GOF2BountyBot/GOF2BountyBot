from __future__ import annotations
from carica import ISerializable


class ItemDiscount(ISerializable):
    """A temporary modification to an item's value, potentially increasing or decreasing it,
    accompanied by a short description of the discount.
    ItemDiscount comparison operators directly compare multiplier attributes. This allows for sorting a list
    of ItemDiscount instances by the discount that they offer.

    :var mult: Scalar to multiply the discounted item's value by. E.g 0.5 to decrease the item's value (discount) by 50%
    :vartype mult: float
    :var desc: A short description of the discount.
    :vartype desc: str
    """
    def __init__(self, mult : float, desc : str):
        """
        :param float mult: Scalar to multiply the discounted item's value by. E.g 0.5 to decrease the item's value (discount) by 50%
        :param str desc: A short description of the discount.
        """
        self.mult = mult
        self.desc = desc


    def __eq__(self, o : ItemDiscount) -> bool:
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


    def toDict(self, **kwargs):
        data = super().toDict(**kwargs)
        data["mult"] = self.mult
        data["desc"] = self.desc
        return data


    @classmethod
    def fromDict(cls, data: dict, **kwargs) -> ItemDiscount:
        return ItemDiscount(data["mult"], data["desc"])