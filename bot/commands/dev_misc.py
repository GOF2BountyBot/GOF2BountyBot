import asyncio
from logging import exception
from typing import Dict, Type, cast
import discord
import traceback
from datetime import datetime

from bot.gameObjects.bounties.bountyBoards import bountyBoardChannel

from . import commandsDB as botCommands
from .. import botState, lib
from ..users.basedUser import BasedUser
from ..users import basedGuild
from ..gameObjects.items.tools import crateTool
from datetime import timedelta
from ..reactionMenus import giveawayMenu
from ..cfg import bbData, cfg, versionInfo
from ..reactionMenus import reactionMenu
from ..scheduling import timedTask
from ..databases import bountyDB, bountyDivision

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


async def dev_cmd_restart_task_checker(message : discord.Message, args : str, isDM : bool):
    """developer command that restarts the global timedtask scheduler

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    botState.taskScheduler.stopTaskChecking()
    botState.taskScheduler.startTaskChecking()
    await message.author.send(f"> {message.jump_url}\n✅ Done!")

botCommands.register("restart-task-scheduler", dev_cmd_restart_task_checker, 3, allowDM=True, useDoc=True)


def describeTT(tt: timedTask.TimedTask, issueTime: bool = True, expiryFunc: bool = True, nextExpiry: bool = True, expiryDelta: bool = True, autoReschedule: bool = True, sep="\n") -> str:
    if tt is None:
        return "null TT"

    ttStrParts = []
    if issueTime:
        ttStrParts.append(f"Issue time: {'null' if tt.issueTime is None else tt.issueTime.strftime('%m/%d/%Y, %H:%M:%S')}")
    if nextExpiry:
        ttStrParts.append(f"Next expiry: {'null' if tt.expiryTime is None else tt.expiryTime.strftime('%m/%d/%Y, %H:%M:%S')}")
    if expiryDelta:
        ttStrParts.append(f"Expiry delta: {'null' if tt.expiryDelta is None else lib.timeUtil.td_format_noYM(tt.expiryDelta)}")
    if autoReschedule:
        ttStrParts.append(f"Auto-reschedule: {tt.autoReschedule}")
    if expiryFunc:
        ttStrParts.append(f"Function: {'None' if tt.expiryFunction is None else str(tt.expiryFunction)}")
        ttStrParts.append(f"Args: {'None' if tt.expiryFunctionArgs is None else 'Not None'}")

    return(sep.join(ttStrParts))


async def dev_cmd_bot_status(message : discord.Message, args : str, isDM : bool):
    """developer command sending a DM containing various info about the bot's current status

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    embed = discord.Embed(title="Bot Status", colour=discord.Colour.random())

    newestBASED = await versionInfo.getNewestTagOnRemote(botState.httpClient, versionInfo.BASED_API_URL)
    nextUpdate = versionInfo.nextUpdateCheck().strftime("%m/%d/%Y, %H:%M:%S") if cfg.BASED_checkForUpdates else "disabled"

    embed.add_field(name="Client",
                    value=f"{botState.client.user} ({botState.client.user.id})")

    embed.add_field(name="Shutdown Mode",
                    value=f"{botState.shutdown}")

    embed.add_field(name="HttpClient",
                    value=f"State: {'Closed' if botState.httpClient.closed else 'Open'}\n" \
                        + f"Cookies: {len(botState.httpClient.cookie_jar)}")

    embed.add_field(name="GitHub",
                    value=f"Repo: {botState.githubRepo.url}")

    embed.add_field(name="Shop Refresh TT",
                    value=describeTT(botState.shopRefreshTT))

    if botState.taskScheduler is None:
        schedulerStr = "null"
    else:
        if len(botState.taskScheduler.tasksHeap) == 0:
            nextTaskStr = "No tasks"
        else:
            nextTask = botState.taskScheduler.tasksHeap[0]
            nextTaskStr = "- " + describeTT(nextTask, sep="\n- ")

        asyncIOLoopStr = f"{'running' if botState.taskScheduler.loop.is_running() else 'not running'}/" \
                        + ('closed' if botState.taskScheduler.loop.is_closed() else 'not closed')

        if botState.taskScheduler.sleepTask is None:
            sleepTaskStr = "None"
        else:
            if botState.taskScheduler.sleepTask.done() or botState.taskScheduler.sleepTask.cancelled():
                if e := botState.taskScheduler.sleepTask.exception():
                    exceptionStr = str(e)
                else:
                    exceptionStr = "None"

                resultStr = "None" if botState.taskScheduler.sleepTask.result is None else "Not None"
            else:
                exceptionStr = "Still executing"
                returnStr = "Still executing"

            sleepTaskStr = f"{'done' if botState.taskScheduler.sleepTask.done() else 'not done'}/" \
                        + f"{'cancelled' if botState.taskScheduler.sleepTask.cancelled() else 'cancelled'}\n" \
                        + f"Exception: {exceptionStr}\nResult: {returnStr}"

        schedulerStr = f"Active: {botState.taskScheduler.active}\n" \
                    + f"Asyncio Loop: {asyncIOLoopStr}\n" \
                    + f"Tasks: {len(botState.taskScheduler.tasksHeap)}\n" \
                    + f"Next task: {nextTaskStr}\n" \
                    + f"Sleep task: {sleepTaskStr}"

    embed.add_field(name="Task Scheduler",
                    value=schedulerStr, inline=False)

    embed.add_field(name="BASED",
                    value=f"Current: {versionInfo.BASED_VERSION}\n Newest: {newestBASED}\n Next check: {nextUpdate}\n- " \
                        + describeTT(botState.updatesCheckTT, sep="\n- "))

    embed.add_field(name="Commands",
                    value=f"Modules: {', '.join(cfg.includedCommandModules)}\n" \
                        + f"Total commands: {sum(len(i) for i in botCommands.commands)}\n"
                            + "\n".join(f"- {level}: {len(commands)}" for level, commands in enumerate(botCommands.commands)),
                    inline=False)

    menuTypeCounts: Dict[Type[reactionMenu.ReactionMenu], int] = {}
    for menu in botState.reactionMenusDB.values():
        menuTypeCounts[type(menu)] = menuTypeCounts.get(type(menuTypeCounts), 0) + 1

    embed.add_field(name="Reaction Menus",
                    value=f"{len(botState.reactionMenusDB)} Menus\n" \
                        + "\n".join(f"- {menuType.__name__}: {numMenus}" for menuType, numMenus in menuTypeCounts.items()))
    embed.add_field(name="Users",
                    value=f"Guilds: {len(botState.guildsDB.guilds)} registered/{len(botState.client.guilds)} total\n" \
                        + f"Users: {len(botState.usersDB.users)} Users/0 Depracated Users *(UNIMPLEMENTED)*")

    embed.add_field(name="Logger",
                    value=f"Unsaved logs:\n" \
                        + "\n".join(f"{c}: {len(l.values())}" for c, l in botState.logger.logs.items() if l))

    embed.add_field(name="DB Save TT",
                    value=describeTT(botState.dbSaveTT))

    embed.add_field(name="Temps Delay TT",
                    value=describeTT(botState.temperatureDecayTT))

    embed.add_field(name="New Bounty Fixed Delta Changed",
                    value=botState.newBountyFixedDeltaChanged)

    embed.add_field(name="Current Renders",
                    value=", ".join(botState.currentRenders) if botState.currentRenders else 'Empty')

    embed.add_field(name="System UTC Offset",
                    value=lib.timeUtil.td_format_noYM(botState.utcOffset) if botState.utcOffset else 'No offset')
                
    embed.add_field(name="$premium Cooldown End",
                    value='Null TT' if botState.premiumCooldownEnd is None else \
                            botState.premiumCooldownEnd.strftime("%m/%d/%Y, %H:%M:%S"))

    await message.author.send(embed=embed)

botCommands.register("bot-status", dev_cmd_bot_status, 3, forceKeepArgsCasing=True, allowDM=True, useDoc=True)


async def dev_cmd_item_status(message : discord.Message, args : str, isDM : bool):
    """developer command sending a DM containing info about the loaded game objects

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    embed = discord.Embed(title="Bot Status", colour=discord.Colour.random())

    embed.add_field(name="Built-in GameObjects",
                    value=lib.stringTyping.matchIndentation([
                        ("`Ships", f" | {len(bbData.builtInShipData)} data/{len(bbData.shipKeysByTL)} sorted/{sum(len(i) for i in bbData.shipKeysByTL)} sorted (total)`"),
                        ("`Modules", f" | {len(bbData.builtInModuleData)} data/{len(bbData.builtInModuleObjs)} objs/{len(bbData.moduleObjsByTL)} sorted/{sum(len(i) for i in bbData.moduleObjsByTL)} sorted (total)`"),
                        ("`Weapons", f" | {len(bbData.builtInWeaponData)} data/{len(bbData.builtInWeaponObjs)} objs/{len(bbData.weaponObjsByTL)} sorted/{sum(len(i) for i in bbData.weaponObjsByTL)} sorted (total)`"),
                        ("`Upgrades", f" | {len(bbData.builtInUpgradeData)} data/{len(bbData.builtInUpgradeObjs)} objs/{len(bbData.shipUpgradeToolsByUpgrade)} tools`"),
                        ("`Criminals", f" | {len(bbData.builtInCriminalData)} data/{len(bbData.builtInCriminalObjs)} objs`"),
                        ("`Systems", f" | {len(bbData.builtInSystemData)} data/{len(bbData.builtInSystemObjs)} objs`"),
                        ("`Turrets", f" | {len(bbData.builtInTurretData)} data/{len(bbData.builtInTurretObjs)} objs/{len(bbData.turretObjsByTL)} sorted/{sum(len(i) for i in bbData.turretObjsByTL)} sorted (total)`"),
                        ("`Commodities", f" | {len(bbData.builtInCommodityData)} data/{len(bbData.builtInCommodityObjs)} objs`"),
                        ("`Tools", f" | {len(bbData.builtInToolData)} data/{len(bbData.builtInToolObjs)} objs`"),
                        ("`Secondaries", f" | {len(bbData.builtInSecondariesData)} data/{len(bbData.builtInSecondaryObjs)} objs`"),
                        ("`ShipSkins", f" | {len(bbData.builtInShipSkinsData)} data/{len(bbData.builtInShipSkins)} objs/{len(bbData.shipSkinToolsBySkin)} tools`"),
                        ("`Medals", f" | {len(bbData.medalsData)} data/{len(bbData.medalObjs)} objs`"),
                        ("`Crates", f" | {len(bbData.builtInCrateObjs)} types/{', '.join(f'{t}: {len(v)}' for t, v in bbData.builtInCrateObjs.items())}`")
                    ]))
    
    await message.author.send(embed=embed)

botCommands.register("item-status", dev_cmd_item_status, 3, forceKeepArgsCasing=True, allowDM=True, useDoc=True)


async def dev_cmd_guild_status(message : discord.Message, args : str, isDM : bool):
    """developer command sending a DM containing info about the specified guild

    :param discord.Message message: the discord message calling the command
    :param str args: nothing, or a guild id
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if args:
        if isDM:
            await message.author.send("Give an id, or call from a guild")
            return
        if not lib.stringTyping.isInt(args):
            await message.author.send("Invalid id")
            return
        guildId = int(args)
    else:
        guildId = message.guild.id
    
    if botState.client.get_guild(guildId) is None:
        await message.author.send("I am not a member of the guild")

    if not botState.guildsDB.idExists(guildId):
        await message.author.send("Guild not registered in the database")
        return

    bGuild: basedGuild.BasedGuild = botState.guildsDB.getGuild(guildId)

    embed = discord.Embed(title="Guild Status", colour=discord.Colour.random())
    
    embed.add_field(name=str(guildId), value=f"{bGuild.dcGuild.name}")

    embed.add_field(name="Channels",
                    value=(f"announceChannel: {bGuild.announceChannel.mention} ({bGuild.announceChannel.id})\n" if bGuild.announceChannel is not None else f"announceChannel: None\n") \
                    + (f"playChannel: {bGuild.playChannel.mention} ({bGuild.playChannel.id})\n" if bGuild.playChannel is not None else f"playChannel: None\n") \
                    + (f"rendersChannel: {bGuild.rendersChannel.mention} ({bGuild.rendersChannel.id})" if bGuild.rendersChannel is not None else f"rendersChannel: None\n"))

    if bGuild.shopsDisabled:
        shopsStr = "Disabled"
    else:
        shopsStr = "\n".join(f"{divName}: Level {shop.currentTechLevel}" \
                            + f"\n- Ships: {shop.shipsStock.totalItems}\n-  > " \
                                + ", ".join(s.item.name for s in shop.shipsStock.items.values()) \
                            + f"\n- Weapons: {shop.weaponsStock.totalItems}\n-  > " \
                                + ", ".join(str(s.count) + "x " + s.item.name for s in shop.weaponsStock.items.values() if shop.weaponsStock.totalItems) \
                            + f"\n- Modules: {shop.modulesStock.totalItems}\n-  > " \
                                + ", ".join(str(s.count) + "x " + s.item.name for s in shop.modulesStock.items.values() if shop.modulesStock.totalItems) \
                            + f"\n- Turrets: {shop.turretsStock.totalItems}\n-  > " \
                                + ", ".join(str(s.count) + "x " + s.item.name for s in shop.turretsStock.items.values() if shop.turretsStock.totalItems) \
                            + f"\n- Tools: {shop.toolsStock.totalItems}\n-  > " \
                                + ", ".join(str(s.count) + "x " + s.item.name for s in shop.toolsStock.items.values() if shop.toolsStock.totalItems)
                            for divName, shop in bGuild.divisionShops.items())

    embed.add_field(name="Shops", value=shopsStr, inline=False)

    if bGuild.bountiesDisabled:
        bountiesStr = "Disabled"
    else:
        bountiesStr = "\n".join(f"{bountyDB.nameForDivision(div)}: " \
                            + str(sum(len(i) for i in div.bounties.values()) \
                                + sum(len(i) for i in div.escapedBounties.values())) \
                                + " Bounties" \
                            + f"\n- Active: {sum(len(i) for i in div.bounties.values())}\n-  > " \
                                + ", ".join(", ".join(d.criminal.name for d in s.values()) for s in div.bounties.values() if any(s.values())) \
                            + f"\n- Escaped: {sum(len(i) for i in div.escapedBounties.values())}\n-  > " \
                                + ", ".join(", ".join(d.criminal.name for d in s.values()) for s in div.escapedBounties.values() if any(s.values())) \
                            for div in bGuild.bountiesDB.divisions.values())

    embed.add_field(name="Bounties", value=bountiesStr, inline=False)
    
    if bGuild.alertRoles:
        alertRolesStr = "\n".join(f"{name}: <@&{roleId}> ({roleId})" if roleId != -1 else f"{name}: None" \
                                    for name, roleId in bGuild.alertRoles.items())
    else:
        alertRolesStr = "None"

    embed.add_field(name="Alert Roles",
                    value=alertRolesStr)

    if bGuild.bountiesDisabled:
        bountyBoardChannelsStr = "Bounties disabled"
    else:
        if not bGuild.hasBountyBoardChannels:
            bountyBoardChannelsStr = "BBCs disabled"
        else:
            bountyBoardChannelsStr = ""

    if any(div.bountyBoardChannel for div in bGuild.bountiesDB.divisions.values()):
        bountyBoardChannelsStr += "\n- " \
            + "\n- ".join(f"{bountyDB.nameForDivision(div)}: {div.bountyBoardChannel.channel.mention} ({div.bountyBoardChannel.channel.id})"
                        + (("\n-  > " + "\n-  > ".join(f"[{c.name}]({m.jump_url})" for c, m in div.bountyBoardChannel.bountyMessages.items())) \
                            if div.bountyBoardChannel.bountyMessages else "") \
                        for div in bGuild.bountiesDB.divisions.values() if div.bountyBoardChannel)
    
    embed.add_field(name="BountyBoardChannels", value=bountyBoardChannelsStr)

    embed.add_field(name="Role Menus", value=str(bGuild.ownedRoleMenus))

    if bGuild.bountiesDisabled:
        bountyAlertRolesStr = "Bounties disabled"
    else:
        if not bGuild.hasBountyAlertRoles:
            bountyAlertRolesStr = "BBCs disabled"
        else:
            bountyAlertRolesStr = ""

    if any(div.alertRoleID != -1 for div in bGuild.bountiesDB.divisions.values()):
        bountyAlertRolesStr += "\n" \
            + "\n".join(f"{bountyDB.nameForDivision(div)}: <@&{div.alertRoleID}> ({div.alertRoleID})" if div.alertRoleID != -1 else \
                f"{bountyDB.nameForDivision(div)}: None" for div in bGuild.bountiesDB.divisions.values())
    
    embed.add_field(name="Bounty Alert Roles", value=bountyAlertRolesStr)
    
    await message.author.send(embed=embed)

botCommands.register("guild-status", dev_cmd_guild_status, 3, signatureStr="**guild-status** *[id]*",
                    forceKeepArgsCasing=True, allowDM=True, useDoc=True)


async def dev_cmd_user_status(message : discord.Message, args : str, isDM : bool):
    """developer command sending a DM containing info about the specified user

    :param discord.Message message: the discord message calling the command
    :param str args: nothing or a user id
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if args:
        if isDM:
            await message.author.send("Give an id, nothing for yourself")
            return
        if not lib.stringTyping.isInt(args):
            await message.author.send("Invalid id")
            return
        userId = int(args)
    else:
        userId = message.user.id
    
    if botState.client.get_user(userId) is None:
        await message.author.send("I don't share any servers with that user")

    if not botState.usersDB.idExists(userId):
        await message.author.send("user not registered in the database")
        return

    buser: BasedUser = botState.usersDB.getUser(userId)

    embed = discord.Embed(title="User Status", colour=discord.Colour.random())

    id
    credits
    lifetimeBountyCreditsWon
    bountyCooldownEnd
    systemsChecked
    bountyWins
    activeShip
    inactiveShips
    inactiveModules
    inactiveWeapons
    inactiveTurrets
    inactiveTools
    duelRequests
    duelWins
    duelLosses
    duelCreditsWins
    duelCreditsLosses
    userAlerts
    homeGuildID
    guildTransferCooldownEnd
    kaamo
    loma
    prestiges
    ownedMenus
    medals
    classicModeEnabled
        async def transferGuild(self, newGuild : Guild):
    
    
    await message.author.send(embed=embed)

botCommands.register("item-status", dev_cmd_item_status, 3, forceKeepArgsCasing=True, allowDM=True, useDoc=True)
