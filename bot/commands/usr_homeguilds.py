import discord
from datetime import datetime

from . import commandsDB as botCommands
from .. import botState, lib
from ..cfg import cfg
from ..reactionMenus.confirmationReactionMenu import InlineConfirmationMenu


botCommands.addHelpSection(0, "home servers")


async def cmd_transfer(message : discord.Message, args : str, isDM : bool):
    """Transfer the calling user's home guild to the guild where the message was sent.

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    requestedBBUser = botState.usersDB.getOrAddID(message.author.id)
    if message.guild.id == requestedBBUser.homeGuildID:
        await message.channel.send(":x: This is already your home server!")
    elif not requestedBBUser.canTransferGuild():
        timeLeft = requestedBBUser.guildTransferCooldownEnd - datetime.utcnow()
        await message.channel.send(":x: This command is still on cooldown. (" \
                                    + lib.timeUtil.td_format_noYM(timeLeft) + " left)")
    else:
        confirmMsg = await message.channel.send("Move your home server to '" + message.guild.name + "'?")
        cooldownTime = lib.timeUtil.timeDeltaFromDict(cfg.homeGuildTransferCooldown)
        confirmation = await InlineConfirmationMenu(confirmMsg, message.author, cfg.toolUseConfirmTimeoutSeconds,
                                                    desc="This command's cooldown is " \
                                                        + lib.timeUtil.td_format_noYM(cooldownTime) + ".").doMenu()

        if cfg.defaultEmojis.reject in confirmation:
            await message.channel.send("🛑 Home guild transfer cancelled.")
        elif cfg.defaultEmojis.accept in confirmation:
            await requestedBBUser.transferGuild(message.guild)
            await message.channel.send(":airplane_arriving: You transferred your home server to " + message.guild.name + "!")

botCommands.register("transfer", cmd_transfer, 0, allowDM=False, helpSection="home servers", signatureStr="**transfer**",
                    shortHelp="Change your home server. This command has a long cooldown!",
                    longHelp="Transfer your home server to the one where you sent this command. You will be asked for " \
                                + "confirmation first, since this command has a long cooldown!")


async def cmd_home(message : discord.Message, args : str, isDM : bool):
    """Display the name of the calling user's home guild, if they have one.

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if botState.usersDB.idExists(message.author.id):
        requestedBBUser = botState.usersDB.getUser(message.author.id)
        if message.guild is not None and message.guild.id == requestedBBUser.homeGuildID:
            await message.channel.send("🌍 This is your home server.")
            return
        elif requestedBBUser.hasHomeGuild() and botState.client.get_guild(requestedBBUser.homeGuildID) is not None:
            await message.channel.send("🪐 Your home server is '" \
                                        + botState.client.get_guild(requestedBBUser.homeGuildID).name + "'.")
            return
    if isDM:
        prefix = cfg.defaultCommandPrefix
    else:
        prefix = botState.guildsDB.getGuild(message.guild.id).commandPrefix
    await message.channel.send("🌑 Your home server has not yet been set.\n" \
                                + "Set your home server by using the shop or bounty board, or with the `" + prefix \
                                + "transfer` command.")

botCommands.register("home", cmd_home, 0, allowDM=True, helpSection="home servers", signatureStr="**home**",
                    shortHelp="Get the name of your home server, if one is set.",
                    longHelp="Get the name of your home server, if one is set. This is the the only server where you may " \
                                + "use certain commands, such as buying items from the shop, or fighting bounties.")
