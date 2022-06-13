from . import toolItem
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ....users import basedUser
from .... import lib, botState
from ....cfg import cfg
from discord import Message
from typing import List
from .. import gameItem


@gameItem.spawnableItem
class CreditsTool(toolItem.ToolItem):
    """A slightly unnecessary tool that is supposed to add a number of credits to a user's account upon entering their hangar.
    """

    def __init__(self, name : str, aliases : List[str], value : int = 0, wiki : str = "",
            manufacturer : str = "", icon : str = cfg.moneyIcon, emoji : lib.emojis.BasedEmoji = None,
            techLevel : int = -1, builtIn : bool = False, autoUse: bool = True):
        """
        :param str name: The name of the item. Must be unique. (a model number is a good starting point)
        :param list[str] aliases: A list of alternative names this item may be referred to by.
        :param int value: The number of credits that this item can be bought/sold for at a shop. (Default 0)
        :param str wiki: A web page that is displayed as the wiki page for this item. (Default "")
        :param str manufacturer: The name of the manufacturer of this item (Default "")
        :param str icon: A URL pointing to an image to use for this item's icon (Default cfg.moneyIcon)
        :param lib.emojis.BasedEmoji emoji: The emoji to use for this item's small icon (Default cfg.defaultEmojis.money)
        :param int techLevel: A rating from 1 to 10 of this item's technical advancement. Used as a measure for its
                                effectiveness compared to other items of the same type (Default -1)
        :param bool builtIn: Whether this is a BountyBot standard item (loaded in from bbData) or a custom spawned
                                item (Default False)
        :param bool autoUse: Whether use of this item should be automatically triggered upon entering a user's hangar
                                (Default True)
        """
        super().__init__(name, aliases, value=value, wiki=wiki, manufacturer=manufacturer, icon=icon,
                            emoji=cfg.defaultEmojis.money if emoji is None else emoji,
                            techLevel=techLevel, builtIn=builtIn, autoUse=autoUse)


    @toolItem.singleUse
    async def use(self, callingBUser: "basedUser.BasedUser" = None, *args, **kwargs):
        """Add money to the calling user's account.
        """
        callingBUser.credits += self.value


    @toolItem.userFriendlySingleUse
    async def userFriendlyUse(self, message : Message, *args, **kwargs) -> str:
        """Add money to the calling user's account.
        :param Message message: The discord message that triggered this tool use
        :return: A user-friendly message summarising the result of the tool use.
        :rtype: str
        """
        callingBUser = botState.client.usersDB.getOrAddID(message.author.id)
        callingBUser.credits += self.value
        return f"You got {self.value} credits!"


    def statsStringShort(self) -> str:
        """Summarise all the statistics and functionality of this item as a string.
        :return: A string summarising the statistics and functionality of this item
        :rtype: str
        """
        return f"*{self.value} credits*"


    def serialize(self, **kwargs) -> dict:
        """Serialize this tool into dictionary format.
        This step of implementation adds a 'type' string indicating the name of this tool's subclass.
        :param bool saveType: When true, include the string name of the object type in the output.
        :return: The default gameItem serialize implementation, with an added 'type' field
        :rtype: dict
        """
        data = super().serialize(**kwargs)
        data["autoUse"] = self.autoUse
        return data


    @classmethod
    def deserialize(cls, data: dict, **kwargs) -> "CreditsTool":
        """Deserialize a CreditsTool from dictionary format.
        :return: A new CreditsTool as described by data
        :rtype: CreditsTool
        """
        return cls(**cls._makeDefaults(data, ignores=("type",)))
