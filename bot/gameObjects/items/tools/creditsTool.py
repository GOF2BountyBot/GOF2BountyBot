from bot.gameObjects.items.tools import toolItem
from typing import TYPE_CHECKING, Optional
from discord import Interaction
from typing import List

if TYPE_CHECKING:
    from bot.users import basedUser
from bot.lib.emojis import BasedEmoji
from bot.lib.discordUtil import interactionSend
from bot.cfg import cfg
from bot.gameObjects.items import gameItem
from bot.client import onboardInteractionBasedUser


@gameItem.spawnableItem
class CreditsTool(toolItem.ToolItem):
    """A slightly unnecessary tool that is supposed to add a number of credits to a user's account upon entering their hangar.
    """

    def __init__(self, name: str, aliases: List[str], value: int = 0, wiki: str = "",
            manufacturer: str = "", icon: str = cfg.moneyIcon, emoji: Optional[BasedEmoji] = None,
            techLevel: int = -1, builtIn: bool = False, autoUse: bool = True):
        """
        :param str name: The name of the item. Must be unique. (a model number is a good starting point)
        :param list[str] aliases: A list of alternative names this item may be referred to by.
        :param int value: The number of credits that this item can be bought/sold for at a shop. (Default 0)
        :param str wiki: A web page that is displayed as the wiki page for this item. (Default "")
        :param str manufacturer: The name of the manufacturer of this item (Default "")
        :param str icon: A URL pointing to an image to use for this item's icon (Default cfg.moneyIcon)
        :param BasedEmoji emoji: The emoji to use for this item's small icon (Default cfg.defaultEmojis.money)
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
    async def use(self, *args, callingBUser: "basedUser.BasedUser", **_) -> bool:
        """Add money to the calling user's account.
        """
        if not isinstance(callingBUser, "basedUser.BasedUser"): raise ValueError("Missing required kwarg: callingBUser")
        callingBUser.credits += self.value
        return True


    @toolItem.userFriendlySingleUse
    async def userFriendlyUse(self, interaction: Interaction, respond: bool, followup: bool, *args, **_) -> bool:
        """Add money to the calling user's account.

        :param interaction Interaction: The discord interaction that triggered this tool use
        :returns: Whether or not the use was successful
        :rtype: bool
        """
        callingBUser = onboardInteractionBasedUser(interaction)
        callingBUser.credits += self.value
        await interactionSend(interaction, respond, followup, f"You got {self.value} credits!")
        return True


    def statsStringShort(self) -> str:
        """Summarise all the statistics and functionality of this item as a string.
        :return: A string summarising the statistics and functionality of this item
        :rtype: str
        """
        return f"*{self.value} credits*"


    @classmethod
    def deserialize(cls, data: toolItem.SerializedToolItemUnion, **kwargs) -> "CreditsTool":
        """Deserialize a CreditsTool from dictionary format.
        :return: A new CreditsTool as described by data
        :rtype: CreditsTool
        """
        return cls(**cls._makeDefaults(data, ignores=("type",)))
