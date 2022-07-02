from ...baseClasses.serializable import Serializable
from ..itemDiscount import ItemDiscount
from ..items import gameItem
from typing import Generic, List, TypeVar

TItemType = TypeVar("TItemType", bound=gameItem.GameItem)

class InventoryListing(Serializable, Generic[TItemType]):
    """A listing representing an object and a quantity of that object stored.
    To ensure serializability, inventorylistings can only store serializable objects.

    serializable deserializing is not defined in the general case, so InventoryListing does
    not have a general case deserialize function.

    :var item: The item this inventory listing represents
    :var count: The quantity of item stored
    :vartype count: int
    """

    def __init__(self, item: TItemType, count: int = 0):
        """
        :param item: The item to store
        :param int quantity: The amount of item to store (Default 0)
        """
        if not isinstance(item, gameItem.GameItem):
            raise TypeError("InventoryListing can only store serializables to ensure serializability. Given: " \
                            + type(item).__name__)
        self.item = item
        self.count = count


    def increaseCount(self, numIncrease: int):
        """Increase the number of this item stored in the listing

        :param int numIncrease: The amount to increment this listing's count by
        """
        self.count += numIncrease


    def decreaseCount(self, numDecrease: int):
        """Decrease the number of this item stored in the listing

        :param int numDecrease: The amount to decrement this listing's count by
        :raise ValueError: When attempting to decrease the listing by more than what is currently stored
        """
        if self.count < numDecrease:
            raise ValueError("INVLIS_DECRCOUNT_NEG: Attempted to decreaseCount into a negative total: " \
                                + str(self.count) + " - " + str(numDecrease))
        self.count -= numDecrease


    def getItem(self):
        """Get the object stored in this listing

        :return: the object that this listing counts
        """
        return self.item


    def storesItem(self, otherItem: TItemType) -> bool:
        """Decide whether this inventory listing stores the given object

        :return: True if otherItem is the same object as the one stored in the listing, down to memory location.
                    False otherwise
        :rtype: bool
        """
        return self.item is otherItem


    def serialize(self, **kwargs) -> dict:
        """Return a dictionary description of this inventory listing.

        :return: A dictionary identifying the object stored, and the amount
        :rtype: int
        """
        return {"item": self.item.serialize(**kwargs), "count": self.count}


    @classmethod
    def deserialize(cls, listingDict: dict, **kwargs):
        raise NotImplementedError("Cannot deserialize on InventoryListing in the general case. " \
                                    + "Instead instance InventoryListing with your deserialized item object.")


class DiscountableItemListing(InventoryListing[TItemType]):
    """An item listing that also stores a max-sorted list of single-use value modifications.
    A single value modification applies to a single instance of an item.
    """
    def __init__(self, item: TItemType, count: int = 0):
        """
        :param item: The item to store
        :param int quantity: The amount of item to store (Default 0)
        """
        super().__init__(item, count=count)
        self.discounts: List[ItemDiscount] = []


    def pushDiscount(self, discount: ItemDiscount):
        self.discounts.append(discount)
        self.discounts.sort(reverse=True) # reversed to give max-sorting - the biggest discount will be first


    def popDiscount(self) -> ItemDiscount:
        return self.discounts.pop(0)


    def serialize(self, **kwargs) -> dict:
        data = super().serialize(**kwargs)
        if self.discounts:
            data["discounts"] = [discount.serialize(**kwargs) for discount in self.discounts]
        return data
