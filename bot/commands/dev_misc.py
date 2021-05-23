import discord
import traceback
from datetime import datetime

from . import commandsDB as botCommands
from .. import botState, lib

from . import util_help


async def dev_cmd_dev_help(message: discord.Message, args: str, isDM: bool):
    """dev command printing help strings for dev commands

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    await util_help.util_autohelp(message, args, isDM, 3)

botCommands.register("dev-help", dev_cmd_dev_help, 3, signatureStr="**dev-help** *[page number, section or command]*",
                        shortHelp="Display information about developer-only commands.\nGive a specific command for " \
                                    + "detailed info about it, or give a page number or give a section name for brief info.",
                        longHelp="Display information about developer-only commands.\nGive a specific command for " \
                                    + "detailed info about it, or give a page number or give a section name for brief info " \
                                    + "about a set of commands. These are the currently valid section names:" \
                                    + "\n- Miscellaneous")


async def dev_cmd_sleep(message: discord.Message, args: str, isDM: bool):
    """developer command saving all data to JSON and then shutting down the bot

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    botState.shutdown = botState.ShutDownState.shutdown
    await message.channel.send("shutting down.")
    await botState.client.shutdown()

botCommands.register("bot-sleep", dev_cmd_sleep, 3, allowDM=True, useDoc=True)


async def dev_cmd_save(message: discord.Message, args: str, isDM: bool):
    """developer command saving all databases to JSON

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    try:
        botState.client.saveAllDBs()
    except Exception as e:
        print("SAVING ERROR", type(e).__name__)
        print(traceback.format_exc())
        await message.channel.send("failed!")
        return
    print(datetime.now().strftime("%H:%M:%S: Data saved manually!"))
    await message.channel.send("saved!")

botCommands.register("save", dev_cmd_save, 3, allowDM=True, useDoc=True)


async def dev_cmd_say(message: discord.Message, args: str, isDM: bool):
    """developer command sending a message to the same channel as the command is called in

    :param discord.Message message: the discord message calling the command
    :param str args: string containing the message to broadcast
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if args == "":
        await message.channel.send("provide a message!")
    else:
        await message.channel.send(**lib.discordUtil.messageArgsFromStr(args))

botCommands.register("say", dev_cmd_say, 3, forceKeepArgsCasing=True, allowDM=True, useDoc=True)


async def dev_cmd_broadcast(message : discord.Message, args : str, isDM : bool):
    """developer command sending a message to the playChannel of all guilds that have one

    :param discord.Message message: the discord message calling the command
    :param str args: string containing the message to broadcast
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if args == "":
        await message.channel.send("provide a message!")
    else:
        sendArgs = lib.discordUtil.messageArgsFromStr(args)

        if args.split(" ")[0].lower() == "announce-channel":
            for guild in botState.guildsDB.guilds.values():
                if guild.hasAnnounceChannel():
                    await guild.getAnnounceChannel().send(sendArgs)
        else:
            for guild in botState.guildsDB.guilds.values():
                if guild.hasPlayChannel():
                    await guild.getPlayChannel().send(sendArgs)

botCommands.register("broadcast", dev_cmd_broadcast, 2, forceKeepArgsCasing=True, allowDM=True, useDoc=True)


async def dev_cmd_reset_has_poll(message : discord.Message, args : str, isDM : bool):
    """developer command resetting the poll ownership of the calling user, or the specified user if one is given.

    :param discord.Message message: the discord message calling the command
    :param str args: string, can be empty or contain a user mention
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    # reset the calling user's cooldown if no user is specified
    if args == "":
        botState.usersDB.getUser(message.author.id).pollOwned = False
        # otherwise get the specified user's discord object and reset their cooldown.
        # [!] no validation is done.
    else:
        botState.usersDB.getUser(int(args.lstrip("<@!").rstrip(">"))).pollOwned = False
    await message.channel.send("Done!")

botCommands.register("reset-has-poll", dev_cmd_reset_has_poll, 2, allowDM=True, useDoc=True)


async def dev_cmd_bot_update(message: discord.Message, args: str, isDM: bool):
    """developer command that gracefully shuts down the bot, performs git pull, and then reboots the bot.

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    botState.shutdown = botState.ShutDownState.update
    await message.channel.send("updating and restarting...")
    await botState.client.shutdown()

botCommands.register("bot-update", dev_cmd_bot_update, 3, allowDM=True, useDoc=True)


async def dev_cmd_setbalance(message : discord.Message, args : str, isDM : bool):
    """developer command setting the requested user's balance.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing a user mention and an integer number of credits
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    argsSplit = args.split(" ")
    # verify both a user and a balance were given
    if len(argsSplit) < 2:
        await message.channel.send(":x: Please give a user mention followed by the new balance!")
        return
    # verify the requested balance is an integer
    if not lib.stringTyping.isInt(argsSplit[1]):
        await message.channel.send(":x: that's not a number!")
        return
    # verify the requested user
    requestedUser = botState.client.get_user(int(argsSplit[0].lstrip("<@!").rstrip(">")))
    if requestedUser is None:
        await message.channel.send(":x: invalid user!!")
        return
    if not botState.usersDB.idExists(requestedUser.id):
        requestedBBUser = botState.usersDB.addID(requestedUser.id)
    else:
        requestedBBUser = botState.usersDB.getUser(requestedUser.id)
    # update the balance
    requestedBBUser.credits = int(argsSplit[1])
    await message.channel.send("Done!")

botCommands.register("setbalance", dev_cmd_setbalance, 2, allowDM=True, useDoc=True)


async def dev_cmd_reset_transfer_cool(message : discord.Message, args : str, isDM : bool):
    """developer command resetting a user's home guild transfer cooldown.

    :param discord.Message message: the discord message calling the command
    :param str args: either empty string or string containing a user mention or ID
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    # reset the calling user's cooldown if no user is specified
    if args == "":
        botState.usersDB.getUser(message.author.id).guildTransferCooldownEnd = datetime.utcnow()
    # otherwise get the specified user's discord object and reset their cooldown.
    # [!] no validation is done.
    else:
        botState.usersDB.getUser(int(args.lstrip("<@!").rstrip(">"))).guildTransferCooldownEnd = datetime.utcnow()
    await message.channel.send("Done!")


botCommands.register("reset-transfer-cool", dev_cmd_reset_transfer_cool, 2, allowDM=True, useDoc=True)
