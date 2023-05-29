from typing import cast
import discord

from . import commandsDB as textCommandsDB
from .. import botState
from ..cfg import cfg
from . import util_autoskin


async def admin_cmd_showmeHD(message: discord.Message, args: str, isDM: bool):
    """Render the attached image file onto the specified ship, in high definition.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing a ship name
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if isDM:
        prefix: str = cfg.defaultCommandPrefix
    else:
        # Casting here because message.guild can be none, but it cannot be None here because we know that isDM is False
        prefix = botState.client.guildsDB.getGuild(cast(discord.Guild, message.guild).id).commandPrefix

    # verify a item was given
    if args == "":
        await message.reply(mention_author=False,
                            content=f":x: Please provide a ship! Example: `{prefix}showme ship Groza Mk II`")
        return

    full = args.endswith("-full")
    if full:
        args = args.split("-full")[0].rstrip()

    result = await util_autoskin.collectAutoskinArgs(message, args, cfg.skinRenderShowmeHDResolution[0],
                                                                        cfg.skinRenderShowmeHDResolution[1],
                                                                        cfg.skinRenderShowmeHDSamples, True, full=full)
    if result is None:
        return
    shipName, rendererArgs = result
    await util_autoskin.doAutoSkin(message, rendererArgs, shipName, "HD")


textCommandsDB.register("showmehd", admin_cmd_showmeHD, 2, allowDM=True, signatureStr="**showmeHD <ship-name>** *[-full]*",
                        shortHelp="Render your specified ship with the given skin, in full HD 1080p! " \
                                    + "⚠ WARNING: THIS WILL TAKE A LONG TIME.",
                        longHelp="You must attach a 2048x2048 jpg to your message. Render your specified ship with the " \
                                    + "given skin, in full HD 1080p! ⚠ WARNING: THIS WILL TAKE A LONG TIME. Give `-full` " \
                                    + "to disable autoskin and render exactly your provided image, " \
                                    + "with no additional texturing.")
