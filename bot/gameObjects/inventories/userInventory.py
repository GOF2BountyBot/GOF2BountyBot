from .inventory import TypeRestrictedInventory
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...users import basedUser
from typing import Type, Union
from ..items.tools import toolItem
import asyncio

# Used to allow for inventory deserializing without triggering autoUse
class USER_PLACEHOLDER:
    pass

class UserToolInventory(TypeRestrictedInventory):
    """A tool inventory for use by users.
    This inventory type will automatically schedule a tool's use coroutine upon being added to the inventory,
    but only if added through `addItem`, and only if the tool has `autoUse` set.
    """

    def __init__(self, owningBUser: Union["basedUser.BasedUser", Type[USER_PLACEHOLDER]],
                    itemType: Type[toolItem.ToolItem] = toolItem.ToolItem):
        super().__init__(itemType)
        self.owningBUser = owningBUser


    def addItem(self, item: toolItem.ToolItem, quantity : int = 1):
        super().addItem(item, quantity=quantity)
        if item.autoUse and self.owningBUser is not USER_PLACEHOLDER:
            # TODO: schedule this with logging with lib.discordUtil
            asyncio.create_task(item.use(callingBUser=self.owningBUser))