from typing import Awaitable, Callable, cast
import discord
from discord.utils import utcnow

from . import commandsDB as textCommandsDB
from .. import lib
import importlib
cmd_showme_ship = cast(Callable[[discord.Message, str, bool], Awaitable], importlib.import_module("bot.commands.usr_gof2-info").cmd_showme_ship)

import os
CWD = os.getcwd()

PAINTBRUSH_ICON = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/twitter/282/paintbrush_1f58c-fe0f.png"


textCommandsDB.addHelpSection(3, "skins")


# TODO: Move to DevSkinsCog once cmd_showme_ship has been ported
async def dev_cmd_timed_showme_ship(message: discord.Message, args: str, isDM: bool):
    """Perform cmd_showme_ship, but also send the amount of time taken to execute

    :param discord.Message message: the discord message calling the command
    :param str args: same as showme_ship but without "ship"
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    now = utcnow()
    await cmd_showme_ship(message, args, isDM)
    await message.reply(f"This command took: {lib.timeUtil.td_format_noYM(utcnow() - now)}", mention_author=False)
    

textCommandsDB.register("timed-showme-ship", dev_cmd_timed_showme_ship, 3, helpSection="skins", useDoc=True)
