from . import toolItem
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ....users import basedUser
from .... import lib, botState
from ....cfg import cfg
from discord import Message, User, Client, MessageType, File, TextChannel, Embed, Colour
from typing import List, cast
from .. import gameItem
from random import randint
from PIL import Image
from io import BytesIO

SNOWBALL_ICON = "https://cdn.discordapp.com/attachments/700683544103747594/924100261046259742/Snowball_PNG_Clipart.png"

@gameItem.spawnableItem
class ThrowSnowballTool(toolItem.ToolItem):
    """A tool that lets the user choose another user to throw a snowball at. Renders their profile picture
    with a snowball layered over the top.
    """

    def __init__(self, name : str, aliases : List[str] = [], value : int = 0, wiki : str = "",
            manufacturer : str = "", icon : str = SNOWBALL_ICON, emoji : lib.emojis.BasedEmoji = None,
            techLevel : int = -1, builtIn : bool = False, autoUse: bool = False):
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
        :param bool autoUse: Ignored. This is always False
        """
        super().__init__(name, aliases, value=value, wiki=wiki, manufacturer=manufacturer, icon=icon,
                            emoji=lib.emojis.BasedEmoji(id=924100293925412894) if emoji is None else emoji,
                            techLevel=techLevel, builtIn=builtIn, autoUse=False)


    async def use(self, callingBUser: "basedUser.BasedUser" = None, *args, **kwargs):
        """This tool can only be used from userFriendlyUse, as it must be interactive.

        :raise NotImplementedError: always
        """
        raise NotImplementedError("This tool can only be used from userFriendlyUse, as it must be interactive")


    @toolItem.userFriendlySingleUse
    async def userFriendlyUse(self, message : Message, *args, **kwargs) -> str:
        """Pick a user, and throw a snowball at them by rendering a snowball image over their profile

        :param Message message: The discord message that triggered this tool use
        :return: A user-friendly message summarising the result of the tool use.
        :rtype: str
        """
        pickMsg = await message.reply("Pick your target! **Reply** to this message, pinging one victim, within 60s.")

        def targetCheck(m: Message) -> bool:
            return m.type == MessageType.default and m.reference is not None and m.reference.message_id == pickMsg.id and len(m.mentions) == 1

        targetPickedMsg: Message = await botState.client.wait_for("message", check=targetCheck, timeout=60)
        targetUser: User = targetPickedMsg.mentions[0]

        profileAsset = targetUser.avatar_url_as(size=256, format="png")
        assetBytes = BytesIO()
        # targetProfile = Image.frombytes("RGBA", (256, 256), await profileAsset.read())
        await profileAsset.save(assetBytes, seek_begin=True)
        assetBytes.seek(0)
        targetProfile = Image.open(assetBytes)

        overlay = Image.open(f"snowballs/{randint(0,5)}.png")
        result = Image.alpha_composite(targetProfile, overlay)

        resultBytes = BytesIO()
        result.save(resultBytes, "PNG")
        resultBytes.seek(0)
        
        splatEmbed = Embed()
        splatEmbed.colour = Colour.random()
        splatEmbed.set_image(url="attachment://splat.png")

        await cast(TextChannel, message.channel).send(embed=splatEmbed, file=File(resultBytes, filename="splat.png"))

        assetBytes.close()
        targetProfile.close()
        overlay.close()
        result.close()
        resultBytes.close()

        return f"{message.author.display_name} threw a snowball at {targetUser.display_name}!"


    def statsStringShort(self) -> str:
        """Summarise all the statistics and functionality of this item as a string.

        :return: A string summarising the statistics and functionality of this item
        :rtype: str
        """
        return f"*{self.value} credits*"


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


    @classmethod
    def fromDict(cls, data: dict, **kwargs) -> dict:
        """Deserialize a CreditsTool from dictionary format.

        :return: A new CreditsTool as described by data
        :rtype: CreditsTool
        """
        return cls(**cls._makeDefaults(data, ignores=("type","emoji")))
