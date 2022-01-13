from typing import TYPE_CHECKING, Any, Coroutine
if TYPE_CHECKING:
    from ....users import basedUser
from .. import gameItem
from abc import abstractmethod
from .... import lib, botState
from discord import Message
from typing import Callable, List


class ToolItem(gameItem.GameItem):
    """An item that has a function of some kind.
    Intended to be very generic at this level of implementation.
    """

    def __init__(self, name : str, aliases : List[str], value : int = 0, wiki : str = "",
            manufacturer : str = "", icon : str = "", emoji : lib.emojis.BasedEmoji = lib.emojis.BasedEmoji.EMPTY,
            techLevel : int = -1, builtIn : bool = False, autoUse: bool = False):
        """
        :param str name: The name of the item. Must be unique. (a model number is a good starting point)
        :param list[str] aliases: A list of alternative names this item may be referred to by.
        :param int value: The number of credits that this item can be bought/sold for at a shop. (Default 0)
        :param str wiki: A web page that is displayed as the wiki page for this item. (Default "")
        :param str manufacturer: The name of the manufacturer of this item (Default "")
        :param str icon: A URL pointing to an image to use for this item's icon (Default "")
        :param lib.emojis.BasedEmoji emoji: The emoji to use for this item's small icon (Default lib.emojis.BasedEmoji.EMPTY)
        :param int techLevel: A rating from 1 to 10 of this item's technical advancement. Used as a measure for its
                                effectiveness compared to other items of the same type (Default -1)
        :param bool builtIn: Whether this is a BountyBot standard item (loaded in from bbData) or a custom spawned
                                item (Default False)
        :param bool autoUse: Whether use of this item should be automatically triggered upon entering a user's hangar
                                (Default False)
        """
        super().__init__(name, aliases, value=value, wiki=wiki, manufacturer=manufacturer, icon=icon, emoji=emoji,
                            techLevel=techLevel, builtIn=builtIn)
        self.autoUse = autoUse


    @abstractmethod
    async def use(self, *args, **kwargs):
        """This item's behaviour function. Intended to be very generic at this level of implementation.
        """
        pass


    @abstractmethod
    async def userFriendlyUse(self, message: Message, argsStr: str, *args, **kwargs) -> str:
        """A version of self.use intended to be called by users, where exceptions are never thrown in the case of
        user error, and results strings are always returned.

        :param Message message: The discord message that triggered this tool use
        :param str argsStr: A potentially empty string of arguments for use, probably extracted from message
        :return: A user-friendly message summarising the result of the tool use.
        :rtype: str
        """
        pass


    @abstractmethod
    def statsStringShort(self) -> str:
        """Summarise all the statistics and functionality of this item as a string.

        :return: A string summarising the statistics and functionality of this item
        :rtype: str
        """
        return "*No effect*"


    def statsStringLong(self) -> str:
        """Summarise all the statistics and functionality of this item as a string.

        :return: A string summarising the statistics and functionality of this item
        :rtype: str
        """
        return self.statsStringShort()


    @abstractmethod
    def toDict(self, **kwargs) -> dict:
        """Serialize this tool into dictionary format.
        This step of implementation adds a 'type' string indicating the name of this tool's subclass.

        :param bool saveType: When true, include the string name of the object type in the output.
        :return: The default gameItem toDict implementation, with an added 'type' field
        :rtype: dict
        """
        data = super().toDict(**kwargs)
        data["autoUse"] = self.autoUse
        return data


def singleUse(func: Callable) -> Callable:
    """Decorator to apply to ToolItem use methods. The tool becomes single use, automatically removing itself
    from callingBUsers inactiveTools after use.
    """
    async def inner(self: ToolItem, *args, callingBUser: "basedUser.BasedUser" = None, **kwargs):
        if callingBUser is None:
            raise ValueError("Missing required argument: callingBUser")
        result = await func(self, *args, callingBUser=callingBUser, **kwargs)
        if self in callingBUser.inactiveTools:
            callingBUser.inactiveTools.removeItem(self)
        return result

    return inner


def userFriendlySingleUse(func: Callable) -> Callable:
    """Decorator to apply to ToolItem user friendly use methods. The tool becomes single use, automatically removing itself
    from calling user's inactiveTools after use.
    """
    async def inner(self: ToolItem, message: Message, *args, **kwargs):
        callingBUser = botState.usersDB.getOrAddID(message.author.id)
        result = await func(self, message, *args, **kwargs)
        if self in callingBUser.inactiveTools:
            callingBUser.inactiveTools.removeItem(self)
        return result

    return inner
