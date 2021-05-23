import discord
from datetime import datetime
from aiohttp import client_exceptions
import operator
import traceback

from . import commandsDB as botCommands
from . import util_help
from .. import lib, botState
from ..cfg import cfg, bbData, versionInfo
from ..users import basedUser
from ..reactionMenus import reactionMenu, reactionPollMenu
from ..scheduling import timedTask
from ..userAlerts import userAlerts


async def cmd_help(message: discord.Message, args: str, isDM: bool):
    """Print the help strings as an embed.
    If a command is provided in args, the associated help string for just that command is printed.

    :param discord.Message message: the discord message calling the command
    :param str args: empty, or a single command name
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    await util_help.util_autohelp(message, args, isDM, 0)

botCommands.register("help", cmd_help, 0, allowDM=True, signatureStr="**help** *[page number, section or command]*",
                     shortHelp="Show usage information for available commands.\nGive a specific command for detailed info " \
                                + "about it, or give a page number or give a section name for brief info.",
                     longHelp="Show usage information for available commands.\nGive a specific command for detailed info " \
                                + "about it, or give a page number or give a section name for brief info about a set of " \
                                + "commands. These are the currently valid section names:\n- Miscellaneous",
                     useDoc=False)


async def cmd_source(message: discord.Message, args: str, isDM: bool):
    """Print a short message with information about the bot's source code.

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    srcEmbed = lib.discordUtil.makeEmbed(authorName="Source Code",
                                         col=discord.Colour.purple(),
                                         icon="https://image.flaticon.com/icons/png/512/25/25231.png",
                                         footerTxt="Bot Source",
                                         footerIcon="https://i.imgur.com/7SMgF0t.png")
    srcEmbed.add_field(name="Uptime",
                       value=lib.timeUtil.td_format_noYM(datetime.utcnow() - botState.client.launchTime))
    srcEmbed.add_field(name="Author",
                       value="Trimatix#2244")
    srcEmbed.add_field(name="API",
                       value="[Discord.py " + discord.__version__ + "](https://github.com/Rapptz/discord.py/)")
    srcEmbed.add_field(name="BASED",
                       value="[BASED " + versionInfo.BASED_VERSION + "](https://github.com/Trimatix/BASED)")
    srcEmbed.add_field(name="GitHub",
                       value="Please ask the bot developer to post their GitHub repository here!")
    srcEmbed.add_field(name="Invite",
                       value="Please ask the bot developer to post the bot's invite link here!")
    srcEmbed.add_field(name="__Upcoming Features__",
                       value="[Todo list](https://github.com/Trimatix/GOF2BountyBot/projects/1)")
    srcEmbed.add_field(name="__Special Thanks__", value=" • **DeepSilver FishLabs**, creators of Galaxy on Fire 2. " \
                                                            + "I own no intellectual property rights for GOF assets.\n" \
                                                        + " • **The BountyBot testing team** for their incredible support\n" \
                                                        + " • **NovahKiin22 and Poisonwasp** for development " \
                                                            + "contributions and insights", inline=False)
    await message.channel.send(embed=srcEmbed)

botCommands.register("source", cmd_source, 0, allowDM=True, signatureStr="**source**",
                     shortHelp="Show links to the project's GitHub page and todo list, and some information about the " \
                                + "people behind BountyBot.")


async def cmd_how_to_play(message : discord.Message, args : str, isDM : bool):
    """Print a short guide, teaching users how to play bounties.

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    sendChannel = None
    sendDM = False

    if message.author.dm_channel is None:
        await message.author.create_dm()
    if message.author.dm_channel is None:
        sendChannel = message.channel
    else:
        sendChannel = message.author.dm_channel
        sendDM = True

    try:
        newBountiesChannelStr = ""
        if not isDM:
            requestedBBGuild = botState.guildsDB.addDcGuild(message.guild)
            if requestedBBGuild.hasBountyBoardChannel:
                newBountiesChannelStr = " in <#" + str(requestedBBGuild.bountyBoardChannel.channel.id) + ">"
            elif requestedBBGuild.hasAnnounceChannel:
                newBountiesChannelStr = " in <#" + str(requestedBBGuild.getAnnounceChannel().id) + ">"
            prefix = requestedBBGuild.commandPrefix
        else:
            prefix = cfg.defaultCommandPrefix


        howToPlayEmbed = lib.discordUtil.makeEmbed(titleTxt='**How To Play**',
                                                    desc="This game is based on the *'Most Wanted'* system from Galaxy on " \
                                                            + "Fire 2. If you have played the Supernova addon, this should " \
                                                            + "be familiar!\n\nIf at any time you would like information " \
                                                            + "about a command, use the `" + prefix + "help [command]` " \
                                                            + "command. To see all commands, just use `" + prefix \
                                                            + "help`.\n‎", footerTxt="Have fun! 🚀",
                                                    thumb=botState.client.user.avatar_url_as(size=64))
        howToPlayEmbed.add_field(name="1. New Bounties",
                                    value="Every 15m - 1h (randomly), bounties are announced" + newBountiesChannelStr \
                                        + ".\n• Use `" + prefix + "bounties` to see the currently active bounties.\n" \
                                        + "• Criminals spawn in a system somewhere on the `" + prefix + "map`.\n" \
                                        + "• To view a criminal's current route *(possible systems)*, use `" + prefix \
                                            + "route [criminal]`.\n‎", inline=False)
        howToPlayEmbed.add_field(name="2. System Checking",
                                    value="Now that we know where our criminal could be, we can check a system with `" \
                                        + prefix + "check [system]`.\nThis system will now be crossed out in the " \
                                        + "criminal's `" + prefix + "route`, so we know not to check there.\n\n" \
                                        + "> Didn't win the bounty? No worries!\nYou will be awarded credits for helping " \
                                        + "*narrow down the search*.\n‎", inline=False)
        howToPlayEmbed.add_field(name="3. Items",
                                    value="Now that you've got some credits, try customising your `" + prefix + "loadout`!" \
                                        + "\n• You can see your inventory of inactive items in the `" + prefix + "hangar`." \
                                        + "\n• You can `" + prefix + "buy` more items from the `" + prefix + "shop`.\n‎",
                                    inline=False)
        howToPlayEmbed.add_field(name="Extra Notes/Tips",
                                    value="• Bounties are shared across all servers, everyone is competing to find them!\n" \
                                        + "• Each server has its own `" + prefix + "shop`. The shops refresh every " \
                                            + "*6 hours.*\n" \
                                        + "• Is a criminal, item or system name too long? Use an alias instead! You can " \
                                            + "see aliases with `" + prefix + "info`.\n" \
                                        + "• Having trouble getting to new bounties in time? Try out the new `" + prefix \
                                            + "notify bounties` command!", inline=False)

        await sendChannel.send(embed=howToPlayEmbed)
    except discord.Forbidden:
        await message.channel.send(":x: I can't DM you, " + message.author.display_name \
                                    + "! Please enable DMs from users who are not friends.")
        return

    if sendDM:
        await message.add_reaction(cfg.defaultEmojis.dmSent.sendable)

botCommands.register("how-to-play", cmd_how_to_play, 0, aliases=["guide"], allowDM=True, signatureStr="**how-to-play**",
                        shortHelp="Get a short introduction on how to play bounties!")


async def cmd_hello(message : discord.Message, args : str, isDM : bool):
    """say hello!

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    await message.channel.send("Greetings, pilot! **o7**")

botCommands.register("hello", cmd_hello, 0, allowDM=True, noHelp=True)


async def cmd_stats(message : discord.Message, args : str, isDM : bool):
    """print the stats of the specified user, use the calling user if no user is specified.

    :param discord.Message message: the discord message calling the command
    :param str args: string, can be empty or contain a user mention
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    # if no user is specified
    if args == "":
        requestedUser = message.author

    # If a user is specified
    else:
        requestedUser = lib.discordUtil.getMemberByRefOverDB(args, dcGuild=message.guild)
        # verify the user mention
        if requestedUser is None:
            if isDM:
                prefix = cfg.defaultCommandPrefix
            else:
                prefix = botState.guildsDB.getGuild(message.guild.id).commandPrefix
            await message.channel.send(":x: **Invalid user!** use `" + prefix + "balance` to display your own balance, or `" \
                                        + prefix + "balance <user>` to display someone else's balance!\n" \
                                        + "When referencing a player from another server, you must use their long ID number")
            return

        # create the stats embed
        statsEmbed = lib.discordUtil.makeEmbed(col=bbData.factionColours["neutral"], desc="__Pilot Statistics__",
                                                titleTxt=lib.discordUtil.userOrMemberName(requestedUser, message.guild),
                                                footerTxt="Pilot number #" + requestedUser.discriminator,
                                                thumb=requestedUser.avatar_url_as(size=64))
        # If the requested user is not in the database, don't bother adding them just print zeroes
        if not botState.usersDB.idExists(requestedUser.id):
            statsEmbed.add_field(name="Credits balance:", value=0, inline=True)
            statsEmbed.add_field(name="Total value:", value=str(basedUser.defaultUserValue), inline=True)
            statsEmbed.add_field(name="‎", value="__Bounty Hunting__", inline=False)
            statsEmbed.add_field(name="Total systems checked:", value=0, inline=True)
            statsEmbed.add_field(name="Total bounties won:", value=0, inline=True)
            statsEmbed.add_field(name="Total earned from bounties:", value=0, inline=True)
            statsEmbed.add_field(name="‎", value="__Dueling__", inline=False)
            statsEmbed.add_field(name="Duels won:", value="0", inline=True)
            statsEmbed.add_field(name="Duels lost:", value="0", inline=True)
            statsEmbed.add_field(name="Total credits won:", value="0", inline=True)
            statsEmbed.add_field(name="Total credits lost:", value="0", inline=True)

        # Otherwise, print the stats stored in the user's database entry
        else:
            userObj = botState.usersDB.getUser(requestedUser.id)
            statsEmbed.add_field(name="Credits balance:", value=str(userObj.credits), inline=True)
            statsEmbed.add_field(name="Total value:", value=str(userObj.getStatByName("value")), inline=True)
            statsEmbed.add_field(name="‎", value="__Bounty Hunting__", inline=False)
            statsEmbed.add_field(name="Total systems checked:", value=str( userObj.systemsChecked), inline=True)
            statsEmbed.add_field(name="Total bounties won:", value=str( userObj.bountyWins), inline=True)
            statsEmbed.add_field(name="Total credits earned from bounties:", value=str( userObj.lifetimeCredits), inline=True)
            statsEmbed.add_field(name="‎", value="__Dueling__", inline=False)
            statsEmbed.add_field(name="Duels won:", value=str( userObj.duelWins), inline=True)
            statsEmbed.add_field(name="Duels lost:", value=str( userObj.duelLosses), inline=True)
            statsEmbed.add_field(name="Total credits won:", value=str( userObj.duelCreditsWins), inline=True)
            statsEmbed.add_field(name="Total credits lost:", value=str( userObj.duelCreditsLosses), inline=True)

        # send the stats embed
        await message.channel.send(embed=statsEmbed)

botCommands.register("stats", cmd_stats, 0, aliases=["profile"], forceKeepArgsCasing=True, allowDM=True,
                        signatureStr="**stats** *[user]*",
                        shortHelp="Get various credits and bounty statistics about yourself, or another user.")


async def cmd_leaderboard(message : discord.Message, args : str, isDM : bool):
    """display leaderboards for different statistics
    if no arguments are given, display the local leaderboard for pilot value (value of loadout, hangar and balance, summed)
    if -g is given, display the appropriate leaderbaord across all guilds
    if -c is given, display the leaderboard for current balance
    if -s is given, display the leaderboard for systems checked
    if -w is given, display the leaderboard for bounties won

    :param discord.Message message: the discord message calling the command
    :param str args: string containing the arguments the user passed to the command
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    # across all guilds?
    globalBoard = False
    # stat to display
    stat = "value"
    # "global" or the local guild name
    boardScope = message.guild.name
    # user friendly string for the stat
    boardTitle = "Total Player Value"
    # units for the stat
    boardUnit = "Credit"
    boardUnits = "Credits"
    boardDesc = "*The total value of player inventory, loadout and credits balance"

    if isDM:
        prefix = cfg.defaultCommandPrefix
    else:
        prefix = botState.guildsDB.getGuild(message.guild.id).commandPrefix

    # change leaderboard arguments based on the what is provided in args
    if args != "":
        args = args.lower()
        if not args.startswith("-"):
            await message.channel.send(":x: Please prefix your arguments with a dash! E.g: `" + prefix + "leaderboard -gc`")
            return
        args = args[1:]
        if ("g" not in args and len(args) > 2) or ("g" in args and len(args) > 3):
            await message.channel.send(":x: Too many arguments! Please only specify one leaderboard. E.g: `" + prefix \
                                        + "leaderboard -gc`")
            return
        for arg in args:
            if arg not in "gcsw":
                await message.channel.send(":x: Unknown argument: '**" + arg + "**'. Please refer to `" + prefix \
                                            + "help leaderboard`")
                return
        if "c" in args:
            stat = "credits"
            boardTitle = "Current Balance"
            boardUnit = "Credit"
            boardUnits = "Credits"
            boardDesc = "*Current player credits balance"
        elif "s" in args:
            stat = "systemsChecked"
            boardTitle = "Systems Checked"
            boardUnit = "System"
            boardUnits = "Systems"
            boardDesc = "*Total number of systems `" + prefix + "check`ed"
        elif "w" in args:
            stat = "bountyWins"
            boardTitle = "Bounties Won"
            boardUnit = "Bounty"
            boardUnits = "Bounties"
            boardDesc = "*Total number of bounties won"
        if "g" in args:
            globalBoard = True
            boardScope = "Global Leaderboard"
            boardDesc += " across all servers"

    boardDesc += ".*"

    # get the requested stats and sort users by the stat
    inputDict = {}
    for user in botState.usersDB.getUsers():
        if (globalBoard and botState.client.get_user(user.id) is not None) or \
                (not globalBoard and message.guild.get_member(user.id) is not None):
            inputDict[user.id] = user.getStatByName(stat)
    sortedUsers = sorted(inputDict.items(), key=operator.itemgetter(1))[::-1]

    # build the leaderboard embed
    leaderboardEmbed = lib.discordUtil.makeEmbed(titleTxt=boardTitle, authorName=boardScope,
                                                    icon=bbData.winIcon, col=bbData.factionColours["neutral"], desc=boardDesc)

    # add all users to the leaderboard embed with places and values
    externalUser = False
    first = True
    for place in range(min(len(sortedUsers), 10)):
        # handling for global leaderboards and users not in the local guild
        if globalBoard and message.guild.get_member(sortedUsers[place][0]) is None:
            leaderboardEmbed.add_field(value="*" + str(place + 1) + ". " \
                                            + str(botState.client.get_user(sortedUsers[place][0])),
                                        name=("⭐ " if first else "") + str(sortedUsers[place][1]) + " " \
                                            + (boardUnit if sortedUsers[place][1] == 1 else boardUnits), inline=False)
            externalUser = True
            if first:
                first = False
        else:
            leaderboardEmbed.add_field(value=str(place + 1) + ". " + message.guild.get_member(sortedUsers[place][0]).mention,
                                        name=("⭐ " if first else "") + str(sortedUsers[place][1]) + " " \
                                            + (boardUnit if sortedUsers[place][1] == 1 else boardUnits), inline=False)
            if first:
                first = False
    # If at least one external use is on the leaderboard, give a key
    if externalUser:
        leaderboardEmbed.set_footer(
            text="An `*` indicates a user that is from another server.")
    # send the embed
    await message.channel.send(embed=leaderboardEmbed)

botCommands.register("leaderboard", cmd_leaderboard, 0, allowDM=False, signatureStr="**leaderboard** *[-g|-c|-s|-w]*",
                        longHelp="Show the leaderboard for total player value. Give `-g` for the global leaderboard, " \
                            + "not just this server.\n> Give `-c` for the current credits balance leaderboard.\n" \
                            + "> Give `-s` for the 'systems checked' leaderboard.\n" \
                            + "> Give `-w` for the 'bounties won' leaderboard.\n" \
                            + "E.g: `leaderboard -gs`")


async def cmd_notify(message : discord.Message, args : str, isDM : bool):
    """⚠ WARNING: MARKED FOR CHANGE ⚠
    The following function is provisional and marked as planned for overhaul.
    Details: Notifications for shop items have yet to be implemented.

    Allow a user to subscribe and unsubscribe from pings when certain events occur.
    Currently only new bounty notifications are implemented, but more are planned.
    For example, a ping when a requested item is in stock in the guild's shop.

    :param discord.Message message: the discord message calling the command
    :param str args: the notification type (e.g ship), possibly followed by a specific notification (e.g groza mk II),
                        separated by a single space.
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    requestedBBUser = botState.usersDB.getOrAddID(message.author.id)
    requestedBBGuild = botState.guildsDB.getGuild(message.guild.id)

    if not message.guild.me.guild_permissions.manage_roles:
        await message.channel.send(":x: I do not have the 'Manage Roles' permission in this server! " \
                                    + "Please contact an admin :robot:")
        return
    if args == "":
        await message.channel.send(":x: Please name what you would like to be notified for! E.g `" \
                                    + requestedBBGuild.commandPrefix + "notify bounties`")
        return

    argsSplit = args.split(" ")
    alertsToToggle = userAlerts.getAlertIDFromHeirarchicalAliases(argsSplit)

    if alertsToToggle[0] == "ERR":
        await message.channel.send(alertsToToggle[1].replace("$COMMANDPREFIX$", requestedBBGuild.commandPrefix))
        return

    for alertID in alertsToToggle:
        alertType = userAlerts.userAlertsIDsTypes[alertID]
        try:
            alertNewState = await requestedBBUser.toggleAlertType(alertType, message.guild, requestedBBGuild, message.author)
            await message.channel.send(":white_check_mark: You have " \
                                        + ("subscribed to" if alertNewState else "unsubscribed from") + " " \
                                        + userAlerts.userAlertsTypesNames[alertType] + " notifications.")
        except discord.Forbidden:
            await message.channel.send(":woozy_face: I don't have permission to do that! Please ensure the requested role " \
                                        + "is beneath the BountyBot role.")
        except discord.HTTPException:
            await message.channel.send(":woozy_face: Something went wrong! Please contact an admin or try again later.")
        except ValueError:
            await message.channel.send(":x: This server does not have a role for " \
                                        + userAlerts.userAlertsTypesNames[alertType] + " notifications. :robot:")
        except client_exceptions.ClientOSError:
            await message.channel.send(":thinking: Whoops! A connection error occurred, and the error has been logged. " \
                                        + "Could you try that again please?")
            botState.logger.log("main", "cmd_notify", "aiohttp.client_exceptions.ClientOSError occurred when attempting to " \
                                                        + "grant " + message.author.name + "#" + str(message.author.id) \
                                                        + " alert " + alertID + "in guild " + message.guild.name + "#" \
                                                        + str(message.guild.id) + ".", category="userAlerts",
                                eventType="ClientOSError", trace=traceback.format_exc())

botCommands.register("notify", cmd_notify, 0, allowDM=False, signatureStr="**notify <type>** *[alert]*",
                        longHelp="Subscribe to pings when events take place. Currently, **type** can be `bounties`, " \
                            + "`shop`, `duels`, or `bot`.\n" \
                            + "> `shop` requires the `refresh` option.\n" \
                            + "> `duels` requires either `new` or `cancel`.\n" \
                            + "> `bot` can take `updates` or `announcements`.\n" \
                            + "> `bot updates` must be `major` or `minor`.")


async def cmd_poll(message : discord.Message, args : str, isDM : bool):
    """Run a reaction-based poll, allowing users to choose between several named options.
    Users may not create more than one poll at a time, anywhere.
    Option reactions must be either unicode, or custom to the server where the poll is being created.

    args must contain a poll subject (question) and new line, followed by a newline-separated list of emoji-option pairs,
    where each pair is separated with a space.
    For example: 'Which one?\n0️⃣ option a\n1️⃣ my second option\n2️⃣ three' will produce three options:
    - 'option a'         which participants vote for by adding the 0️⃣ reaction
    - 'my second option' which participants vote for by adding the 1️⃣ reaction
    - 'three'            which participants vote for by adding the 2️⃣ reaction
    and the subject of the poll is 'Which one?'
    The poll subject is optional. To not provide a subject, simply begin args with a new line.

    args may also optionally contain the following keyword arguments, given as argname=value
    - target         : A role or user to restrict participants by. Must be a user or role mention, not ID.
    - multiplechoice : Whether or not to allow participants to vote for multiple poll options. Must be true or false.
    - days           : The number of days that the poll should run for. Must be at least one, or unspecified.
    - hours          : The number of hours that the poll should run for. Must be at least one, or unspecified.
    - minutes        : The number of minutes that the poll should run for. Must be at least one, or unspecified.
    - seconds        : The number of seconds that the poll should run for. Must be at least one, or unspecified.

    Polls must have a run length. That is, specifying ALL run time kwargs as 'off' will return an error.

    TODO: restrict target kwarg to just roles, not users
    TODO: Change options list formatting from comma separated to new line separated
    TODO: Support target IDs

    :param discord.Message message: the discord message calling the command
    :param str args: A comma-separated list of space-separated emoji-option pairs, and optionally any kwargs as specified
                        in this function's docstring
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if botState.usersDB.getOrAddID(message.author.id).pollOwned:
        await message.channel.send(":x: You can only make one poll at a time!")
        return

    pollOptions = {}
    kwArgs = {}
    requestedBBGuild = botState.guildsDB.getGuild(message.guild.id)

    argsSplit = args.split("\n")
    if len(argsSplit) < 2:
        await message.channel.send(":x: Invalid arguments! Please provide your poll subject, followed by a new line, then " \
                                    + "a new line-separated series of poll options.\nFor more info, see `" \
                                    + requestedBBGuild.commandPrefix + "help poll`")
        return
    pollSubject = argsSplit[0]
    argPos = 0
    for arg in argsSplit[1:]:
        if arg == "":
            continue
        argPos += 1
        try:
            argNoSpaces = arg.strip(" ")
            optionName = argNoSpaces[arg.strip(" ").index(" ") + 1:]
            dumbReact = lib.emojis.BasedEmoji.fromStr(argNoSpaces.split(" ")[0])
        except (ValueError, IndexError):
            for kwArg in ["target=", "days=", "hours=", "seconds=", "minutes=", "multiplechoice="]:
                if arg.lower().startswith(kwArg):
                    kwArgs[kwArg[:-1]] = arg[len(kwArg):]
                    break
        # except lib.exceptions.UnrecognisedCustomEmoji:
        #     await message.channel.send(":x: I don't know your " + str(argPos) + lib.stringTyping.getNumExtension(argPos) \
        #                                 + " emoji!\n" \
        #                                 + "You can only use built in emojis, or custom emojis that are in this server.")
        #     return
        else:
            if dumbReact.sendable == "None":
                await message.channel.send(":x: I don't know your " + str(argPos) + lib.stringTyping.getNumExtension(argPos) \
                                            + " emoji!\nYou can only use built in emojis, " \
                                            + "or custom emojis that are in this server.")
                return
            if dumbReact is None:
                await message.channel.send(":x: Invalid emoji: " + argNoSpaces.split(" ")[1])
                return
            elif dumbReact.isID:
                localEmoji = False
                for localEmoji in message.guild.emojis:
                    if localEmoji.id == dumbReact.id:
                        localEmoji = True
                        print("EMOJI FOUND")
                        break
                if not localEmoji:
                    await message.channel.send(":x: I don't know your " + str(argPos) \
                                                + lib.stringTyping.getNumExtension(argPos) + " emoji!\n" \
                                                + "You can only use built in emojis, or custom emojis " \
                                                + "that are in this server.")
                    return

            if dumbReact in pollOptions:
                await message.channel.send(":x: Cannot use the same emoji for two options!")
                return

            pollOptions[dumbReact] = reactionMenu.DummyReactionMenuOption(optionName, dumbReact)

    if len(pollOptions) == 0:
        await message.channel.send(":x: No options given!")
        return

    targetRole = None
    targetMember = None
    if "target" in kwArgs:
        if lib.stringTyping.isRoleMention(kwArgs["target"]):
            targetRole = message.guild.get_role(int(kwArgs["target"].lstrip("<@&").rstrip(">")))
            if targetRole is None:
                await message.channel.send(":x: Unknown target role!")
                return

        elif lib.stringTyping.isMention(kwArgs["target"]):
            targetMember = message.guild.get_member(int(kwArgs["target"].lstrip("<@!").rstrip(">")))
            if targetMember is None:
                await message.channel.send(":x: Unknown target user!")
                return

        else:
            await message.channel.send(":x: Invalid target role/user!")
            return

    timeoutDict = {}

    for timeName in ["days", "hours", "minutes", "seconds"]:
        if timeName in kwArgs:
            if kwArgs[timeName].lower() == "off":
                timeoutDict[timeName] = -1
            else:
                if not lib.stringTyping.isInt(kwArgs[timeName]) or int(kwArgs[timeName]) < 1:
                    await message.channel.send(":x: Invalid number of " + timeName + " before timeout!")
                    return

                timeoutDict[timeName] = int(kwArgs[timeName])


    multipleChoice = True

    if "multiplechoice" in kwArgs:
        if kwArgs["multiplechoice"].lower() in ["off", "no", "false", "single", "one"]:
            multipleChoice = False
        elif kwArgs["multiplechoice"].lower() not in ["on", "yes", "true", "multiple", "many"]:
            await message.channel.send("Invalid `multiplechoice` argument '" + kwArgs["multiplechoice"] \
                                        + "'! Please use either `multiplechoice=yes` or `multiplechoice=no`")
            return


    timeoutExists = False
    for timeName in timeoutDict:
        if timeoutDict[timeName] != -1:
            timeoutExists = True
    timeoutExists = timeoutExists or timeoutDict == {}

    if not timeoutExists:
        await message.channel.send(":x: Poll timeouts cannot be disabled!")
        return

    menuMsg = await message.channel.send("‎")

    timeoutDelta = lib.timeUtil.timeDeltaFromDict(cfg.timeouts.pollMenuExpiry if timeoutDict == {} else timeoutDict)
    timeoutTT = timedTask.TimedTask(expiryDelta=timeoutDelta, expiryFunction=reactionPollMenu.printAndExpirePollResults,
                                    expiryFunctionArgs=menuMsg.id)
    botState.reactionMenusTTDB.scheduleTask(timeoutTT)

    menu = reactionPollMenu.ReactionPollMenu(menuMsg, pollOptions, timeoutTT, pollStarter=message.author,
                                                multipleChoice=multipleChoice, targetRole=targetRole,
                                                targetMember=targetMember,
                                                owningBBUser=botState.usersDB.getUser(message.author.id),
                                                desc=pollSubject)
    await menu.updateMessage()
    botState.reactionMenusDB[menuMsg.id] = menu
    botState.usersDB.getUser(message.author.id).pollOwned = True

botCommands.register("poll", cmd_poll, 0, forceKeepArgsCasing=True, allowDM=False,
                        signatureStr="**poll** *<subject>*\n**<option1 emoji> <option1 name>**\n...    ...\n*[kwargs]*",
                        shortHelp="Start a reaction-based poll. Each option must be on its own new line, as an emoji, " \
                            + "followed by a space, followed by the option name.",
                        longHelp="Start a reaction-based poll. Each option must be on its own new line, as an emoji, " \
                            + "followed by a space, followed by the option name. The `subject` is the question that users " \
                            + "answer in the poll and is optional, to exclude your subject simply give a new line.\n\n" \
                            + "__Optional Arguments__\nOptional arguments should be given by `name=value`, with each arg " \
                                + "on a new line.\n" \
                            + "- Give `multiplechoice=no` to only allow one vote per person (default: yes).\n" \
                            + "- Give `target=@role mention` to limit poll participants only to users with the specified " \
                                + "role.\n" \
                            + "- You may specify the length of the poll, with each time division on a new line. Acceptable " \
                                + "time divisions are: `seconds`, `minutes`, `hours`, `days`. (default: minutes=5)")
