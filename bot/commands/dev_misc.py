import discord
import traceback
from datetime import datetime

from . import commandsDB as botCommands
from .. import botState, lib
from ..users.basedUser import BasedUser
from ..gameObjects.items.tools import crateTool
from datetime import timedelta
from ..reactionMenus import giveawayMenu

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
                                    + "about a set of commands. These are the currently valid section names:• " \
                                + '\n• '.join(["Bounties", "Channels", "Misc", "GitHub", "Items", "Kaamo", "Loma", "Medals",
                                                "Skins"]))


async def dev_cmd_sleep(message: discord.Message, args: str, isDM: bool):
    """developer command saving all data to JSON and then shutting down the bot

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    botState.shutdown = botState.ShutDownState.shutdown
    await message.reply(mention_author=False, content="shutting down.")
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
        await message.reply(mention_author=False, content="failed!")
        return
    print(datetime.now().strftime("%H:%M:%S: Data saved manually!"))
    await message.reply(mention_author=False, content="saved!")

botCommands.register("save", dev_cmd_save, 3, allowDM=True, useDoc=True)


async def dev_cmd_say(message: discord.Message, args: str, isDM: bool):
    """developer command sending a message to the same channel as the command is called in

    :param discord.Message message: the discord message calling the command
    :param str args: string containing the message to broadcast
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if args == "":
        await message.reply(mention_author=False, content="provide a message!")
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
        await message.reply(mention_author=False, content="provide a message!")
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

botCommands.register("broadcast", dev_cmd_broadcast, 3, forceKeepArgsCasing=True, allowDM=True, useDoc=True)


async def dev_cmd_reset_has_poll(message : discord.Message, args : str, isDM : bool):
    """developer command resetting the poll ownership of the calling user, or the specified user if one is given.

    :param discord.Message message: the discord message calling the command
    :param str args: string, can be empty or contain a user mention
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    try:
        # reset the calling user's cooldown if no user is specified
        if args == "":
            requestedBUser: BasedUser = botState.usersDB.getUser(message.author.id)
        # otherwise get the specified user's discord object and reset their poll ownership.
        # [!] no validation is done.
        else:
            requestedBUser: BasedUser = botState.usersDB.getUser(int(args.lstrip("<@!").rstrip(">")))
    except KeyError:
        await message.reply(":x: Unknown user. They may not have used the bot yet.")

    menusRemoved = requestedBUser.removeAllOwnedMenusOfTypeID("poll")
    if menusRemoved:
        await message.reply(f"Ownership of {menusRemoved} removed successfuly.")
    else:
        await message.reply(mention_author=False, content="This user has no polls!")

botCommands.register("reset-has-poll", dev_cmd_reset_has_poll, 3, allowDM=True, useDoc=True)


async def dev_cmd_bot_update(message: discord.Message, args: str, isDM: bool):
    """developer command that gracefully shuts down the bot, performs git pull, and then reboots the bot.

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    botState.shutdown = botState.ShutDownState.update
    await message.reply(mention_author=False, content="updating and restarting...")
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
        await message.reply(mention_author=False, content=":x: Please give a user mention followed by the new balance!")
        return
    # verify the requested balance is an integer
    if not lib.stringTyping.isInt(argsSplit[1]):
        await message.reply(mention_author=False, content=":x: that's not a number!")
        return
    # verify the requested user
    requestedUser = botState.client.get_user(int(argsSplit[0].lstrip("<@!").rstrip(">")))
    if requestedUser is None:
        await message.reply(mention_author=False, content=":x: invalid user!!")
        return
    if not botState.usersDB.idExists(requestedUser.id):
        requestedBBUser = botState.usersDB.addID(requestedUser.id)
    else:
        requestedBBUser = botState.usersDB.getUser(requestedUser.id)
    # update the balance
    requestedBBUser.credits = int(argsSplit[1])
    await message.reply(mention_author=False, content="Done!")

botCommands.register("setbalance", dev_cmd_setbalance, 3, allowDM=True, useDoc=True)


async def dev_cmd_start_stocking_giveaway(message : discord.Message, args : str, isDM : bool):
    """developer command starting a giveaway of the keith stocking crate for 48 hours
    :param discord.Message message: the discord message calling the command
    :param str args: ignore
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    giveawayMsg = await message.channel.send("‎")
    stocking = crateTool.CrateTool.fromDict({"type": "CrateTool", "crateType": "christmas", "typeNum": 2021, "builtIn": True})
    menu = giveawayMenu.GiveawayMenu(giveawayMsg, [stocking], activeTime=timedelta(days=3),
                                        titleTxt="Merry Christmas!", 
                                        desc="React below to receive your stocking!\nFind it in your `$hangar tool`, and open it with the new `$use` command.",
                                        col=discord.Colour.random())

    botState.reactionMenusDB[giveawayMsg.id] = menu
    await menu.updateMessage()

botCommands.register("start-stocking-giveaway", dev_cmd_start_stocking_giveaway, 3, useDoc=True)
