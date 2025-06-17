from bot.gameObjects.items.tools import toolItem
from typing import TYPE_CHECKING, Optional
from discord import Guild, Interaction, Message, MessageType, Embed, Colour
from typing import List, cast
from random import randint
from PIL import Image
from io import BytesIO
import asyncio

if TYPE_CHECKING:
    from bot.users import basedUser
from bot.lib.discordUtil import ImageFile, interactionSend
from bot.lib.emojis import BasedEmoji
from bot.gameObjects.items import gameItem
from bot.cfg import cfg

SNOWBALL_ICON = "https://cdn.discordapp.com/attachments/700683544103747594/924100261046259742/Snowball_PNG_Clipart.png"

@gameItem.spawnableItem
class ThrowSnowballTool(toolItem.ToolItem):
    """A tool that lets the user choose another user to throw a snowball at. Renders their profile picture
    with a snowball layered over the top.
    """

    def __init__(self, name: str, aliases: List[str] = [], value: int = 0, wiki: str = "",
            manufacturer: str = "", icon: str = SNOWBALL_ICON, emoji: Optional[BasedEmoji] = None,
            techLevel: int = -1, builtIn: bool = False, autoUse: bool = False):
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
                            emoji=BasedEmoji(unicode="❄") if emoji is None else emoji, # TODO: BasedEmoji(id=924100293925412894)
                            techLevel=techLevel, builtIn=builtIn, autoUse=False)

    
    async def use(self, *, callingBUser: "basedUser.BasedUser", **kwargs) -> bool:
        """This tool can only be used from userFriendlyUse, as it must be interactive.
        :raise NotImplementedError: always
        """
        return False
        raise NotImplementedError("This tool can only be used from userFriendlyUse, as it must be interactive")


    @toolItem.userFriendlySingleUse
    async def userFriendlyUse(self, interaction: Interaction, respond: bool, followup: bool, *args, **kwargs) -> bool:
        """Pick a user, and throw a snowball at them by rendering a snowball image over their profile

        :param interaction Interaction: The discord interaction that triggered this tool use
        :returns: Whether or not the use was successful
        :rtype: bool
        """
        if interaction.guild is None:
            await interactionSend(interaction, respond, followup,
                                    f":x: The {self.name} can only be used from within a server!",
                                    ephemeral=True)
            return False
        
        pickMsg = await interactionSend(interaction, respond, followup,
                                        "Pick your target! **Reply** to this message, pinging one victim, within 60s.")
        if respond or followup:
            pickMsg = await interaction.original_response()
            respond, followup = False, False

        if not isinstance(pickMsg, Message): raise RuntimeError("Failed to fetch menu message")

        def targetCheck(m: Message) -> bool:
            # Casting here because the message must be a reply to one sent in the same channel as the message that triggered the use
            return      m.type == MessageType.default \
                    and m.reference is not None \
                    and m.reference.message_id == cast(Message, pickMsg).id \
                    and ((len(m.mentions) == 1 and m.mentions[0] == cast(Guild, interaction.guild).me)
                        or (len([u for u in m.mentions if u != cast(Guild, interaction.guild).me]) == 1))

        try:
            targetPickedMsg: Message = await interaction.client.wait_for("message", check=targetCheck, timeout=60)
        except asyncio.TimeoutError:
            await pickMsg.reply(":x: Out of time! Please try again.")
            return False

        if len(targetPickedMsg.mentions) != 1:
            targetUser = next(u for u in targetPickedMsg.mentions if u != interaction.guild.me)
        else:
            targetUser = targetPickedMsg.mentions[0]

        profileAsset = targetUser.display_avatar.with_size(256).with_format("png")
        with BytesIO() as assetBytes:
            await profileAsset.save(assetBytes, seek_begin=True)
            assetBytes.seek(0)

            targetProfile = Image.open(assetBytes)
            if targetProfile.mode != "RGBA":
                targetProfile = targetProfile.convert("RGBA")

            with Image.open(f"{cfg.paths.snowballImages}/{randint(0, cfg.numSnowballs - 1)}.png") as overlay:
                targetProfile.paste(overlay, (0, 0), overlay)

                with ImageFile(targetProfile, "splat.png") as resultFile:
                    splatEmbed = Embed()
                    splatEmbed.colour = Colour.random()
                    splatEmbed.set_image(url=f"attachment://{resultFile.fileName}")

                    await interactionSend(interaction, respond, followup,
                                            f"{interaction.user.display_name} threw a snowball at {targetUser.display_name}!",
                                            embed=splatEmbed, file=resultFile)
        
        return True


    def statsStringShort(self) -> str:
        """Summarise all the statistics and functionality of this item as a string.
        :return: A string summarising the statistics and functionality of this item
        :rtype: str
        """
        return f"*{self.value} credits*"


    @classmethod
    def deserialize(cls, data: toolItem.SerializedToolItemUnion, **kwargs) -> "ThrowSnowballTool":
        """Deserialize a CreditsTool from dictionary format.
        :return: A new CreditsTool as described by data
        :rtype: CreditsTool
        """
        return cls(**cls._makeDefaults(data, ignores=("type", "emoji")))
