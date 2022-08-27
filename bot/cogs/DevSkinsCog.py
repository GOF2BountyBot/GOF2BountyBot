from typing import List, cast

from discord import app_commands, Interaction
from discord.abc import Snowflake
from discord.app_commands import Range

from .. import client
from ..cfg import cfg
from ..cfg.cfg import basicAccessLevels
from ..interactions import basedCommand
from ..interactions.basedApp import BasedCog

PAINTBRUSH_ICON = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/twitter/282/paintbrush_1f58c-fe0f.png"

class DevSkinsCog(BasedCog):
    def __init__(self, bot: client.BasedClient, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="skins")
    @app_commands.command(name="add-skin",
                            description="Make the specified ship compatible with the specified skin")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_addSkin(self, interaction: Interaction, balance: Range[int, 1, ...], user_id: str = ""):
        """Make the specified ship compatible with the specified skin.
        """
        # verify a item was given
        if args == "":
            if isDM:
                prefix = cfg.defaultCommandPrefix
            else:
                prefix = botState.client.guildsDB.getGuild(message.guild.id).commandPrefix
            await message.reply(mention_author=False, content=":x: Please provide a ship! Example: `" + prefix + "ship Groza Mk II`")
            return

        if "+" in args:
            if len(args.split("+")) > 2:
                await message.reply(mention_author=False, content=":x: Please only provide one skin, with one `+`!")
                return
            args, skin = args.split("+")
        else:
            skin = ""

        # look up the ship object
        itemName = args.rstrip(" ").title()
        itemObj = None
        for ship in bbData.builtInShipData.values():
            shipObj = shipItem.Ship.deserialize(ship)
            if shipObj.isCalled(itemName):
                itemObj = shipObj

        # report unrecognised ship names
        if itemObj is None:
            if len(itemName) < 20:
                await message.reply(mention_author=False, content=":x: **" + itemName + "** is not in my database! :detective:")
            else:
                await message.reply(mention_author=False, content=":x: **" + itemName[0:15] + "**... is not in my database! :detective:")
            return

        if skin != "":
            skin = skin.lstrip(" ").lower()
            if skin not in bbData.builtInShipSkins:
                if len(skin) < 20:
                    await message.reply(mention_author=False, content=":x: The **" + skin + "** skin is not in my database! :detective:")
                else:
                    await message.reply(mention_author=False, content=":x: The **" + skin[0:15] + "**... skin is not in my database! :detective:")

            elif skin in bbData.builtInShipData[itemObj.name]["compatibleSkins"]:
                await message.reply(mention_author=False, content=":x: That skin is already compatible with the **" + itemObj.name + "**!")

            else:
                await lib.discordUtil.startLongProcess(message)
                await bbData.builtInShipSkins[skin].addShip(itemObj.name, botState.client.skinStorageChannel)
                await lib.discordUtil.endLongProcess(message)
                await message.reply(mention_author=False, content="Done!")

        else:
            await message.reply(mention_author=False, content=":x: Please provide a skin, prefaced by a `+`!")

    textCommandsDB.register("addSkin", dev_cmd_addSkin, 3, helpSection="skins", useDoc=True)


async def setup(bot: client.BasedClient):
    # Casting here because for some reason pyright doesn't think SerializableDiscordObject is a Snowflake,
    # even though it extends discord.Object
    await bot.add_cog(DevSkinsCog(bot), guilds=cast(List[Snowflake], cfg.developmentGuilds))
