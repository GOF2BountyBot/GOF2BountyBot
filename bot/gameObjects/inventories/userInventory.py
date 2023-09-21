from .inventoryBase import Inventory
from typing import TYPE_CHECKING, Generic, TypeVar
if TYPE_CHECKING:
    from ...entities.user import basedUser
from typing import Type, Union
from ..items.tools import toolItem
import asyncio

# Used to allow for inventory deserializing without triggering autoUse
class USER_PLACEHOLDER:
    pass


TItemType = TypeVar("TItemType", bound=toolItem.ToolItem)
TSerializedItemType = TypeVar("TSerializedItemType", bound=toolItem.SerializedToolItemUnion)

class UserToolInventory(Inventory[TItemType, TSerializedItemType], Generic[TItemType, TSerializedItemType]):
    """A tool inventory for use by users.
    This inventory type will automatically schedule a tool's use coroutine upon being added to the inventory,
    but only if added through `addItem`, and only if the tool has `autoUse` set.
    """

    def __init__(self, owningBUser: Union["basedUser.BasedUser", Type[USER_PLACEHOLDER]],
                    itemType: Type[TItemType] = toolItem.ToolItem):
        super().__init__(itemType)
        self.owningBUser = owningBUser


    def addItem(self, item: TItemType, quantity: int = 1):
        super().addItem(item, quantity=quantity)
        if item.autoUse and self.owningBUser is not USER_PLACEHOLDER:
            # TODO: schedule this with logging with lib.discordUtil
            asyncio.create_task(item.use(callingBUser=self.owningBUser))
