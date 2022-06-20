import discord
from datetime import datetime

from . import commandsDB as botCommands
from .. import botState, lib
from ..users import basedUser


botCommands.addHelpSection(3, "home servers")


async def dev_cmd_reset_transfer_cooldown(message : discord.Message, args : str, isDM : bool):
    """Reset the requested user's cmd_transfer cooldown.

    :param discord.Message message: the discord message calling the command
    :param str args: empty, or a user reference
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if not args:
        if not botState.client.usersDB.idExists(message.author.id):
            await message.reply(":x: You are not on transfer cooldown!")
            return
        requestedBBUser: basedUser.BasedUser = botState.client.usersDB.getUser(message.author.id)
    else:
        requestedUser = lib.discordUtil.getMemberFromRef(args, message.guild)
        if requestedUser is None:
            await message.reply(":x: Unknown user!")
            return
        if not botState.client.usersDB.idExists(requestedUser.id):
            await message.reply(":x: That user is not on transfer cooldown!")
            return
        requestedBBUser = botState.client.usersDB.getUser(message.author.id)

    now = datetime.utcnow()
    if requestedBBUser.canTransferGuild(now=now):
        await message.reply(":x: That user is not on transfer cooldown!")
    else:
        requestedBBUser.guildTransferCooldownEnd = now
        await message.reply("✅ Done!")


botCommands.register("reset-transfer-cooldown", dev_cmd_reset_transfer_cooldown, 3, aliases=["reset-transfer-cool"],
                    allowDM=False, helpSection="home servers", signatureStr="**reset-transfer-cooldown**", useDoc=True)