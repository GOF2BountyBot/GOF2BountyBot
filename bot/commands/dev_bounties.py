import discord
from datetime import datetime, timedelta
import asyncio
import traceback
import random

from . import commandsDB as botCommands
from .. import botState, lib
from ..lib import gameMaths
from ..cfg import cfg, bbData
from ..gameObjects.bounties import bounty, bountyConfig
from ..gameObjects.items import shipItem
from ..users import basedGuild, basedUser
from ..databases.bountyDB import nameForDivision

botCommands.addHelpSection(3, "bounties")


async def dev_cmd_clear_bounties(message : discord.Message, args : str, isDM : bool):
    """developer command clearing all active bounties. If a guild ID is given, clear bounties in that guild.
    If 'all' is given, clear bounties in all guilds. If nothing is given, clear bounties in the calling guild.

    :param discord.Message message: the discord message calling the command
    :param str args: empty or a guild id
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    argsSplit = args.split(" ")
    if len(argsSplit) < 2:
        await message.reply(":x: Please specify a guild (ID, this or all) and division (name, tl or all)")
        return

    guildStr = argsSplit[0]
    divStr = args[len(guildStr) + 1:]

    allGuilds = False
    if guildStr in ["this", "here"]:
        callingBBGuild: basedGuild.BasedGuild = botState.guildsDB.getGuild(message.guild.id)
    elif guildStr == "all":
        allGuilds = True
    elif not lib.stringTyping.isInt(guildStr):
        await message.reply(":x: Please provide a guild ID, 'all' or 'this' as your first argument.")
        return
    else:
        guildID = int(guildStr)
        if not botState.guildsDB.idExists(guildID):
            await message.channel.send(f"Unrecognised guild ID: {guildID}")
            return
        callingBBGuild = botState.guildsDB.getGuild(guildID)
    if not allGuilds and callingBBGuild.bountiesDisabled:
        await message.reply(":x: Bounties are disabled in " \
                            + "that guild" if callingBBGuild.dcGuild is None else callingBBGuild.dcGuild.name \
                            + "!")
        return

    allDivs = False
    if divStr == "all":
        allDivs = True
    elif lib.stringTyping.isInt(divStr):
        useTL = True
        tl = int(divStr)
        if tl < cfg.minTechLevel or tl > cfg.maxTechLevel:
            await message.reply(f":x: Tech level must be between {cfg.minTechLevel} and {cfg.maxTechLevel}")
            return
    else:
        useTL = False
        if divStr not in cfg.bountyDivisionNames:
            await message.reply(f":x: Unknown division name. Must be one of: {', '.join(cfg.bountyDivisionNames)}")
            return
            

    if allGuilds:
        bbcClearTasks = lib.discordUtil.BasicScheduler()
        currentGuild: basedGuild.BasedGuild = None
        for currentGuild in botState.guildsDB.guilds.values():
            if not callingBBGuild.bountiesDisabled:
                if allDivs:
                    currentGuild.bountiesDB.clearAllBounties(includeEscaped=True)
                    if callingBBGuild.hasBountyBoardChannels:
                        for div in callingBBGuild.bountiesDB.divisions.values():
                            bbcClearTasks.add(div.bountyBoardChannel.clear())
                elif useTL:
                    currentGuild.bountiesDB.divisionForLevel(tl).clear(includeEscaped=True)
                else:
                    currentGuild.bountiesDB.divisionForName(divStr).clear(includeEscaped=True)
        if bbcClearTasks:
            await bbcClearTasks.wait()
            bbcClearTasks.logExceptions("bountiesDB", "dev_bounties", "dev_cmd_clear_bounties")
        await message.reply(":ballot_box_with_check: Active bounties cleared for all guilds.", mention_author=False)
    else:
        if callingBBGuild.bountiesDisabled:
            await message.reply((("'" + callingBBGuild.dcGuild.name + "' ") if callingBBGuild.dcGuild is not None \
                                        else "The requested guild ") + " has bounties disabled.",
                                mention_author=False)
            return

        if allDivs:
            divs = callingBBGuild.bountiesDB.divisions.values()
        elif lib.stringTyping.isInt(divStr):
            divs = [callingBBGuild.bountiesDB.divisionForLevel(tl)]
        else:
            divs = [callingBBGuild.bountiesDB.divisionForName(divStr)]

        for div in divs:
            if callingBBGuild.hasBountyBoardChannels:
                bbcTasks = lib.discordUtil.BasicScheduler()
                bbc = div.bountyBoardChannel
                for tlCriminals in div.bounties.values():
                    for crim in tlCriminals:
                        if bbc.hasMessageForCriminal(crim):
                            bbcTasks.add(bbc.removeCriminal(crim))
                if bbcTasks:
                    await bbcTasks.wait()
                    bbcTasks.logExceptions("bountiesDB", "dev_bounties", "dev_cmd_clear_bounties")
            await div.clear(includeEscaped=True)

        await message.reply(":ballot_box_with_check: Active bounties cleared" + ((" for '" + callingBBGuild.dcGuild.name \
                            + "'.") if callingBBGuild.dcGuild is not None else "."), mention_author=False)

botCommands.register("clear-bounties", dev_cmd_clear_bounties, 3, allowDM=True, helpSection="bounties", useDoc=True)


async def dev_cmd_get_cooldown(message : discord.Message, args : str, isDM : bool):
    """developer command printing the calling user's checking cooldown

    :param discord.Message message: the discord message calling the command
    :param str args: ignore
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    callingUser = botState.usersDB.getUser(message.author.id)
    diff = datetime.utcfromtimestamp(callingUser.bountyCooldownEnd) - datetime.utcnow()
    minutes = int(diff.total_seconds() / 60)
    seconds = int(diff.total_seconds() % 60)
    await message.reply(str(callingUser.bountyCooldownEnd) + " = " + str(minutes) + "m, " + str(seconds) + "s.", mention_author=False)
    await message.reply(datetime.utcfromtimestamp(callingUser.bountyCooldownEnd).strftime("%Hh%Mm%Ss"), mention_author=False)
    await message.reply(datetime.utcnow().strftime("%Hh%Mm%Ss"), mention_author=False)

botCommands.register("get-cool", dev_cmd_get_cooldown, 3, allowDM=True, helpSection="bounties", useDoc=True)


async def dev_cmd_reset_cooldown(message : discord.Message, args : str, isDM : bool):
    """developer command resetting the checking cooldown of the calling user, or the specified user if one is given

    :param discord.Message message: the discord message calling the command
    :param str args: string, can be empty or contain a user mention
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    # reset the calling user's cooldown if no user is specified
    if args == "":
        botState.usersDB.getUser(
            message.author.id).bountyCooldownEnd = datetime.utcnow().timestamp()
    # otherwise get the specified user's discord object and reset their cooldown.
    # [!] no validation is done.
    else:
        botState.usersDB.getUser(int(args.lstrip("<@!").rstrip(">"))).bountyCooldownEnd = datetime.utcnow().timestamp()
    await message.reply(mention_author=False, content="Done!")

botCommands.register("reset-cool", dev_cmd_reset_cooldown, 3, allowDM=True, helpSection="bounties", useDoc=True)


async def dev_cmd_setcheckcooldown(message : discord.Message, args : str, isDM : bool):
    """developer command setting the checking cooldown applied to users
    this does not update cfg and will be reverted on bot restart

    :param discord.Message message: the discord message calling the command
    :param str args: string containing an integer number of minutes
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    # verify a time was requested
    if args == "":
        await message.reply(mention_author=False, content=":x: please give the number of minutes!")
        return
    # verify the requested time is an integer
    if not lib.stringTyping.isInt(args):
        await message.reply(mention_author=False, content=":x: that's not a number!")
        return
    # update the checking cooldown amount
    cfg.timeouts.checkCooldown["minutes"] = int(args)
    await message.reply(mention_author=True, content="Done! *you still need to update the config file though* ")

botCommands.register("setcheckcooldown", dev_cmd_setcheckcooldown, 3, allowDM=True, helpSection="bounties", useDoc=True)


async def dev_cmd_setbountyperiodm(message : discord.Message, args : str, isDM : bool):
    """developer command setting the number of minutes in the new bounty generation period
    this does not update cfg and will be reverted on bot restart
    this does not affect the numebr of hours in the new bounty generation period

    :param discord.Message message: the discord message calling the command
    :param str args: string containing an integer number of minutes
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    # verify a time was given
    if args == "":
        await message.reply(mention_author=False, content=":x: please give the number of minutes!")
        return
    # verify the given time is an integer
    if not lib.stringTyping.isInt(args):
        await message.reply(mention_author=False, content=":x: that's not a number!")
        return
    # update the new bounty generation cooldown
    cfg.newBountyFixedDelta["minutes"] = int(args)
    botState.newBountyFixedDeltaChanged = True
    await message.reply(mention_author=True, content="Done! *you still need to update the config file though*")

botCommands.register("setbountyperiodm", dev_cmd_setbountyperiodm, 3, allowDM=True, helpSection="bounties", useDoc=True)


async def dev_cmd_setbountyperiodh(message : discord.Message, args : str, isDM : bool):
    """developer command setting the number of hours in the new bounty generation period
    this does not update cfg and will be reverted on bot restart
    this does not affect the numebr of minutes in the new bounty generation period

    :param discord.Message message: the discord message calling the command
    :param str args: string containing an integer number of hours
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    # verify a time was specified
    if args == "":
        await message.reply(mention_author=False, content=":x: please give the number of hours!")
        return
    # verify the given time is an integer
    if not lib.stringTyping.isInt(args):
        await message.reply(mention_author=False, content=":x: that's not a number!")
        return
    # update the bounty generation period
    botState.newBountyFixedDeltaChanged = True
    cfg.newBountyFixedDelta["hours"] = int(args)
    await message.reply(mention_author=True, content="Done! *you still need to update the file though*")

botCommands.register("setbountyperiodh", dev_cmd_setbountyperiodh, 3, allowDM=True, helpSection="bounties", useDoc=True)


async def dev_cmd_resetnewbountycool(message : discord.Message, args : str, isDM : bool):
    """developer command resetting the current bounty generation period,
    instantly generating a new bounty

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    argsSplit = args.split(" ")
    if len(argsSplit) < 2:
        await message.reply(":x: Please specify a guild (ID, this or all) and division (name, tl or all)")
        return

    guildStr = argsSplit[0]
    divStr = args[len(guildStr) + 1:]

    allGuilds = False
    if guildStr in ["this", "here"]:
        callingBBGuild: basedGuild.BasedGuild = botState.guildsDB.getGuild(message.guild.id)
    elif guildStr == "all":
        allGuilds = True
    elif not lib.stringTyping.isInt(guildStr):
        await message.reply(":x: Please provide a guild ID, 'all' or 'this' as your first argument.")
        return
    else:
        guildID = int(guildStr)
        if not botState.guildsDB.idExists(guildID):
            await message.reply(mention_author=False, content=f"Unrecognised guild ID: {guildID}")
            return
        callingBBGuild = botState.guildsDB.getGuild(guildID)
    if not allGuilds and callingBBGuild.bountiesDisabled:
        await message.reply(":x: Bounties are disabled in " \
                            + "that guild" if callingBBGuild.dcGuild is None else callingBBGuild.dcGuild.name \
                            + "!")
        return

    allDivs = False
    if divStr == "all":
        allDivs = True
    elif lib.stringTyping.isInt(divStr):
        useTL = True
        tl = int(divStr)
        if tl < cfg.minTechLevel or tl > cfg.maxTechLevel:
            await message.reply(f":x: Tech level must be between {cfg.minTechLevel} and {cfg.maxTechLevel}")
            return
    else:
        useTL = False
        if divStr not in cfg.bountyDivisionNames:
            await message.reply(f":x: Unknown division name. Must be one of: {', '.join(cfg.bountyDivisionNames)}")
            return

    if allGuilds:
        cooldownTasks = lib.discordUtil.BasicScheduler()
        currentGuild: basedGuild.BasedGuild = None
        for currentGuild in botState.guildsDB.guilds.values():
            if not currentGuild.bountiesDisabled:
                if allDivs:
                    cooldownTasks.add(currentGuild.bountiesDB.resetAllNewBountyTTs())
                elif useTL:
                    div = currentGuild.bountiesDB.divisionForLevel(tl)
                    if not div.isFull() or not div.hasMinTLBounty():
                        cooldownTasks.add(div.resetNewBountyCool())
                else:
                    div = currentGuild.bountiesDB.divisionForName(divStr)
                    if not div.isFull() or not div.hasMinTLBounty():
                        cooldownTasks.add(div.resetNewBountyCool())
        if cooldownTasks:
            await cooldownTasks.wait()
            cooldownTasks.logExceptions("bountiesDB", "dev_bounties", "dev_cmd_resetnewbountycool")
        await message.reply(mention_author=False, content=":ballot_box_with_check: All bounty cooldowns reset across all guilds!")
    else:
        if allDivs:
            await callingBBGuild.bountiesDB.resetAllNewBountyTTs()
            await message.reply(mention_author=False, content=":ballot_box_with_check: All bounty cooldowns reset for '" \
                                        + callingBBGuild.dcGuild.name + "'")
        elif useTL:
            div = callingBBGuild.bountiesDB.divisionForLevel(tl)
            if div.isFull() and div.hasMinTLBounty():
                await message.reply(mention_author=False, content=":x: That division is full!")
            else:
                await div.resetNewBountyCool()
                await message.reply(mention_author=False, content=":ballot_box_with_check: Division " + nameForDivision(div).title() \
                                            + " bounty cooldown reset for '" + callingBBGuild.dcGuild.name + "'")
        else:
            div = callingBBGuild.bountiesDB.divisionForName(divStr)
            if div.isFull() and div.hasMinTLBounty():
                await message.reply(mention_author=False, content=":x: That division is full!")
            else:
                await div.resetNewBountyCool()
                await message.reply(mention_author=False, content=":ballot_box_with_check: Division " + divStr.title() \
                                            + " bounty cooldown reset for '" + callingBBGuild.dcGuild.name + "'")


botCommands.register("resetnewbountycool", dev_cmd_resetnewbountycool, 3, allowDM=True, helpSection="bounties", useDoc=True)


async def dev_cmd_set_temp(message : discord.Message, args : str, isDM : bool):
    """developer command setting the activity level for the calling guild at the given tech level

    :param discord.Message message: the discord message calling the command
    :param str args: a tech level followed by an activity level
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    argsSplit = args.split(" ")
    if len(argsSplit) < 3:
        await message.reply(":x: Please specify a guild (ID, this or all), new temperature, and division (name, tl or all).")
        return

    guildStr = argsSplit[0]
    tempStr = argsSplit[1]
    divStr = args[len(guildStr + tempStr) + 1:]

    allGuilds = False
    if guildStr in ["this", "here"]:
        callingBBGuild: basedGuild.BasedGuild = botState.guildsDB.getGuild(message.guild.id)
    elif guildStr == "all":
        allGuilds = True
    elif not lib.stringTyping.isInt(guildStr):
        await message.reply(":x: Please provide a guild ID, 'all' or 'this' as your first argument.")
        return
    else:
        guildID = int(guildStr)
        if not botState.guildsDB.idExists(guildID):
            await message.reply(mention_author=False, content=f"Unrecognised guild ID: {guildID}")
            return
        callingBBGuild = botState.guildsDB.getGuild(guildID)
    if not allGuilds and callingBBGuild.bountiesDisabled:
        await message.reply(":x: Bounties are disabled in " \
                            + "that guild" if callingBBGuild.dcGuild is None else callingBBGuild.dcGuild.name \
                            + "!")
        return

    allDivs = False
    if divStr == "all":
        allDivs = True
    elif lib.stringTyping.isInt(divStr):
        useTL = True
        divTL = int(divStr)
        if divTL < cfg.minTechLevel or divTL > cfg.maxTechLevel:
            await message.reply(f":x: Tech level must be between {cfg.minTechLevel} and {cfg.maxTechLevel}")
            return
    else:
        useTL = False
        if divStr not in cfg.bountyDivisionNames:
            await message.reply(f":x: Unknown division name. Must be one of: {', '.join(cfg.bountyDivisionNames)}")
            return

    try:
        temp = float(tempStr)
    except ValueError:
        await message.reply(mention_author=False, content=":x: Incorrect temp, must be float '" + tempStr + "'")
    else:
        if allGuilds:
            currentGuild: basedGuild.BasedGuild = None
            for currentGuild in botState.guildsDB.guilds.values():
                if not currentGuild.bountiesDisabled:
                    if allDivs:
                        for div in currentGuild.bountiesDB.divisions.values():
                            div.setTemp(temp)
                    elif useTL:
                        div = currentGuild.bountiesDB.divisionForLevel(divTL)
                        div.setTemp(temp)
                    else:
                        div = currentGuild.bountiesDB.divisionForName(divStr)
                        div.setTemp(temp)
            await message.reply(f"Temperatures set to {temp} for {'all divisions in' if allDivs else nameForDivision(div)} all guilds!")
        else:
            if allDivs:
                for div in callingBBGuild.bountiesDB.divisions.values():
                    div.setTemp(temp)
            elif useTL:
                div = callingBBGuild.bountiesDB.divisionForLevel(divTL)
                div.setTemp(temp)
            else:
                div = callingBBGuild.bountiesDB.divisionForName(divStr)
                div.setTemp(temp)
            await message.reply(f"Temperatures set to {temp} for {'all divisions in' if allDivs else nameForDivision(div)} the guild!")

botCommands.register("set-temp", dev_cmd_set_temp, 3, allowDM=False, helpSection="bounties", useDoc=True)


async def dev_cmd_canmakebounty(message : discord.Message, args : str, isDM : bool):
    """developer command printing whether or not the given faction can accept new bounties
    If no guild ID is given, bounty spawning ability is checked for the calling guild

    :param discord.Message message: the discord message calling the command
    :param str args: string containing a faction followed by optionally a guild ID
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    argsSplit = args.split(" ")
    if len(argsSplit) < 2:
        await message.reply(":x: Please specify a guild (ID, this or here) and division (name, tl or all)")
        return

    guildStr = argsSplit[0]
    divStr = args[len(guildStr) + 1:]

    if guildStr in ["this", "here"]:
        callingBBGuild: basedGuild.BasedGuild = botState.guildsDB.getGuild(message.guild.id)
    elif not lib.stringTyping.isInt(guildStr):
        await message.reply(":x: Please provide a guild ID, 'all' or 'this' as your first argument.")
        return
    else:
        guildID = int(guildStr)
        if not botState.guildsDB.idExists(guildID):
            await message.reply(mention_author=False, content=f"Unrecognised guild ID: {guildID}")
            return
        callingBBGuild = botState.guildsDB.getGuild(guildID)
    if callingBBGuild.bountiesDisabled:
        await message.reply(":x: Bounties are disabled in " \
                            + "that guild" if callingBBGuild.dcGuild is None else callingBBGuild.dcGuild.name \
                            + "!")
        return

    allDivs = False
    if divStr == "all":
        allDivs = True
    elif lib.stringTyping.isInt(divStr):
        useTL = True
        tl = int(divStr)
        if tl < cfg.minTechLevel or tl > cfg.maxTechLevel:
            await message.reply(f":x: Tech level must be between {cfg.minTechLevel} and {cfg.maxTechLevel}")
            return
    else:
        useTL = False
        if divStr not in cfg.bountyDivisionNames:
            await message.reply(f":x: Unknown division name. Must be one of: {', '.join(cfg.bountyDivisionNames)}")
            return

    msgEmbed = lib.discordUtil.makeEmbed(callingBBGuild.dcGuild.name if callingBBGuild.dcGuild is not None else '' \
                                        + "Division has space for more bounties")
    if allDivs:
        for div in callingBBGuild.bountiesDB.divisions.values():
            msgEmbed.add_field(name=nameForDivision(div), value=str(not div.isFull() or not div.hasMinTLBounty()))
    elif useTL:
        div = callingBBGuild.bountiesDB.divisionForLevel(tl)
        msgEmbed.add_field(name=nameForDivision(div), value=str(not div.isFull() or not div.hasMinTLBounty()))
    else:
        div = callingBBGuild.bountiesDB.divisionForName(divStr)
        msgEmbed.add_field(name=nameForDivision(div), value=str(not div.isFull() or not div.hasMinTLBounty()))

    await message.reply(embed=msgEmbed)

botCommands.register("canmakebounty", dev_cmd_canmakebounty, 3, allowDM=False, helpSection="bounties", useDoc=True)


async def dev_cmd_make_bounty(message : discord.Message, args : str, isDM : bool):
    """developer command making a new bounty
    args should be separated by a space and then a plus symbol
    if no args except guild are given, generate a new bounty at complete random
    if only one argument except guild is given it is assumed to be a difficulty level, and a bounty is generated at that TL
    if two arguments except guild are given, they are assumed to be TL and faction
    otherwise, all 10 arguments required to generate a bounty must be given
    the route should be separated by only commas and no spaces. the endTime should be a UTC timestamp. Any argument can be
    given as 'auto' to be either inferred or randomly generated
    as such, '$make-bounty +<guild>' is an alias for:
    '$make-bounty +<guild> +auto +auto +auto +auto +auto +auto +auto +auto +auto +auto'
    Args are: guild, difficulty, faction, name, route, start sys, end sys, answer sys, reward pool (-loadout), end time, icon

    :param discord.Message message: the discord message calling the command
    :param str args: can be empty, can be '+<guild> +<TL>', or can be '+<guild> +<TL> +<faction> +<name> +<route> +<start>
                        +<end> +<answer> +<reward> +<endtime> +<icon>'
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    guildStr = args.split("+")[0].strip()
    args = args[len(guildStr):].lstrip()
    argsSplit = args.split("+")
    allGuilds = False
    if guildStr in ["this", "here"]:
        callingBBGuild: basedGuild.BasedGuild = botState.guildsDB.getGuild(message.guild.id)
    elif guildStr == "all":
        allGuilds = True
    elif not lib.stringTyping.isInt(guildStr):
        await message.reply(":x: Please provide a guild ID, 'all' or 'this' as your first argument.")
        return
    else:
        guildID = int(guildStr)
        if not botState.guildsDB.idExists(guildID):
            await message.reply(mention_author=False, content=f"Unrecognised guild ID: {guildID}")
            return
        callingBBGuild = botState.guildsDB.getGuild(guildID)
    if not allGuilds and callingBBGuild.bountiesDisabled:
        await message.reply(":x: Bounties are disabled in " \
                            + "that guild" if callingBBGuild.dcGuild is None else callingBBGuild.dcGuild.name \
                            + "!")
        return
    if not allGuilds and not callingBBGuild.bountiesDB.canMakeBounty():
        await message.reply(":x: No space for bounties in this guild!")
        return

    # if no args were given, generate a completely random bounty
    if args == "":
        newTL = -1
        config = bountyConfig.BountyConfig()
        # newBounty = bounty.Bounty(owningDB=callingBBGuild.bountiesDB)
    # if only one argument was given, use it as a TL
    elif len(argsSplit) == 2:
        newTL = int(argsSplit[1])
        config = bountyConfig.BountyConfig(techLevel=newTL)
    # if two are given, assume TL and faction name
    elif len(argsSplit) == 3:
        newTL = int(argsSplit[1].rstrip(" "))
        config = bountyConfig.BountyConfig(techLevel=newTL, faction=argsSplit[2])
    elif len(argsSplit) != 11:
        await message.reply("Incorrect number of arguments. Formats:\n" \
                            + "- +`<TL>`\n" \
                            + "- +`<TL>` +`<faction>`\n" \
                            + "- +`<TL>' +`<faction>` +`<name>` +`<route>` +`<start>` " \
                                + "+`<end>` +`<answer>` +`<reward>` +`<endtime>` +`<icon>`")
        return

    # if all args were given, generate a completely custom bounty
    # 10 args plus account for empty string at the start of the split = split of 11 elements
    else:
        # track whether a builtIn criminal was requested
        builtIn = False
        builtInCrimObj = None
        # [1:] remove empty string before + splits
        bData = argsSplit[1:]

        newTL = bData[0].rstrip(" ")
        if newTL == "auto":
            newTL = -1
        elif not lib.stringTyping.isInt(newTL) or int(newTL) < cfg.minTechLevel or int(newTL) > cfg.maxTechLevel:
            await message.reply(f":x: Invalid tech level, must be a number between {cfg.minTechLevel} and {cfg.maxTechLevel}: {newTL}")
            return
        else:
            newTL = int(newTL)

        # parse the given faction
        newFaction = bData[1].rstrip(" ")
        if newFaction == "auto":
            newFaction = ""

        # parse the given criminal name
        newName = bData[2].rstrip(" ").title()
        if newName == "Auto":
            newName = ""
        else:
            # if a criminal name was given, see if it corresponds to a builtIn criminal
            for crim in bbData.builtInCriminalObjs.values():
                if crim.isCalled(newName):
                    builtIn = True
                    builtInCrimObj = crim
                    newName = crim.name
                    break

            # if a criminal name was given, ensure it does not already exist as a bounty
            if newName != "" and callingBBGuild.bountiesDB.bountyNameExists(newName):
                await message.reply(mention_author=False, content=":x: That pilot is already wanted!")
                return

        # parse the given route
        newRoute = bData[3].rstrip(" ")
        if newRoute == "auto":
            newRoute = []
        else:
            newRoute = bData[3].split(",")
            newRoute[-1] = newRoute[-1].rstrip(" ")

        # parse the given start system
        newStart = bData[4].rstrip(" ")
        if newStart == "auto":
            newStart = ""

        # parse the given end system
        newEnd = bData[5].rstrip(" ")
        if newEnd == "auto":
            newEnd = ""

        # parse the given answer system
        newAnswer = bData[6].rstrip(" ")
        if newAnswer == "auto":
            newAnswer = ""

        # parse the given reward amount
        newReward = bData[7].rstrip(" ")
        if newReward == "auto":
            newReward = -1
        newReward = int(newReward)

        # parse the given end time
        newEndTime = bData[8].rstrip(" ")
        if newEndTime == "auto":
            newEndTime = -1.0
        else:
            newEndTime = float(newEndTime)
            try:
                endTimeDT = datetime.utcfromtimestamp(newEndTime)
            except:
                await message.reply(":x: Invalid end time!")
                return
            if endTimeDT - datetime.utcnow() < timedelta(minutes=1):
                await message.reply(":x: Please provide an end time at least one minute in the future!")
                return

        # parse the given icon
        newIcon = bData[9].rstrip(" ")
        if newIcon == "auto":
            newIcon = "" if not builtIn else builtInCrimObj.icon

        # special bounty generation for builtIn criminals
        if builtIn:
            config = bountyConfig.BountyConfig(faction=newFaction, route=newRoute,
                                                start=newStart, end=newEnd, answer=newAnswer,
                                                reward=newReward, endTime=newEndTime,
                                                isPlayer=False, icon=newIcon, name=builtInCrimObj.name, techLevel=newTL)
        # normal bounty generation for custom criminals
        else:
            config = bountyConfig.BountyConfig(faction=newFaction, name=newName, route=newRoute,
                                                start=newStart, end=newEnd, answer=newAnswer,
                                                reward=newReward, endTime=newEndTime,
                                                isPlayer=False, icon=newIcon, techLevel=newTL)

    if allGuilds:
        currentGuild: basedGuild.BasedGuild = None
        spawnTasks = lib.discordUtil.BasicScheduler()
        for currentGuild in botState.guildsDB.guilds.values():
            if not currentGuild.bountiesDisabled and currentGuild.bountiesDB.canMakeBounty():
                if newTL == -1:
                    div = random.choice(list(currentGuild.bountiesDB.divisions.values()))
                    while div.isFull() and div.hasMinTLBounty():
                        div = random.choice(list(currentGuild.bountiesDB.divisions.values()))
                else:
                    div = currentGuild.bountiesDB.divisionForLevel(newTL)
                if div.isFull() and (newTL != div.minLevel or (newTL == div.minLevel and div.hasMinTLBounty())):
                    await message.reply(f"The {nameForDivision(div)} division is full in guild {currentGuild.dcGuild.name if currentGuild.dcGuild is not None else ''}#{currentGuild.id}, skipping this guild")
                else:
                    newBounty = bounty.Bounty(division=div, config=config.generate(div))
                    currentGuild.bountiesDB.addBounty(newBounty)
                    spawnTasks.add(currentGuild.announceNewBounty(newBounty))
        if spawnTasks:
            await spawnTasks.wait()
            spawnTasks.logExceptions("bountiesDB", "dev_bounties", "dev_cmd_make_bounty")
        await message.reply(mention_author=False, content=f"Criminal spawned into {len(spawnTasks)} guilds!")
    else:
        if newTL == -1:
            div = random.choice(list(callingBBGuild.bountiesDB.divisions.values()))
            while div.isFull() and div.hasMinTLBounty():
                div = random.choice(list(callingBBGuild.bountiesDB.divisions.values()))
        else:
            div = callingBBGuild.bountiesDB.divisionForLevel(newTL)
        if div.isFull() and (newTL != div.minLevel or (newTL == div.minLevel and div.hasMinTLBounty())):
            await message.reply(f"The {nameForDivision(div)} division is full in that guild!")
        else:
            newBounty = bounty.Bounty(division=div, config=config.generate(div))
            callingBBGuild.bountiesDB.addBounty(newBounty)
            await callingBBGuild.announceNewBounty(newBounty)
            await message.reply(mention_author=False, content=f"Criminal spawned!")


botCommands.register("make-bounty", dev_cmd_make_bounty, 3, forceKeepArgsCasing=True, allowDM=True, helpSection="bounties",
                    useDoc=True)


async def dev_cmd_make_player_bounty(message : discord.Message, args : str, isDM : bool):
    """developer command making a new PLAYER bounty
    args should be separated by a space and then a plus symbol
    the first argument should be a guild, and the second should be a user mention or ID.
    if no other args are given, generate a new bounty at complete random, for the specified user
    the user's bounty hunter level is used as the bounty's difficulty.
    THe user's active ship is used as the bounty's ship.
    if one other argument is given it is assumed to be a faction, and a bounty is generated for that faction for the
    specified user
    otherwise, all 10 arguments required to generate a bounty must be given
    the route should be separated by only commas and no spaces. the endTime should be a UTC timestamp. Any argument can
    be given as 'auto' to be either inferred or randomly generated

    as such, '$make-bounty +<guild> +<player>' is an alias for:
    '$make-bounty +<guild> +<player> +auto +auto +auto +auto +auto +auto +auto +auto +auto'
    Args are: guild, player, difficulty, faction, route, start sys, end sys, answer sys, reward pool (-loadout), end time, icon

    :param discord.Message message: the discord message calling the command
    :param str args: can be empty, can be '+<guild> +<player>', or can be '+<guild> +<player> +<faction> +<route> +<start>
                        +<end> +<answer> +<reward> +<endtime> +<icon>'
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    guildStr = args.split("+")[0].strip()
    args = args[len(guildStr):].lstrip()
    argsSplit = args.split("+")[1:]
    allGuilds = False
    if guildStr in ["this", "here"]:
        callingBBGuild: basedGuild.BasedGuild = botState.guildsDB.getGuild(message.guild.id)
    elif guildStr == "all":
        allGuilds = True
    elif not lib.stringTyping.isInt(guildStr):
        await message.reply(":x: Please provide a guild ID, 'all' or 'this' as your first argument.")
        return
    else:
        guildID = int(guildStr)
        if not botState.guildsDB.idExists(guildID):
            await message.reply(mention_author=False, content=f"Unrecognised guild ID: {guildID}")
            return
        callingBBGuild = botState.guildsDB.getGuild(guildID)
    if not allGuilds and callingBBGuild.bountiesDisabled:
        await message.reply(":x: Bounties are disabled in " \
                            + "that guild" if callingBBGuild.dcGuild is None else callingBBGuild.dcGuild.name \
                            + "!")
        return
    if not allGuilds and not callingBBGuild.bountiesDB.canMakeBounty():
        await message.reply(":x: No space for bounties in this guild!")
        return

    # if no arguments were given, generate a completely random bounty
    # if only one argument was given, use it as a faction
    elif len(argsSplit) in (1, 2):
        newName = argsSplit[0]
        if lib.stringTyping.isInt(newName):
            newName = int(newName)
        elif lib.stringTyping.isMention(newName):
            newName = int(argsSplit[0].lstrip("<@!").rstrip(">"))
        # verify the requested user
        requestedUser = botState.client.get_user(newName)
        if requestedUser is None:
            await message.reply(mention_author=False, content=":x: Player not found!")
            return
        
        if botState.usersDB.idExists(requestedUser.id):
            requestedBUser: basedUser.BasedUser = botState.usersDB.getUser(requestedUser.id)
            activeShip = requestedBUser.activeShip
            if requestedBUser.classicModeEnabled:
                newTL = cfg.minTechLevel
            else:
                newTL = gameMaths.calculateUserBountyHuntingLevel(requestedBUser.bountyHuntingXP)
        else:
            activeShip = shipItem.Ship.fromDict(basedUser.defaultShipLoadoutDict)
            newTL = cfg.minTechLevel

        # create a new bounty at random for the specified user
        config = bountyConfig.BountyConfig(name="<@" + str(newName) + ">", isPlayer=True,
                                            icon=str(requestedUser.avatar_url_as(size=64)),
                                            aliases=[lib.discordUtil.userTagOrDiscrim(newName)],
                                            techLevel=newTL, activeShip=activeShip,
                                            faction=argsSplit[1] if len(argsSplit) == 2 else "")

    elif len(argsSplit) != 9:
        await message.reply("Incorrect number of arguments. Formats:\n" \
                            + "- +`<player>`\n" \
                            + "- +`<player>` +`<faction>`\n" \
                            + "- +`<player>` +`<faction>` +`<route>` +`<start>` " \
                                + "+`<end>` +`<answer>` +`<reward>` +`<endtime>` +`<icon>`")
        return

    # if all args were given, generate a completely custom bounty
    # 9 args plus account for empty string at the start of the split = split of 10 elements
    else:
        # track whether a builtIn criminal was requested
        builtIn = False
        builtInCrimObj = None
        # [1:] remove empty string before + splits
        bData = argsSplit[1:]

        newName = argsSplit[0]
        if lib.stringTyping.isInt(newName):
            newName = int(newName)
        elif lib.stringTyping.isMention(newName):
            newName = int(argsSplit[0].lstrip("<@!").rstrip(">"))
        # verify the requested user
        requestedUser = botState.client.get_user(newName)
        if requestedUser is None:
            await message.reply(mention_author=False, content=":x: Player not found!")
            return

        # parse the given faction
        newFaction = bData[1].rstrip(" ")
        if newFaction == "auto":
            newFaction = ""

        # parse the given route
        newRoute = bData[2].rstrip(" ")
        if newRoute == "auto":
            newRoute = []
        else:
            newRoute = bData[2].split(",")
            newRoute[-1] = newRoute[-1].rstrip(" ")

        # parse the given start system
        newStart = bData[3].rstrip(" ")
        if newStart == "auto":
            newStart = ""

        # parse the given end system
        newEnd = bData[4].rstrip(" ")
        if newEnd == "auto":
            newEnd = ""

        # parse the given answer system
        newAnswer = bData[5].rstrip(" ")
        if newAnswer == "auto":
            newAnswer = ""

        # parse the given reward amount
        newReward = bData[6].rstrip(" ")
        if newReward == "auto":
            newReward = -1
        newReward = int(newReward)

        # parse the given end time
        newEndTime = bData[7].rstrip(" ")
        if newEndTime == "auto":
            newEndTime = -1.0
        else:
            newEndTime = float(newEndTime)
            try:
                endTimeDT = datetime.utcfromtimestamp(newEndTime)
            except:
                await message.reply(":x: Invalid end time!")
                return
            if endTimeDT - datetime.utcnow() < timedelta(minutes=1):
                await message.reply(":x: Please provide an end time at least one minute in the future!")
                return

        # parse the given icon
        newIcon = bData[8].rstrip(" ")
        if newIcon == "auto":
            newIcon = "" if not builtIn else builtInCrimObj.icon
        
        if botState.usersDB.idExists(requestedUser.id):
            requestedBUser: basedUser.BasedUser = botState.usersDB.getUser(requestedUser.id)
            activeShip = requestedBUser.activeShip
            if requestedBUser.classicModeEnabled:
                newTL = cfg.minTechLevel
            else:
                newTL = gameMaths.calculateUserBountyHuntingLevel(requestedBUser.bountyHuntingXP)
        else:
            activeShip = shipItem.Ship.fromDict(basedUser.defaultShipLoadoutDict)
            newTL = cfg.minTechLevel

        config = bountyConfig.BountyConfig(name="<@" + str(newName) + ">", isPlayer=True,
                                            icon=str(requestedUser.avatar_url_as(size=64)),
                                            aliases=[lib.discordUtil.userTagOrDiscrim(newName)],
                                            techLevel=newTL, activeShip=activeShip,
                                            faction=newFaction, route=newRoute,
                                            start=newStart, end=newEnd, answer=newAnswer,
                                            reward=newReward, endTime=newEndTime)

    if allGuilds:
        currentGuild: basedGuild.BasedGuild = None
        spawnTasks = lib.discordUtil.BasicScheduler()
        for currentGuild in botState.guildsDB.guilds.values():
            if not currentGuild.bountiesDisabled:
                # ensure the player does not already exist as a bounty
                if currentGuild.bountiesDB.bountyNameExists(f"<@{newName}>"):
                    await message.reply(mention_author=False, content=f"Skipping guild: {currentGuild.dcGuild.name if currentGuild.dcGuild is not None else ''}#{currentGuild.id} - criminal with this name already exists")
                else:
                    div = currentGuild.bountiesDB.divisionForLevel(newTL)
                    if div.isFull() and (newTL != div.minLevel or (newTL == div.minLevel and div.hasMinTLBounty())):
                        await message.reply(f"The {nameForDivision(div)} division is full in guild {currentGuild.dcGuild.name if currentGuild.dcGuild is not None else ''}#{currentGuild.id}, skipping this guild")
                    else:
                        newBounty = bounty.Bounty(division=div, config=config.generate(div))
                        currentGuild.bountiesDB.addBounty(newBounty)
                        spawnTasks.add(currentGuild.announceNewBounty(newBounty))
        if spawnTasks:
            await spawnTasks.wait()
            spawnTasks.logExceptions("bountiesDB", "dev_bounties", "dev_cmd_make_bounty")
        await message.reply(mention_author=False, content=f"Criminal spawned into {len(spawnTasks)} guilds!")
    else:
        if callingBBGuild.bountiesDB.bountyNameExists(f"<@{newName}>"):
            await message.reply(mention_author=False, content="A criminal with the same name already exists in that guild!")
        else:
            div = callingBBGuild.bountiesDB.divisionForLevel(newTL)
            if div.isFull() and (newTL != div.minLevel or (newTL == div.minLevel and div.hasMinTLBounty())):
                await message.reply(f"The {nameForDivision(div)} division is full in that guild!")
            else:
                newBounty = bounty.Bounty(division=div, config=config.generate(div))
                callingBBGuild.bountiesDB.addBounty(newBounty)
                await callingBBGuild.announceNewBounty(newBounty)
                await message.reply(mention_author=False, content=f"Criminal spawned!")


botCommands.register("make-player-bounty", dev_cmd_make_player_bounty, 3, forceKeepArgsCasing=True, allowDM=True,
                        helpSection="bounties", useDoc=True)


async def dev_cmd_set_bounty_xp(message : discord.Message, args : str, isDM : bool):
    """developer command setting the requested user's bounty hunting xp.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing a user mention and an integer amount of xp
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    argsSplit = args.split(" ")
    # verify both a user and a balance were given
    if len(argsSplit) < 2:
        await message.reply(mention_author=False, content=":x: Please give a user mention followed by the new xp!")
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

    newXP = int(argsSplit[1])
    newLevel = gameMaths.calculateUserBountyHuntingLevel(newXP)

    requestedBBUser: basedUser.BasedUser = None
    if not botState.usersDB.idExists(requestedUser.id):
        requestedBBUser = botState.usersDB.addID(requestedUser.id)
    else:
        requestedBBUser = botState.usersDB.getUser(requestedUser.id)

    if requestedBBUser.classicModeEnabled:
        await message.reply(":x: That user has classic mode enabled!")
        return

    # Handle bounty alert roles updates
    if requestedBBUser.hasHomeGuild and botState.guildsDB.idExists(requestedBBUser.homeGuildID):
        homeBGuild: basedGuild.BasedGuild = botState.guildsDB.getGuild(requestedBBUser.homeGuildID)
        if homeBGuild.hasBountyAlertRoles:
            tl = gameMaths.calculateUserBountyHuntingLevel(requestedBBUser.bountyHuntingXP)
            oldDiv = homeBGuild.bountiesDB.divisionForLevel(tl)
            oldRole = homeBGuild.dcGuild.get_role(oldDiv.alertRoleID)
            requestedMember = homeBGuild.dcGuild.get_member(requestedUser.id)
            if oldRole is None:
                    await message.reply(mention_author=False, content=f":woozy_face: I can't find the {nameForDivision(oldDiv).title()}" \
                                                + " division bounty alerts role, did it get deleted?")
            elif oldRole in requestedMember.roles:
                newDiv = homeBGuild.bountiesDB.divisionForLevel(newLevel)
                newRole = homeBGuild.dcGuild.get_role(newDiv.alertRoleID)
                if newRole is None:
                    await message.reply(mention_author=False, content=":woozy_face: I can't find the " \
                                            + f"{nameForDivision(newDiv).title()} division's bounty alerts " \
                                            + "role, did it get deleted?")
                
                if oldRole is not None or newRole is not None:
                    await homeBGuild.levelUpSwapRoles(requestedMember, message.channel, oldRole, newRole)

    # update the balance
    requestedBBUser.bountyHuntingXP = newXP
    await message.reply(mention_author=False, content="Done!")

botCommands.register("set-bounty-xp", dev_cmd_set_bounty_xp, 3, allowDM=True, helpSection="bounties", useDoc=True)


async def dev_cmd_set_bounty_level(message : discord.Message, args : str, isDM : bool):
    """developer command setting the requested user's bounty hunting LEVEL.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing a user mention and an integer amount of xp
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    argsSplit = args.split(" ")
    # verify both a user and a balance were given
    if len(argsSplit) < 2:
        await message.reply(mention_author=False, content=":x: Please give a user mention followed by the new level!")
        return
    # verify the requested balance is an integer
    if not lib.stringTyping.isInt(argsSplit[1]):
        await message.reply(mention_author=False, content=":x: that's not a number!")
        return

    # verify the requested user
    requestedUser = botState.client.get_user(
        int(argsSplit[0].lstrip("<@!").rstrip(">")))
    if requestedUser is None:
        await message.reply(mention_author=False, content=":x: invalid user!!")
        return

    newXP = gameMaths.bountyHuntingXPForLevel(int(argsSplit[1]))
    await dev_cmd_set_bounty_xp(message, f"{requestedUser.mention} {newXP}", isDM)

botCommands.register("set-bounty-level", dev_cmd_set_bounty_level, 3, allowDM=True, helpSection="bounties", useDoc=True) 


async def dev_cmd_measure_temps(message : discord.Message, args : str, isDM : bool):
    """developer command fetching the current activity temperatures in the calling guild.

    :param discord.Message message: the discord message calling the command
    :param str args: a string containing a guild ID, 'this' or 'here'
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if not args:
        await message.reply(":x: Please specify a guild (ID, this or all)")
        return

    if args in ["this", "here"]:
        callingBBGuild: basedGuild.BasedGuild = botState.guildsDB.getGuild(message.guild.id)
    elif not lib.stringTyping.isInt(args):
        await message.reply(":x: Please provide a guild ID, 'here' or 'this' as your only argument.")
        return
    else:
        guildID = int(args)
        if not botState.guildsDB.idExists(guildID):
            await message.reply(mention_author=False, content=f"Unrecognised guild ID: {guildID}")
            return
        callingBBGuild = botState.guildsDB.getGuild(guildID)
    if callingBBGuild.bountiesDisabled:
        await message.reply(":x: Bounties are disabled in " \
                            + "that guild" if callingBBGuild.dcGuild is None else callingBBGuild.dcGuild.name \
                            + "!")
        return

    activityEmbed = lib.discordUtil.makeEmbed("Activity Temperatures", desc=message.guild.name, col=discord.Colour.random(),
                    thumb=message.guild.icon_url_as(size=64))
    for div in callingBBGuild.bountiesDB.divisions.values():
        activityEmbed.add_field(name=f"{nameForDivision(div).title()} Division", value=div.temperature)
    await message.author.send(embed=activityEmbed)

botCommands.register("measure-temps", dev_cmd_measure_temps, 3, allowDM=False,
                        helpSection="bounties", useDoc=True)


async def dev_cmd_decay_temps(message : discord.Message, args : str, isDM : bool):
    """developer command decaying the activity temperatures of the calling guild

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    argsSplit = args.split(" ")
    if len(argsSplit) < 2:
        await message.reply(":x: Please specify a guild (ID, this or all) and division (name, tl or all)")
        return

    guildStr = argsSplit[0]
    divStr = args[len(guildStr) + 1:]

    allGuilds = False
    if guildStr in ["this", "here"]:
        callingBBGuild: basedGuild.BasedGuild = botState.guildsDB.getGuild(message.guild.id)
    elif guildStr == "all":
        allGuilds = True
    elif not lib.stringTyping.isInt(guildStr):
        await message.reply(":x: Please provide a guild ID, 'all' or 'this' as your first argument.")
        return
    else:
        guildID = int(guildStr)
        if not botState.guildsDB.idExists(guildID):
            await message.reply(mention_author=False, content=f"Unrecognised guild ID: {guildID}")
            return
        callingBBGuild = botState.guildsDB.getGuild(guildID)
    if not allGuilds and callingBBGuild.bountiesDisabled:
        await message.reply(":x: Bounties are disabled in " \
                            + "that guild" if callingBBGuild.dcGuild is None else callingBBGuild.dcGuild.name \
                            + "!")
        return

    allDivs = False
    if divStr == "all":
        allDivs = True
    elif lib.stringTyping.isInt(divStr):
        useTL = True
        tl = int(divStr)
        if tl < cfg.minTechLevel or tl > cfg.maxTechLevel:
            await message.reply(f":x: Tech level must be between {cfg.minTechLevel} and {cfg.maxTechLevel}")
            return
    else:
        useTL = False
        if divStr not in cfg.bountyDivisionNames:
            await message.reply(f":x: Unknown division name. Must be one of: {', '.join(cfg.bountyDivisionNames)}")
            return
    
    if allGuilds:
        currentGuild: basedGuild.BasedGuild = None
        for currentGuild in botState.guildsDB.guilds.values():
            if not currentGuild.bountiesDisabled:
                if allDivs:
                    for div in currentGuild.bountiesDB.divisions.values():
                        div.decayTemp()
                elif useTL:
                    div = currentGuild.bountiesDB.divisionForLevel(tl)
                    div.decayTemp()
                else:
                    div = currentGuild.bountiesDB.divisionForName(divStr)
                    div.decayTemp()
        await message.reply("done!")
    else:
        if allDivs:
            for div in callingBBGuild.bountiesDB.divisions.values():
                div.decayTemp()
        elif useTL:
            div = callingBBGuild.bountiesDB.divisionForLevel(tl)
            div.decayTemp()
        else:
            div = callingBBGuild.bountiesDB.divisionForName(divStr)
            div.decayTemp()
        await message.reply("Activity temperatures decayed for guild.")

botCommands.register("decay-temps", dev_cmd_decay_temps, 3, allowDM=False,
                        helpSection="bounties", useDoc=True)


async def dev_cmd_reset_temps(message : discord.Message, args : str, isDM : bool):
    """developer command resetting the activity temperatures of the calling guild

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    argsSplit = args.split(" ")
    if len(argsSplit) < 2:
        await message.reply(":x: Please specify a guild (ID, this or all) and division (name, tl or all)")
        return

    guildStr = argsSplit[0]
    divStr = args[len(guildStr) + 1:]

    allGuilds = False
    if guildStr in ["this", "here"]:
        callingBBGuild: basedGuild.BasedGuild = botState.guildsDB.getGuild(message.guild.id)
    elif guildStr == "all":
        allGuilds = True
    elif not lib.stringTyping.isInt(guildStr):
        await message.reply(":x: Please provide a guild ID, 'all' or 'this' as your first argument.")
        return
    else:
        guildID = int(guildStr)
        if not botState.guildsDB.idExists(guildID):
            await message.reply(mention_author=False, content=f"Unrecognised guild ID: {guildID}")
            return
        callingBBGuild = botState.guildsDB.getGuild(guildID)
    if not allGuilds and callingBBGuild.bountiesDisabled:
        await message.reply(":x: Bounties are disabled in " \
                            + "that guild" if callingBBGuild.dcGuild is None else callingBBGuild.dcGuild.name \
                            + "!")
        return

    allDivs = False
    if divStr == "all":
        allDivs = True
    elif lib.stringTyping.isInt(divStr):
        useTL = True
        tl = int(divStr)
        if tl < cfg.minTechLevel or tl > cfg.maxTechLevel:
            await message.reply(f":x: Tech level must be between {cfg.minTechLevel} and {cfg.maxTechLevel}")
            return
    else:
        useTL = False
        if divStr not in cfg.bountyDivisionNames:
            await message.reply(f":x: Unknown division name. Must be one of: {', '.join(cfg.bountyDivisionNames)}")
            return
    
    if allGuilds:
        currentGuild: basedGuild.BasedGuild = None
        for currentGuild in botState.guildsDB.guilds.values():
            if not currentGuild.bountiesDisabled:
                if allDivs:
                    for div in currentGuild.bountiesDB.divisions.values():
                        div.setTemp(cfg.minGuildActivity)
                elif useTL:
                    div = currentGuild.bountiesDB.divisionForLevel(tl)
                    div.setTemp(cfg.minGuildActivity)
                else:
                    div = currentGuild.bountiesDB.divisionForName(divStr)
                    div.setTemp(cfg.minGuildActivity)
        await message.reply("done!")
    else:
        if allDivs:
            for div in callingBBGuild.bountiesDB.divisions.values():
                div.setTemp(cfg.minGuildActivity)
        elif useTL:
            div = callingBBGuild.bountiesDB.divisionForLevel(tl)
            div.setTemp(cfg.minGuildActivity)
        else:
            div = callingBBGuild.bountiesDB.divisionForName(divStr)
            div.setTemp(cfg.minGuildActivity)
        await message.reply("Activity temperatures reset for guild.")

botCommands.register("reset-temps", dev_cmd_reset_temps, 3, allowDM=False,
                        helpSection="bounties", useDoc=True)


async def dev_cmd_current_delay(message : discord.Message, args : str, isDM : bool):
    """developer command DMing the calling user with the current delays on all new bounty TTs for the calling guild
    or if a tl is provided, just the current delay for that TL's TT

    :param discord.Message message: the discord message calling the command
    :param str args: nothing, or a single tech level
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    argsSplit = args.split(" ")
    if len(argsSplit) < 2:
        await message.reply(":x: Please specify a guild (ID, this or all) and division (name, tl or all)")
        return

    guildStr = argsSplit[0]
    divStr = args[len(guildStr) + 1:]

    if guildStr in ["this", "here"]:
        callingBBGuild: basedGuild.BasedGuild = botState.guildsDB.getGuild(message.guild.id)
    elif not lib.stringTyping.isInt(guildStr):
        await message.reply(":x: Please provide a guild ID, 'here' or 'this' as your first argument.")
        return
    else:
        guildID = int(guildStr)
        if not botState.guildsDB.idExists(guildID):
            await message.reply(mention_author=False, content=f"Unrecognised guild ID: {guildID}")
            return
        callingBBGuild = botState.guildsDB.getGuild(guildID)
    if callingBBGuild.bountiesDisabled:
        await message.reply(":x: Bounties are disabled in " \
                            + "that guild" if callingBBGuild.dcGuild is None else callingBBGuild.dcGuild.name \
                            + "!")
        return

    allDivs = False
    if divStr == "all":
        allDivs = True
    elif lib.stringTyping.isInt(divStr):
        useTL = True
        tl = int(divStr)
        if tl < cfg.minTechLevel or tl > cfg.maxTechLevel:
            await message.reply(f":x: Tech level must be between {cfg.minTechLevel} and {cfg.maxTechLevel}")
            return
    else:
        useTL = False
        if divStr not in cfg.bountyDivisionNames:
            await message.reply(f":x: Unknown division name. Must be one of: {', '.join(cfg.bountyDivisionNames)}")
            return

    if allDivs:
        activityEmbed = lib.discordUtil.makeEmbed("Current New Bounty Delays", desc=message.guild.name,
                        col=discord.Colour.random(), thumb=message.guild.icon_url_as(size=64))
        for div in callingBBGuild.bountiesDB.divisions.values():
            if div.isFull() and div.hasMinTLBounty():
                activityEmbed.add_field(name=nameForDivision(div),
                                        value="<DIVISION FULL>")
            else:
                activityEmbed.add_field(name=nameForDivision(div),
                                        value=lib.timeUtil.td_format_noYM(div.newBountyTT.expiryDelta)
                                                + "\nExpiring " + div.newBountyTT.expiryTime.strftime("%B %d %H %M %S"))
        await message.author.send(embed=activityEmbed)
    else:
        if useTL:
            div = callingBBGuild.bountiesDB.divisionForLevel(tl)
        else:
            div = callingBBGuild.bountiesDB.divisionForName(divStr)
        if div.isFull() and div.hasMinTLBounty():
            await message.author.send("<DIVISION FULL>")
        else:
            await message.author.send(lib.timeUtil.td_format_noYM(div.newBountyTT.expiryDelta)
                                        + "\nExpiring " + div.newBountyTT.expiryTime.strftime("%B %d %H %M %S"))

botCommands.register("current-delay", dev_cmd_current_delay, 3, allowDM=False,
                        helpSection="bounties", useDoc=True)


async def dev_cmd_current_max_bounties(message : discord.Message, args : str, isDM : bool):
    """developer command DMing the calling user with the current max bounties for all TLs for the calling guild
    or if a tl is provided, just the current max bounties for that TL

    :param discord.Message message: the discord message calling the command
    :param str args: nothing, or a single tech level
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    argsSplit = args.split(" ")
    if len(argsSplit) < 2:
        await message.reply(":x: Please specify a guild (ID, this or all) and division (name, tl or all)")
        return

    guildStr = argsSplit[0]
    divStr = args[len(guildStr) + 1:]

    if guildStr in ["this", "here"]:
        callingBBGuild: basedGuild.BasedGuild = botState.guildsDB.getGuild(message.guild.id)
    elif not lib.stringTyping.isInt(guildStr):
        await message.reply(":x: Please provide a guild ID, 'here' or 'this' as your first argument.")
        return
    else:
        guildID = int(guildStr)
        if not botState.guildsDB.idExists(guildID):
            await message.reply(mention_author=False, content=f"Unrecognised guild ID: {guildID}")
            return
        callingBBGuild = botState.guildsDB.getGuild(guildID)
    if callingBBGuild.bountiesDisabled:
        await message.reply(":x: Bounties are disabled in " \
                            + "that guild" if callingBBGuild.dcGuild is None else callingBBGuild.dcGuild.name \
                            + "!")
        return

    allDivs = False
    if divStr == "all":
        allDivs = True
    elif lib.stringTyping.isInt(divStr):
        useTL = True
        tl = int(divStr)
        if tl < cfg.minTechLevel or tl > cfg.maxTechLevel:
            await message.reply(f":x: Tech level must be between {cfg.minTechLevel} and {cfg.maxTechLevel}")
            return
    else:
        useTL = False
        if divStr not in cfg.bountyDivisionNames:
            await message.reply(f":x: Unknown division name. Must be one of: {', '.join(cfg.bountyDivisionNames)}")
            return

    if allDivs:
        activityEmbed = lib.discordUtil.makeEmbed("Current Max Bounties", desc=message.guild.name,
                        col=discord.Colour.random(), thumb=message.guild.icon_url_as(size=64))
        for div in callingBBGuild.bountiesDB.divisions.values():
            activityEmbed.add_field(name=nameForDivision(div),
                                    value=str(div.maxBounties()))
        await message.author.send(embed=activityEmbed)
    else:
        if useTL:
            div = callingBBGuild.bountiesDB.divisionForLevel(tl)
        else:
            div = callingBBGuild.bountiesDB.divisionForName(divStr)
        await message.author.send(str(div.maxBounties()))

botCommands.register("current-max-bounties", dev_cmd_current_max_bounties, 3, allowDM=False,
                        helpSection="bounties", useDoc=True)


async def dev_cmd_xp_for_level(message : discord.Message, args : str, isDM : bool):
    """Print the amount of bounty hunter xp required to reach a given level.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing a level.
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if args == "":
        await message.reply(":x: Please give a level!")
        return

    elif not lib.stringTyping.isInt(args):
        await message.reply(":x: That's not a number!")
        return

    tl = int(args)

    if tl < cfg.minTechLevel or tl > cfg.maxTechLevel:
        await message.reply(f":x: Level must be between {cfg.minTechLevel} and {cfg.maxTechLevel}.")

    else:
        await message.reply(mention_author=False, content=f"💎 **{gameMaths.bountyHuntingXPForLevel(tl)}" \
                                    + f"** bounty hunter xp is required to reach level {args}.")

botCommands.register("xp-for-level", dev_cmd_xp_for_level, 3, forceKeepArgsCasing=True, allowDM=True, helpSection="bounties",
                        signatureStr="**xp-for-level** *[level]*",
                        shortHelp="Get the amount of xp required to reach a given bounty hunter level.")


async def dev_cmd_force_expire_bounty(message : discord.Message, args : str, isDM : bool):
    """Force the named bounty to expire immediately.

    :param discord.Message message: the discord message calling the command
    :param str args: a criminal alias
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if not args:
        await message.channel.send(":x: Not enough arguments! Please give the criminal name.")
        return

    callingBBGuild = botState.guildsDB.getGuild(message.guild.id)
    if callingBBGuild.bountiesDisabled:
        await message.channel.send(":x: This server has bounties disabled!")
        return

    # look up the criminal object
    criminalName = args.title()

    # report unrecognised criminal names
    if not callingBBGuild.bountiesDB.bountyNameExists(criminalName, noEscapedCrim=False):
        errmsg = ":x: That pilot is not currently wanted!"

        if lib.stringTyping.isMention(criminalName):
            errmsg += "\n:warning: **Don't tag users**, use their name and ID number like so: `" \
                        + callingBBGuild.commandPrefix + "expire-bounty Trimatix#2244`"

        await message.channel.send(errmsg)
        return

    try:
        bountyObj: bounty.Bounty = callingBBGuild.bountiesDB.getBounty(criminalName)
    except KeyError:
        bountyObj = callingBBGuild.bountiesDB.getEscapedBounty(criminalName)
    if datetime.utcfromtimestamp(bountyObj.endTime) < datetime.utcnow():
        await message.reply("This bounty is already expired, removing erroneous listing.")
        await bountyObj.expire(dbReload=True)
    else:
        await bountyObj.expire()
        await message.reply("✅ Bounty expired successfully")

botCommands.register("expire-bounty", dev_cmd_force_expire_bounty, 3, forceKeepArgsCasing=True, allowDM=False,
                        helpSection="bounties", signatureStr="**expire-bounty <criminal name>**",
                        shortHelp="Force the immediate expiry of a bounty")


async def dev_cmd_force_escape_bounty(message : discord.Message, args : str, isDM : bool):
    """Force the named bounty to escape immediately.

    :param discord.Message message: the discord message calling the command
    :param str args: a criminal alias
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if not args:
        await message.channel.send(":x: Not enough arguments! Please give the criminal name.")
        return

    callingBBGuild = botState.guildsDB.getGuild(message.guild.id)
    if callingBBGuild.bountiesDisabled:
        await message.channel.send(":x: This server has bounties disabled!")
        return

    # look up the criminal object
    criminalName = args.title()

    # report unrecognised criminal names
    if not callingBBGuild.bountiesDB.bountyNameExists(criminalName, noEscapedCrim=True):
        errmsg = ":x: That pilot is not currently wanted!"

        if lib.stringTyping.isMention(criminalName):
            errmsg += "\n:warning: **Don't tag users**, use their name and ID number like so: `" \
                        + callingBBGuild.commandPrefix + "escape-bounty Trimatix#2244`"

        await message.channel.send(errmsg)
        return

    tasks = lib.discordUtil.BasicScheduler()

    bountyObj: bounty.Bounty = callingBBGuild.bountiesDB.getBounty(criminalName)
    if bountyObj.isEscaped():
        await message.reply(":x: This bounty is already escaped")
        bountyObj.escape(dbReload=True)
        if bountyObj.division.bountyBoardChannel is not None:
            tasks.add(callingBBGuild.updateBountyBoardChannel(bountyObj, bountyComplete=True))
            tasks.add(bountyObj.division.bountyBoardChannel.updateEscapedBountiesMessage())
            await tasks.wait()
            tasks.logExceptions(logCategory="escapedBounties", className="dev_bounties",
                                funcName="dev_cmd_force_escape_bounty")
    else:
        bountyObj.escape()
        if bountyObj.division.bountyBoardChannel is not None:
            tasks.add(callingBBGuild.updateBountyBoardChannel(bountyObj, bountyComplete=True))
            tasks.add(bountyObj.division.bountyBoardChannel.updateEscapedBountiesMessage())
            await tasks.wait()
            tasks.logExceptions(logCategory="escapedBounties", className="dev_bounties",
                                funcName="dev_cmd_force_escape_bounty")
        await message.reply("✅ Bounty escaped successfully")

botCommands.register("escape-bounty", dev_cmd_force_escape_bounty, 3, forceKeepArgsCasing=True, allowDM=False,
                        helpSection="bounties", signatureStr="**escape-bounty <criminal name>**",
                        shortHelp="Force a bounty to escape immediately")


async def dev_cmd_force_respawn_bounty(message : discord.Message, args : str, isDM : bool):
    """Force the named bounty to respawn immediately.

    :param discord.Message message: the discord message calling the command
    :param str args: a criminal alias
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if not args:
        await message.channel.send(":x: Not enough arguments! Please give the criminal name.")
        return

    callingBBGuild: basedGuild.BasedGuild = botState.guildsDB.getGuild(message.guild.id)
    if callingBBGuild.bountiesDisabled:
        await message.channel.send(":x: This server has bounties disabled!")
        return

    # look up the criminal object
    criminalName = args.title()

    # report unrecognised criminal names
    if not callingBBGuild.bountiesDB.bountyNameExists(criminalName, noEscapedCrim=False):
        errmsg = ":x: That pilot is not currently wanted!"

        if lib.stringTyping.isMention(criminalName):
            errmsg += "\n:warning: **Don't tag users**, use their name and ID number like so: `" \
                        + callingBBGuild.commandPrefix + "respawn-bounty Trimatix#2244`"

        await message.channel.send(errmsg)
        return

    try:
        bountyObj: bounty.Bounty = callingBBGuild.bountiesDB.getEscapedBounty(criminalName)
    except KeyError:
        await message.reply(":x: The bounty is not currently escaped.")
        return

    if not bountyObj.isEscaped():
        await message.reply("🥴 This bounty is marked as escaped, but recorded in the active bounties db. attempting force...")
        botState.logger.log("dev_bounties", "dev_cmd_force_respawn_bounty",
                            f"bounty {bountyObj.criminal.name} isEscaped but recorded in db as active",
                            eventType="BTY_STATE_CONFLICT")
        await bountyObj.forceRespawn()
    else:
        await bountyObj.forceRespawn()
        await message.reply("✅ Bounty respawned successfully")

botCommands.register("respawn-bounty", dev_cmd_force_respawn_bounty, 3, forceKeepArgsCasing=True, allowDM=False,
                        helpSection="bounties", signatureStr="**respawn-bounty <criminal name>**",
                        shortHelp="Force an escaped bounty to respawn immediately")


async def dev_cmd_restart_new_bounty_task(message : discord.Message, args : str, isDM : bool):
    """developer command that restarts a 'new bounties' timedtask, or all of them for a server if specified

    :param discord.Message message: the discord message calling the command
    :param str args: "all" or a single tech level/division name
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if not args:
        await message.reply(":x: Please specify a division (name, tl or all)")
        return

    allDivs = False
    if args == "all":
        allDivs = True
    elif lib.stringTyping.isInt(args):
        useTL = True
        tl = int(args)
        if tl < cfg.minTechLevel or tl > cfg.maxTechLevel:
            await message.reply(f":x: Tech level must be between {cfg.minTechLevel} and {cfg.maxTechLevel}")
            return
    else:
        useTL = False
        if args not in cfg.bountyDivisionNames:
            await message.reply(f":x: Unknown division name. Must be one of: {', '.join(cfg.bountyDivisionNames)}")
            return

    callingBBGuild: basedGuild.BasedGuild = botState.guildsDB.getGuild(message.guild.id)

    if allDivs:
        for div in callingBBGuild.bountiesDB.divisions.values():
            if div.newBountyTT is not None:
                div.stopBountySpawner()
            if not div.isFull() or not div.hasMinTLBounty():
                div.tryStartBountySpawner()
    else:
        if useTL:
            div = callingBBGuild.bountiesDB.divisionForLevel(tl)
        else:
            div = callingBBGuild.bountiesDB.divisionForName(args)
        if div.newBountyTT is not None:
            div.stopBountySpawner()
        if not div.isFull() or not div.hasMinTLBounty():
            div.tryStartBountySpawner()
    await message.author.send(f"> {message.jump_url}\n✅ Done!")

botCommands.register("restart-bounty-task", dev_cmd_restart_new_bounty_task, 3, allowDM=False,
                        helpSection="bounties", useDoc=True)


async def dev_cmd_user_can_divup_or_prestige(message : discord.Message, args : str, isDM : bool):
    """Decide whether a user can div-up/prestige

    :param discord.Message message: the discord message calling the command
    :param str args: a user ID
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if not args:
        await message.reply(":x: Not enough arguments! Please give the user ID.")
        return

    if not lib.stringTyping.isInt(args):
        await message.reply(":x: That's not a user ID.")
        return

    userID = int(args)

    if not botState.usersDB.idExists(userID):
        await message.reply(":x: Unknown user ID.")
        return

    u = botState.usersDB.getUser(userID)
    await message.reply(f"{u.canDivUp()} ({u.bountyHuntingXpSurplus}xp surplus)")

botCommands.register("can-div-up", dev_cmd_user_can_divup_or_prestige, 3, aliases=["can-prestige"], allowDM=False,
                        helpSection="bounties", signatureStr="**can-div-up <user id>**",
                        shortHelp="Decide whether a user can div-up/prestige")


async def dev_cmd_set_user_divup_surplus(message : discord.Message, args : str, isDM : bool):
    """Enable a user's ability to div-up or prestige by setting their xp surplus

    :param discord.Message message: the discord message calling the command
    :param str args: a user id followed by an amount of xp
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    argsSplit = args.split(" ")
    if len(argsSplit)< 2:
        await message.reply(":x: Not enough arguments! Please give the user ID and xp surplus.")
        return

    if not lib.stringTyping.isInt(argsSplit[0]):
        await message.reply(":x: That's not a user ID.")
        return
    if not lib.stringTyping.isInt(argsSplit[1]):
        await message.reply(":x: That's not an integer amount of xp.")
        return

    userID = int(args[0])

    if not botState.usersDB.idExists(userID):
        await message.reply(":x: Unknown user ID.")
        return

    newSurplus = int(args[1])
    u = botState.usersDB.getUser(userID)
    canDivup = u.canDivUp()

    u.bountyHuntingXpSurplus = newSurplus
    if newSurplus == -1:
        await message.reply("✅ set successfully!" + "User can no longer div-up" if canDivup else "No change.")
    else:
        await message.reply("✅ set successfully!" + "User can now div-up" if not canDivup else "User was already able to div-up.")

botCommands.register("set-xp-surplus", dev_cmd_set_user_divup_surplus, 3, allowDM=False,
                        helpSection="bounties", signatureStr="**set-xp-surplus <user id> <xp surplus>**",
                        shortHelp="Set the amount of xp a user will be awarded AFTER using div-up.\n" \
                                + "Set to at least 0 to enable div-up. Set to -1 to disable div-up.\n" \
                                + "Also enables prestiging, but no xp is awarded after.")


async def dev_cmd_disable_user_can_divup_or_prestige(message : discord.Message, args : str, isDM : bool):
    """Disable a user's ability to div-up/prestige

    :param discord.Message message: the discord message calling the command
    :param str args: a user ID
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if not args:
        await message.reply(":x: Not enough arguments! Please give the user ID.")
        return

    if not lib.stringTyping.isInt(args):
        await message.reply(":x: That's not a user ID.")
        return

    userID = int(args)

    if not botState.usersDB.idExists(userID):
        await message.reply(":x: Unknown user ID.")
        return

    u = botState.usersDB.getUser(userID)
    canDivup = u.canDivUp()
    u.bountyHuntingXpSurplus = -1
    
    await message.reply("✅ set successfully!" + "User can no longer div-up" if canDivup else "No change.")

botCommands.register("disable-div-up", dev_cmd_disable_user_can_divup_or_prestige, 3, aliases=["disable-prestige"],
                        allowDM=False, helpSection="bounties", signatureStr="**can-div-up <user id>**",
                        shortHelp="Remove a user's ability div-up/prestige.")
