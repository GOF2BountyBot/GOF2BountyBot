from typing import TYPE_CHECKING, Coroutine, Protocol, TypeVar, Union, cast, Any
if TYPE_CHECKING:
    from bot.users import basedUser

from bot.gameObjects.items import gameItem
from abc import abstractmethod
from bot import lib
from discord import Interaction
from typing import List
from bot.baseClasses.serializable import SerializesToSchema
from bot.baseClasses.embedFillable import EmbedFillableMixin, embedField


class SerializedToolItem(gameItem.CustomSerializedGameItem):
    autoUse: bool

class TypedSerializedToolItem(SerializedToolItem, gameItem.TypedCustomSerializedGameItem): pass

SerializedToolItemUnion = Union[SerializedToolItem, TypedSerializedToolItem]

class UseCallbackType(Protocol):
    # Ignoring here because methods need a self for the class instance
    def __call__(cbSelf, self, *args, **kwargs) -> Coroutine[Any, Any, bool]: ... # type: ignore[reportSelfClsParameterName]

class UserFriendlyUseCallbackType(Protocol):
    # Ignoring here because methods need a self for the class instance
    def __call__(cbSelf, self, interaction: Interaction, respond: bool, followup: bool, *args, **kwargs) -> Coroutine[Any, Any, bool]: ... # type: ignore[reportSelfClsParameterName]


class ToolItem(gameItem.GameItem, EmbedFillableMixin, SerializesToSchema[SerializedToolItemUnion]):
    """An item that has a function of some kind.
    Intended to be very generic at this level of implementation.
    """

    def __init__(self, name: str, aliases: List[str], value: int = 0, wiki: str = "",
            manufacturer: str = "", icon: str = "", emoji: lib.emojis.BasedEmoji = lib.emojis.BasedEmoji.EMPTY,
            techLevel: int = -1, builtIn: bool = False, autoUse: bool = False):
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

    
    @embedField("Applies on Pickup", hideWhenNone=True)
    def formattedAutoUse(self): return "This item will `/use` automatically when it enters your inventory" if self.autoUse else None


    @abstractmethod
    async def use(self, *args, **kwargs) -> bool:
        """This item's behaviour function. Intended to be very generic at this level of implementation.
        """
        pass


    @abstractmethod
    async def userFriendlyUse(self, interaction: Interaction, respond: bool, followup: bool, *args, **kwargs) -> bool:
        """A version of self.use intended to be called by users, where exceptions are never thrown in the case of
        user error, and results strings are always returned.

        `respond` and `followup` are mutually exclusive.
        If both are `False`, then messages should be sent to `interaction.channel`.

        :param Interaction interaction: The discord interaction that triggered this tool use
        :param bool respond: True if messages should be sent as responses to `interaction`
        :param bool followup: True if messages should be sent as followups to `interaction`
        :returns: Whether or not the use was successful
        :rtype: bool
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


    def serialize(self, **kwargs) -> SerializedToolItemUnion:
        """Serialize this tool into dictionary format.
        This step of implementation adds a 'type' string indicating the name of this tool's subclass.

        :param bool saveType: When true, include the string name of the object type in the output.
        :return: The default gameItem serialize implementation, with an added 'type' field
        :rtype: dict
        """
        # Casting here so I can add the new field
        data = cast(SerializedToolItemUnion, super().serialize(**kwargs))
        data["autoUse"] = self.autoUse
        return data


TUse = TypeVar("TUse", bound=UseCallbackType)
TUserFriendlyUse = TypeVar("TUserFriendlyUse", bound=UserFriendlyUseCallbackType)

def singleUse(func: TUse) -> TUse:
    """Decorator to apply to ToolItem use methods. The tool becomes single use, automatically removing itself
    from callingBUsers inactiveTools after use.

    The tool is only removed if userFriendlyUse succeeds - returns `True`.
    """
    async def inner(self: ToolItem, *args, callingBUser: "basedUser.BasedUser", **kwargs):
        if callingBUser is None:
            raise ValueError("Missing required argument: callingBUser")
        result = await func(self, *args, callingBUser=callingBUser, **kwargs)
        if result and self in callingBUser.inactiveTools:
            callingBUser.inactiveTools.removeItem(self)

    # TODO: Not sure why i need to cast here
    return cast(TUse, inner)


def userFriendlySingleUse(func: TUserFriendlyUse) -> TUserFriendlyUse:
    """Decorator to apply to ToolItem user friendly use methods. The tool becomes single use, automatically removing itself
    from calling user's inactiveTools after use.

    The tool is only removed if userFriendlyUse succeeds - returns `True`.
    """
    # TODO: placed here to avoid a circular import
    from bot import client

    async def inner(self: ToolItem, interaction: Interaction, respond: bool, followup: bool, *args, **kwargs):
        if not isinstance(interaction.client, client.BasedClient):
            raise TypeError(f"{userFriendlySingleUse.__name__} can only be applied interactions that are handled by a BasedClient")
            
        userExists = interaction.client.usersDB.idExists(interaction.user.id)
        callingBUser = interaction.client.usersDB.getUser(interaction.user.id) if userExists else None

        result = await func(self, interaction, respond, followup, *args, **kwargs)

        if result and callingBUser is not None and self in callingBUser.inactiveTools:
            callingBUser.inactiveTools.removeItem(self)

    # TODO: Not sure why i need to cast here
    return cast(TUserFriendlyUse, inner)
