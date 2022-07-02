import asyncio
from logging import exception
from typing import Dict, Optional, Type, cast
import discord
import traceback
from datetime import datetime
import json
import random

from . import commandsDB as botCommands
from .. import botState, lib
from ..lib import BASED_version
from ..logging import LogCategory
from ..users.basedUser import BasedUser
from ..users import basedGuild
from ..gameObjects.items.tools import crateTool
from ..gameObjects.bounties import bounty
from datetime import timedelta
from ..reactionMenus import giveawayMenu
from ..cfg import bbData, cfg
from ..reactionMenus import reactionMenu
from ..scheduling import timedTask
from ..databases import bountyDB, bountyDivision
from ..gameObjects.items import shipItem
from ..gameObjects.bounties import solarSystem

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
    botState.client.shutDownState = botState.ShutDownState.shutdown
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


async def dev_cmd_broadcast(message: discord.Message, args: str, isDM: bool):
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
            for guild in botState.client.guildsDB.guilds.values():
                if guild.hasAnnounceChannel():
                    await guild.getAnnounceChannel().send(sendArgs)
        else:
            for guild in botState.client.guildsDB.guilds.values():
                if guild.hasPlayChannel():
                    await guild.getPlayChannel().send(sendArgs)

botCommands.register("broadcast", dev_cmd_broadcast, 3, forceKeepArgsCasing=True, allowDM=True, useDoc=True)


async def dev_cmd_reset_has_poll(message: discord.Message, args: str, isDM: bool):
    """developer command resetting the poll ownership of the calling user, or the specified user if one is given.

    :param discord.Message message: the discord message calling the command
    :param str args: string, can be empty or contain a user mention
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    try:
        # reset the calling user's cooldown if no user is specified
        if args == "":
            requestedBUser: BasedUser = botState.client.usersDB.getUser(message.author.id)
        # otherwise get the specified user's discord object and reset their poll ownership.
        # [!] no validation is done.
        else:
            requestedBUser: BasedUser = botState.client.usersDB.getUser(int(args.lstrip("<@!").rstrip(">")))
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
    botState.client.shutDownState = botState.ShutDownState.update
    await message.reply(mention_author=False, content="updating and restarting...")
    await botState.client.shutdown()

botCommands.register("bot-update", dev_cmd_bot_update, 3, allowDM=True, useDoc=True)


async def dev_cmd_setbalance(message: discord.Message, args: str, isDM: bool):
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
    if not botState.client.usersDB.idExists(requestedUser.id):
        requestedBBUser = botState.client.usersDB.addID(requestedUser.id)
    else:
        requestedBBUser = botState.client.usersDB.getUser(requestedUser.id)
    # update the balance
    requestedBBUser.credits = int(argsSplit[1])
    await message.reply(mention_author=False, content="Done!")

botCommands.register("setbalance", dev_cmd_setbalance, 3, allowDM=True, useDoc=True)


async def dev_cmd_start_stocking_giveaway(message: discord.Message, args: str, isDM: bool):
    """developer command starting a giveaway of the keith stocking crate for 48 hours
    :param discord.Message message: the discord message calling the command
    :param str args: ignore
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    giveawayMsg = await message.channel.send("‎")
    stocking = crateTool.CrateTool.deserialize({"type": "CrateTool", "crateType": "christmas", "typeNum": 2021, "builtIn": True})
    menu = giveawayMenu.GiveawayMenu(giveawayMsg, [stocking], activeTime=timedelta(days=3),
                                        titleTxt="Merry Christmas!", 
                                        desc="React below to receive your stocking!\nFind it in your `$hangar tool`, and open it with the new `$use` command.",
                                        col=discord.Colour.random())

    botState.client.reactionMenusDB[giveawayMsg.id] = menu
    await menu.updateMessage()

botCommands.register("start-stocking-giveaway", dev_cmd_start_stocking_giveaway, 3, useDoc=True)


async def dev_cmd_restart_task_checker(message: discord.Message, args: str, isDM: bool):
    """developer command that restarts the global timedtask scheduler

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    botState.client.taskScheduler.stopTaskChecking()
    botState.client.taskScheduler.startTaskChecking()
    await message.author.send(f"> {message.jump_url}\n✅ Done!")

botCommands.register("restart-task-scheduler", dev_cmd_restart_task_checker, 3, allowDM=True, useDoc=True)


def describeTT(tt: Optional[timedTask.TimedTask], issueTime: bool = True, expiryFunc: bool = True, nextExpiry: bool = True,
                expiryDelta: bool = True, autoReschedule: bool = True, scheduled: bool = True, sep="\n") -> str:
    if tt is None:
        return "null TT"

    ttStrParts = []
    if issueTime:
        ttStrParts.append(f"Issue time: {'null' if tt.issueTime is None else tt.issueTime.strftime('%d/%m/%Y, %H:%M:%S')}")
    if nextExpiry:
        ttStrParts.append(f"Next expiry: {'null' if tt.expiryTime is None else tt.expiryTime.strftime('%d/%m/%Y, %H:%M:%S')}")
    if expiryDelta:
        ttStrParts.append(f"Expiry delta: {'null' if tt.expiryDelta is None else lib.timeUtil.td_format_noYM(tt.expiryDelta)}")
    if autoReschedule:
        ttStrParts.append(f"Auto-reschedule: {tt.autoReschedule}")
    if expiryFunc:
        ttStrParts.append(f"Function: {'None' if tt.expiryFunction is None else str(tt.expiryFunction)}")
        ttStrParts.append(f"Args: {'None' if tt.expiryFunctionArgs is None else 'Not None'}")
    if scheduled:
        ttStrParts.append(f"Scheduled on taskScheduler: {tt in botState.client.taskScheduler.tasksHeap}")

    return(sep.join(ttStrParts))


async def dev_cmd_bot_status(message: discord.Message, args: str, isDM: bool):
    """developer command sending a DM containing various info about the bot's current status

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    embed = discord.Embed(title="Bot Status", colour=discord.Colour.random())

    newestBASED = await lib.github.getNewestTagOnRemote(botState.client.httpClient, BASED_version.BASED_API_URL)
    nextUpdate = BASED_version.nextUpdateCheck().strftime("%d/%m/%Y, %H:%M:%S") if cfg.BASED_checkForUpdates else "disabled"

    embed.add_field(name="Client",
                    value=f"{botState.client.user} ({botState.client.user.id})")

    embed.add_field(name="Shutdown Mode",
                    value=f"{botState.client.shutDownState}")

    embed.add_field(name="HttpClient",
                    value=f"State: {'Closed' if botState.client.httpClient.closed else 'Open'}\n" \
                        + f"Cookies: {len(botState.client.httpClient.cookie_jar)}")

    embed.add_field(name="GitHub",
                    value=f"Repo: {botState.client.githubRepo.url}")

    embed.add_field(name="Shop Refresh TT",
                    value=describeTT(botState.shopRefreshTT))

    if botState.client.taskScheduler is None:
        schedulerStr = "null"
    else:
        if len(botState.client.taskScheduler.tasksHeap) == 0:
            nextTaskStr = "No tasks"
        else:
            nextTask = botState.client.taskScheduler.tasksHeap[0]
            nextTaskStr = "- " + describeTT(nextTask, sep="\n- ")

        asyncIOLoopStr = f"{'running' if botState.client.taskScheduler.loop.is_running() else 'not running'}/" \
                        + ('closed' if botState.client.taskScheduler.loop.is_closed() else 'not closed')

        if botState.client.taskScheduler.sleepTask is None:
            sleepTaskStr = "None"
        else:
            if botState.client.taskScheduler.sleepTask.done() or botState.client.taskScheduler.sleepTask.cancelled():
                if e := botState.client.taskScheduler.sleepTask.exception():
                    exceptionStr = str(e)
                else:
                    exceptionStr = "None"

                resultStr = "None" if botState.client.taskScheduler.sleepTask.result is None else "Not None"
            else:
                exceptionStr = "Still executing"
                returnStr = "Still executing"

            sleepTaskStr = f"{'done' if botState.client.taskScheduler.sleepTask.done() else 'not done'}/" \
                        + f"{'cancelled' if botState.client.taskScheduler.sleepTask.cancelled() else 'not cancelled'}\n" \
                        + f"Exception: {exceptionStr}\nResult: {returnStr}"

        schedulerStr = f"Active: {botState.client.taskScheduler.active}\n" \
                    + f"Asyncio Loop: {asyncIOLoopStr}\n" \
                    + f"Tasks: {len(botState.client.taskScheduler.tasksHeap)}\n" \
                    + f"Next task: {nextTaskStr}\n" \
                    + f"Sleep task: {sleepTaskStr}"

    embed.add_field(name="Task Scheduler",
                    value=schedulerStr, inline=False)

    embed.add_field(name="BASED",
                    value=f"Current: {BASED_version.getBASEDVersion().BASED_version}\n Newest: {newestBASED}\n Next check: {nextUpdate}\n- " \
                        + describeTT(botState.updatesCheckTT, sep="\n- "))

    embed.add_field(name="Commands",
                    value=f"Modules: {', '.join(cfg.includedCommandModules)}\n" \
                        + f"Total commands: {sum(len(i) for i in botCommands.commands)}\n"
                            + "\n".join(f"- {level}: {len(commands)}" for level, commands in enumerate(botCommands.commands)),
                    inline=False)

    menuTypeCounts: Dict[Type[reactionMenu.ReactionMenu], int] = {}
    for menu in botState.client.reactionMenusDB.values():
        menuTypeCounts[type(menu)] = menuTypeCounts.get(type(menuTypeCounts), 0) + 1

    embed.add_field(name="Reaction Menus",
                    value=f"{len(botState.client.reactionMenusDB)} Menus\n" \
                        + "\n".join(f"- {menuType.__name__}: {numMenus}" for menuType, numMenus in menuTypeCounts.items()))
    embed.add_field(name="Users",
                    value=f"Guilds: {len(botState.client.guildsDB.guilds)} registered/{len(botState.client.guilds)} total\n" \
                        + f"Users: {len(botState.client.usersDB.users)} Users/0 Depracated Users *(UNIMPLEMENTED)*")

    embed.add_field(name="Logger",
                    value=f"Unsaved logs:\n" \
                        + "\n".join(f"{c}: {len(l.values())}" for c, l in botState.client.logger.logs.items() if l))

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
                            botState.premiumCooldownEnd.strftime("%d/%m/%Y, %H:%M:%S"))

    await message.author.send(embed=embed)

botCommands.register("bot-status", dev_cmd_bot_status, 3, allowDM=True, useDoc=True)


async def dev_cmd_item_status(message: discord.Message, args: str, isDM: bool):
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

botCommands.register("item-status", dev_cmd_item_status, 3, allowDM=True, useDoc=True)


async def dev_cmd_guild_status(message: discord.Message, args: str, isDM: bool):
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

    if not botState.client.guildsDB.idExists(guildId):
        await message.author.send("Guild not registered in the database")
        return

    bGuild: basedGuild.BasedGuild = botState.client.guildsDB.getGuild(guildId)

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
                                + " Bounties\n" \
                            + f"temperature: {div.temperature} ({'active' if div.isActive else 'not active'})\n"
                            + f"latest bounty: {'None' if div.latestBounty is None else div.latestBounty.criminal.name}\n"
                            + f"Active: {sum(len(i) for i in div.bounties.values())}\n-  > " \
                                + ", ".join(", ".join(d.criminal.name for d in s.values()) for s in div.bounties.values() if any(s.values())) \
                            + f"\nEscaped: {sum(len(i) for i in div.escapedBounties.values())}\n-  > " \
                                + ", ".join(", ".join(d.criminal.name for d in s.values()) for s in div.escapedBounties.values() if any(s.values())) \
                            for div in bGuild.bountiesDB.divisions.values())

    embed.add_field(name="Bounties", value=bountiesStr, inline=False)

    if bGuild.bountiesDisabled:
        newBountyTTsStr = "Disabled"
    else:
        newBountyTTsStr = "\n".join(f"{bountyDB.nameForDivision(div)}: \n- " \
                            + describeTT(div.newBountyTT, sep="\n- ") \
                            for div in bGuild.bountiesDB.divisions.values())

    embed.add_field(name="New Bounty TTs", value=newBountyTTsStr, inline=False)
    
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
            bountyAlertRolesStr = "Disabled"
        else:
            bountyAlertRolesStr = ""

    if any(div.alertRoleID != -1 for div in bGuild.bountiesDB.divisions.values()):
        bountyAlertRolesStr += "\n" \
            + "\n".join(f"{bountyDB.nameForDivision(div)}: <@&{div.alertRoleID}> ({div.alertRoleID})" if div.alertRoleID != -1 else \
                f"{bountyDB.nameForDivision(div)}: None" for div in bGuild.bountiesDB.divisions.values())
    
    embed.add_field(name="Bounty Alert Roles", value=bountyAlertRolesStr)
    
    await message.author.send(embed=embed)

botCommands.register("guild-status", dev_cmd_guild_status, 3, signatureStr="**guild-status** *[id]*",
                    allowDM=True, useDoc=True)


async def dev_cmd_user_status(message: discord.Message, args: str, isDM: bool):
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
        userId = message.author.id
    
    if not (dcUser := botState.client.get_user(userId)):
        await message.author.send("I don't share any servers with that user")

    if not botState.client.usersDB.idExists(userId):
        await message.author.send("user not registered in the database")
        return

    bUser: BasedUser = botState.client.usersDB.getUser(userId)

    embed = discord.Embed(title="User Status", colour=discord.Colour.random())

    embed.add_field(name=bUser.id, value=str(dcUser) if dcUser is not None else "Unknown")
    embed.add_field(name="Credits",
                    value=f"Current: {bUser.credits}\nlifetimeBountyCreditsWon: {bUser.lifetimeBountyCreditsWon}")
    embed.add_field(name="$check Cooldown", 
                    value=datetime.utcfromtimestamp(bUser.bountyCooldownEnd).strftime("%d/%m/%Y, %H:%M:%S"))
    
    embed.add_field(name="Systems Checked", value=str(bUser.systemsChecked))
    embed.add_field(name="Bounty Wins", value=str(bUser.bountyWins))

    shipStr = f"{bUser.activeShip.name}\nNickname: {bUser.activeShip.nickname if bUser.activeShip.hasNickname else ''}\n" \
            + f"Armour: {bUser.activeShip.armour}\n" \
            + f"Cargo: {bUser.activeShip.cargo}\n" \
            + f"Handling: {bUser.activeShip.handling}\n" \
            + f"Max secondaries: {bUser.activeShip.maxSecondaries}\n" \
            + f"Primaries: {len(bUser.activeShip.weapons)}/{bUser.activeShip.maxPrimaries}:\n" \
                + ((f"- " + ", ".join(i.name for i in bUser.activeShip.weapons) + "\n") if bUser.activeShip.weapons else '') \
            + f"Modules: {len(bUser.activeShip.modules)}/{bUser.activeShip.maxModules}:\n" \
                + ((f"- " + ", ".join(i.name for i in bUser.activeShip.modules) + "\n") if bUser.activeShip.modules else '') \
            + f"Turrets: {len(bUser.activeShip.turrets)}/{bUser.activeShip.maxTurrets}:\n" \
                + ((f"- " + ", ".join(i.name for i in bUser.activeShip.turrets) + "\n") if bUser.activeShip.turrets else '') \
            + f"Upgrades: " + ", ".join(i.name for i in bUser.activeShip.upgradesApplied) + "\n" \
            + f"Skin: " + (bUser.activeShip.skin.name if bUser.activeShip.skin is not None else 'None')

    embed.add_field(name="Active Ship", value=shipStr)
    
    embed.add_field(name="Ships", value=f"Total: {bUser.inactiveShips.totalItems}\n-  > " \
                + ", ".join(s.item.name for s in bUser.inactiveShips.items.values()))
    
    embed.add_field(name="Weapons", value=f"Total: {bUser.inactiveWeapons.totalItems}\n-  > " \
        + ", ".join(str(s.count) + "x " + s.item.name for s in bUser.inactiveWeapons.items.values() if bUser.inactiveWeapons.totalItems))
    embed.add_field(name="Modules", value=f"Total: {bUser.inactiveModules.totalItems}\n-  > " \
        + ", ".join(str(s.count) + "x " + s.item.name for s in bUser.inactiveModules.items.values() if bUser.inactiveModules.totalItems))
    embed.add_field(name="Turrets", value=f"Total: {bUser.inactiveTurrets.totalItems}\n-  > " \
        + ", ".join(str(s.count) + "x " + s.item.name for s in bUser.inactiveTurrets.items.values() if bUser.inactiveTurrets.totalItems))
    embed.add_field(name="Tools", value=f"Total: {bUser.inactiveTools.totalItems}\n-  > " \
        + ", ".join(str(s.count) + "x " + s.item.name for s in bUser.inactiveTools.items.values() if bUser.inactiveTools.totalItems))

    embed.add_field(name="Duel Requests", value="\n".join(f"{target.id}: {request.stakes}" for target, request in bUser.duelRequests.items()) if bUser.duelRequests else "None")
    embed.add_field(name="Duels", value=f"Wins: {bUser.duelWins}\nLosses: {bUser.duelLosses}\nCredits won: {bUser.duelCreditsWins}\nCredits lost: {bUser.duelCreditsLosses}")
    
    if bUser.hasHomeGuild() and (homeGuild := botState.client.guildsDB.getGuild(bUser.homeGuildID)):
        if dcUser is None:
            userAlertsStr = "States unknown, dcUser unavailable.\n" + ", ".join(t.__name__ for t in bUser.userAlerts)
        else:
            userAlertsStr = "\n".join(f"{t.__name__}: {a.getState(homeGuild.dcGuild, homeGuild, homeGuild.dcGuild.get_member(dcUser.id))}" for t, a in bUser.userAlerts.items())
    else:
        userAlertsStr = "States unknown, no homeguild.\n" + ", ".join(t.__name__ for t in bUser.userAlerts)


    embed.add_field(name="User Alerts", value=userAlertsStr)
    embed.add_field(name="Home Guild", value=f"{bUser.homeGuildID} - {botState.client.get_guild(bUser.homeGuildID)}")
    embed.add_field(name="$transfer Cooldown", 
                    value=bUser.guildTransferCooldownEnd.strftime("%d/%m/%Y, %H:%M:%S") if bUser.guildTransferCooldownEnd is not None else "None")

    if bUser.kaamo is None:
        kaamoStr = "None"
    else:
        kaamoStr = f"\n- Ships: {bUser.kaamo.shipsStock.totalItems}\n-  > " \
                        + ", ".join(s.item.name for s in bUser.kaamo.shipsStock.items.values()) \
                    + f"\n- Weapons: {bUser.kaamo.weaponsStock.totalItems}\n-  > " \
                        + ", ".join(str(s.count) + "x " + s.item.name for s in bUser.kaamo.weaponsStock.items.values() if bUser.kaamo.weaponsStock.totalItems) \
                    + f"\n- Modules: {bUser.kaamo.modulesStock.totalItems}\n-  > " \
                        + ", ".join(str(s.count) + "x " + s.item.name for s in bUser.kaamo.modulesStock.items.values() if bUser.kaamo.modulesStock.totalItems) \
                    + f"\n- Turrets: {bUser.kaamo.turretsStock.totalItems}\n-  > " \
                        + ", ".join(str(s.count) + "x " + s.item.name for s in bUser.kaamo.turretsStock.items.values() if bUser.kaamo.turretsStock.totalItems) \
                    + f"\n- Tools: {bUser.kaamo.toolsStock.totalItems}\n-  > " \
                        + ", ".join(str(s.count) + "x " + s.item.name for s in bUser.kaamo.toolsStock.items.values() if bUser.kaamo.toolsStock.totalItems)

    embed.add_field(name="Kaamo", value=kaamoStr, inline=False)


    if bUser.loma is None:
        lomaStr = "None"
    else:
        lomaStr = f"\n- Ships: {bUser.loma.shipsStock.totalItems}\n-  > " \
                        + ", ".join((s.item.name + (f"*{s.discounts[0].mult}" if s.discounts else "")) for s in bUser.loma.shipsStock.items.values()) \
                    + f"\n- Weapons: {bUser.loma.weaponsStock.totalItems}\n-  > " \
                        + ", ".join((str(s.count) + "x " + s.item.name + (f"*{s.discounts[0].mult}" if s.discounts else "")) for s in bUser.loma.weaponsStock.items.values() if bUser.loma.weaponsStock.totalItems) \
                    + f"\n- Modules: {bUser.loma.modulesStock.totalItems}\n-  > " \
                        + ", ".join((str(s.count) + "x " + s.item.name + (f"*{s.discounts[0].mult}" if s.discounts else "")) for s in bUser.loma.modulesStock.items.values() if bUser.loma.modulesStock.totalItems) \
                    + f"\n- Turrets: {bUser.loma.turretsStock.totalItems}\n-  > " \
                        + ", ".join((str(s.count) + "x " + s.item.name + (f"*{s.discounts[0].mult}" if s.discounts else "")) for s in bUser.loma.turretsStock.items.values() if bUser.loma.turretsStock.totalItems) \
                    + f"\n- Tools: {bUser.loma.toolsStock.totalItems}\n-  > " \
                        + ", ".join((str(s.count) + "x " + s.item.name + (f"*{s.discounts[0].mult}" if s.discounts else "")) for s in bUser.loma.toolsStock.items.values() if bUser.loma.toolsStock.totalItems)

    embed.add_field(name="Loma", value=lomaStr, inline=False)

    embed.add_field(name="Prestiges", value=str(bUser.prestiges))
    embed.add_field(name="Owned Menus", value="\n".join(f"{t}: {', '.join(str(i) for i in m)}" for t, m in bUser.ownedMenus.items()) if bUser.ownedMenus else "None")

    embed.add_field(name="Medals", value=", ".join(i.name for i in bUser.medals) if bUser.medals else "None")
    embed.add_field(name="Classic Mode", value="Enabled" if bUser.classicModeEnabled else "Disabled")

    await message.author.send(embed=embed)

botCommands.register("user-status", dev_cmd_user_status, 3, allowDM=True, useDoc=True)


async def dev_cmd_bounty_status(message: discord.Message, args: str, isDM: bool):
    """developer command sending a DM containing info about the specified bounty

    :param discord.Message message: the discord message calling the command
    :param str args: a criminal name
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    # look up the criminal object
    criminalObj = None
    for crim in bbData.builtInCriminalObjs.keys():
        if bbData.builtInCriminalObjs[crim].isCalled(args):
            criminalObj = bbData.builtInCriminalObjs[crim]

    # report unrecognised criminal names
    if criminalObj is None:
        await message.reply("Unknown criminal")
        return

    bGuild: basedGuild.BasedGuild = botState.client.guildsDB.getGuild(message.guild.id)
    if bGuild.bountiesDisabled:
        await message.reply("Bounties disabled here")
        return

    try:
        b = bGuild.bountiesDB.getBountyByCrim(criminalObj)
    except KeyError:
        try:
            b = bGuild.bountiesDB.getEscapedBountyByCrim(criminalObj)
        except KeyError:
            await message.reply("Bounty is not wanted in this server")
            return

    embed = discord.Embed(title="Bounty Status", colour=discord.Colour.random())

    embed.add_field(name="Criminal", value="\n".join([
        f"Name: {b.criminal.name}",
        f"Faction: {b.criminal.faction}",
        f"Wiki: {b.criminal.wiki}",
        f"Is Player: {b.criminal.isPlayer}",
        f"Built-In: {b.criminal.builtIn}",
        f"Is escaped: {b.isEscaped()}"
    ]))

    embed.add_field(name="Stats", value=f"Faction: {b.faction}\nTech level/Difficulty: {b.techLevel}\n" \
                                        + f"Reward: {b.reward}\nReward per check: {b.rewardPerSys}")

    embed.add_field(name="Times", value=f"Issued: {datetime.utcfromtimestamp(b.issueTime).strftime('%d/%m/%Y, %H:%M:%S')}\n" \
                                    + f"ExpiryTT: {describeTT(b.expiryTT)}\n" \
                                    + f"RespawnTT: {describeTT(b.respawnTT)}")
    
    embed.add_field(name="Route", value="\n".join(f"{s}: " + (f"{botState.client.get_user(u)} ({u})" if u != -1 else "unchecked") for s, u in b.checked.items()))
    embed.add_field(name="Answer", value=b.answer)

    botState.client.logger.log("dev_misc", "dev_cmd_bounty_status",
                        f"Bounty answer revealed to user {message.author} ({message.author.id}). " \
                        + f"Bounty: {b.criminal.name} in {message.guild} ({message.guild.id})",
                        category=LogCategory.bountiesDB, eventType="CHEAT")

    if b.activeShip is None:
        shipStr = "None"
    else:
        shipStr = f"{b.activeShip.name}\nNickname: {b.activeShip.nickname if b.activeShip.hasNickname else ''}\n" \
                + f"Armour: {b.activeShip.armour}\n" \
                + f"Cargo: {b.activeShip.cargo}\n" \
                + f"Handling: {b.activeShip.handling}\n" \
                + f"Max secondaries: {b.activeShip.maxSecondaries}\n" \
                + f"Primaries: {len(b.activeShip.weapons)}/{b.activeShip.maxPrimaries}:\n" \
                    + ((f"- " + ", ".join(i.name for i in b.activeShip.weapons) + "\n") if b.activeShip.weapons else '') \
                + f"Modules: {len(b.activeShip.modules)}/{b.activeShip.maxModules}:\n" \
                    + ((f"- " + ", ".join(i.name for i in b.activeShip.modules) + "\n") if b.activeShip.modules else '') \
                + f"Turrets: {len(b.activeShip.turrets)}/{b.activeShip.maxTurrets}:\n" \
                    + ((f"- " + ", ".join(i.name for i in b.activeShip.turrets) + "\n") if b.activeShip.turrets else '') \
                + f"Upgrades: " + ", ".join(i.name for i in b.activeShip.upgradesApplied) + "\n" \
                + f"Skin: " + (b.activeShip.skin.name if b.activeShip.skin is not None else 'None')

    embed.add_field(name="Active Ship", value=f"Has ship: {b.hasShip}\n{shipStr}")
    
    await message.author.send(embed=embed)

botCommands.register("bounty-status", dev_cmd_bounty_status, 3, signatureStr="**bounty-status <criminal name>**", useDoc=True)


BOUNTY_EDIT_FIELDS = {
    "activeShip",
    "faction",
    "issueTime",
    "endTime",
    "expired",
    "route",
    "reward",
    "rewardPerSys",
    "checked",
    "answer",
    "techLevel",
    "respawnTime"
}

async def dev_cmd_edit_bounty(message: discord.Message, args: str, isDM: bool):
    """developer command editing a value on a bounty

    :param discord.Message message: the discord message calling the command
    :param str args: a guild id or 'here' a criminal name `+`a field name `+`a new value
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if args.endswith("-u"):
        updateBBC = True
        args = args[:-2]
    else:
        updateBBC = False
    guildRef = args.split(" ")[0]
    if guildRef == "here":
        guildId = message.guild.id
    elif not lib.stringTyping.isInt(guildRef):
        await message.reply(f"Invalid guild id: {guildRef}")
        return
    else:
        guildId = int(guildRef)
    
    argsSplit = args[len(guildRef) + 1:].split("+")
    if len(argsSplit) < 3:
        await message.reply("Invalid args. Use the format: `edit-bounty <guild id or here> <criminal> +<field> +<value>`")
        return
    
    crimName, fieldName, newValue = map(str.strip, argsSplit)

    if fieldName not in BOUNTY_EDIT_FIELDS:
        await message.reply(f"Unknown field '{fieldName}'. This parameter is case sensitive. Possible values:\n{', '.join(BOUNTY_EDIT_FIELDS)}")
        return

    # look up the criminal object
    criminalObj = None
    for crim in bbData.builtInCriminalObjs.keys():
        if bbData.builtInCriminalObjs[crim].isCalled(crimName):
            criminalObj = bbData.builtInCriminalObjs[crim]

    # report unrecognised criminal names
    if criminalObj is None:
        await message.reply(f"Unknown criminal '{crimName}`")
        return

    try:
        bGuild: basedGuild.BasedGuild = botState.client.guildsDB.getGuild(guildId)
    except KeyError:
        await message.reply(f"Unknown guild: {guildRef}")
        return
    if bGuild.bountiesDisabled:
        await message.reply("Bounties disabled here")
        return

    try:
        b = bGuild.bountiesDB.getBountyByCrim(criminalObj)
    except KeyError:
        try:
            b = bGuild.bountiesDB.getEscapedBountyByCrim(criminalObj)
        except KeyError:
            await message.reply("Bounty is not wanted in this server")
            return

    if fieldName == "activeShip":
        oldTL = b.techLevel
        if newValue.lower() in ["null", "none"]:
            if b.hasShip:
                b.unequipShip()
        else:
            try:
                shipDict = json.loads(newValue)
                newShip = shipItem.Ship.deserialize(shipDict)
            except Exception as e:
                await message.reply(f"{type(e).__name__} when deserializing new ship: {e}")
                botState.client.logger.log("dev_misc", "dev_cmd_edit_bounty", exception=e, event="")
                return

            if b.hasShip:
                b.unequipShip()
            b.equipShip(newShip)
        b.techLevel = oldTL

    elif fieldName == "faction":
        if newValue not in bbData.bountyFactions:
            await message.reply(f"Unknown faction. This parameter is case sensitive. Possible values:\n{', '.join(bbData.bountyFactions)}")
            return
        
        if newValue == b.faction:
            await message.reply("No change. Writing anyway.")
        b.faction = newValue

    elif fieldName == "issueTime":
        try:
            newTime = datetime.utcfromtimestamp(float(newValue))
        except Exception as e:
            await message.reply(f"{type(e).__name__} error converting timestamp str to datetime: {e}")
            botState.client.logger.log("dev_misc", "dev_cmd_edit_bounty", exception=e, event="")
            return

        if newTime == b.issueTime:
            await message.reply("No change. Writing anyway.")
        b.issueTime = newTime.timestamp()

    elif fieldName == "endTime":
        try:
            newTime = datetime.utcfromtimestamp(float(newValue))
        except Exception as e:
            await message.reply(f"{type(e).__name__} error converting timestamp str to datetime: {e}")
            botState.client.logger.log("dev_misc", "dev_cmd_edit_bounty", exception=e, event="")
            return

        if newTime == b.endTime:
            await message.reply("No change. Writing anyway.")
            
        if b.expiryTT is not None:
            b.expiryTT.forceExpire(callExpiryFunc=False)

        if newTime < datetime.utcnow():
            b.expiryTT = None
            await b.expire(dbReload=True)
        else:
            b.expiryTT = timedTask.TimedTask(datetime.utcnow(), newTime, None, b.expire)
            botState.client.taskScheduler.scheduleTask(b.expiryTT)

        b.endTime = newTime.timestamp()

    elif fieldName == "expired":
        if newValue.lower() == "false":
            newExpired = False
        elif newValue.lower() == "true":
            newExpired = True
        else:
            await message.reply("Unknown value for expired. Must be boolean.")
            return

        if newExpired == b.expired:
            await message.reply("No change.")
            return
        elif newExpired:
            await b.expire()
        else:
            endDT = datetime.utcfromtimestamp(b.endTime)
            if endDT < datetime.utcnow():
                await message.reply("bounty expiry time is in the past. Set a new expiry time to unexpire bounty.")
                return
            b.expiryTT = timedTask.TimedTask(datetime.utcnow(), endDT, None, b.expire)
            botState.client.taskScheduler.scheduleTask(b.expiryTT)
    

    elif fieldName == "route":
        routeSplit = list(map(str.strip, newValue.split(",")))
        if len(routeSplit) == 0:
            await message.reply("invalid route. Give as a comma-separated list of system names.")
            return

        parsedRoute = []
        for s in routeSplit:
            try:
                syst: solarSystem.SolarSystem = next(i for i in bbData.builtInSystemObjs.values() if i.isCalled(s))
            except StopIteration:
                await message.reply(f"Unknown system: '{s}'")
                return
            parsedRoute.append(syst.name)

        if parsedRoute == b.route:
            await message.reply("No change.")
            return

        if b.answer not in parsedRoute:
            b.answer = random.choice(parsedRoute)
            await message.reply("Answer randomized")

        b.route = parsedRoute
        b.checked = {s: b.checked.get(s, -1) for s in parsedRoute}

    elif fieldName == "reward":
        if not lib.stringTyping.isInt(newValue) or int(newValue) < 0:
            await message.reply(f"Invalid reward: {newValue}")
            return
        newReward = int(newValue)
        if newReward == b.reward:
            await message.reply("No change. Writing anyway.")
            
        b.rewardPerSys = newReward // len(b.route)
        b.reward = newReward

    elif fieldName == "rewardPerSys":
        if not lib.stringTyping.isInt(newValue) or int(newValue) < 0:
            await message.reply(f"Invalid reward per sys: {newValue}")
            return
        newReward = int(newValue)
        if newReward == b.reward:
            await message.reply("No change. Writing anyway.")
            
        b.rewardPerSys = newReward
        b.rewardPerSys = newReward * len(b.route)

    elif fieldName == "checked":
        checkedSplit = newValue.split("\n")
        if len(checkedSplit) == 0:
            await message.reply("invalid checked. Give as a newline-separated list of system names: user ids.")
            return

        parsedChecked: Dict[str, int] = {}
        for pair in checkedSplit:
            pairSplit = list(map(str.strip, pair.split(":")))
            if len(pairSplit) != 2:
                await message.reply(f"Invalid mapping: '{pair}'. Must be <system>: <user id>")
                return
            s, u = pairSplit
            if not lib.stringTyping.isInt(u) or int(u) == 0 or int(u) < -1:
                await message.reply(f"invalid user ID: {u}")
                return
            try:
                syst = next(i for i in bbData.builtInSystemObjs if i.isCalled(s))
            except StopIteration:
                await message.reply(f"Unknown system: '{s}'")
                return
            parsedChecked[syst.name] = int(u)

        if parsedChecked == b.checked:
            await message.reply("No change.")
            return

        if b.answer not in parsedChecked:
            b.answer = random.choice(parsedChecked.keys())
            await message.reply("Answer randomized")

        b.checked = parsedChecked
        b.route = list(parsedChecked.keys())

    elif fieldName == "answer":
        try:
            syst = next(i for i in bbData.builtInSystemObjs.values() if i.isCalled(newValue))
        except StopIteration:
            await message.reply(f"Unknown system: '{newValue}'")
            return

        if syst.name == b.answer:
            await message.reply("No change.")
            return
        elif syst.name not in b.route:
            await message.reply("that system is not in the bounty's route. cancelled.")
            return
        b.answer = syst.name
        botState.client.logger.log("dev_misc", "dev_cmd_edit_bounty",
                        f"Bounty answer revealed to user {message.author} ({message.author.id}). " \
                        + f"Bounty: {b.criminal.name} in {message.guild} ({message.guild.id})",
                        category=LogCategory.bountiesDB, eventType="CHEAT")

    elif fieldName == "techLevel":
        if not lib.stringTyping.isInt(newValue) or int(newValue) < 0 or int(newValue) > cfg.maxTechLevel:
            await message.reply(f"invalid TL: {newValue}")
            return

        newLevel = int(newValue)

        if newLevel == b.techLevel:
            await message.reply("No change. Writing anyway.")

        if newLevel < b.division.minLevel or newLevel > b.division.maxLevel:
            try:
                newDiv = b.division.owningDB.divisionForLevel(newLevel)
            except KeyError:
                await message.reply("tech level is out of division range, but can't find a new division")
                b.techLevel = newLevel
            else:
                if b.division.bountyBoardChannel is not None and b.division.bountyBoardChannel.hasMessageForBounty(b):
                    await b.division.bountyBoardChannel.removeBounty(b)
                
                if b.isEscaped():
                    b.division.removeEscapedBountyObj(b)
                    b.techLevel = newLevel
                    newDiv._addEscapedBounty(b)
                else:
                    b.division.removeBountyObj(b)
                    if b.division.isEmpty(includeEscaped=False) and b.division.bountyBoardChannel.noBountiesMessage is None:
                        b.division.bountyBoardChannel.noBountiesMessage = await b.division.bountyBoardChannel._sendNoBountiesMessage()
                    if newDiv.bountyBoardChannel is not None and newDiv.isEmpty(includeEscaped=False) and newDiv.bountyBoardChannel.noBountiesMessage is not None:
                        await newDiv.bountyBoardChannel.noBountiesMessage.delete()
                        newDiv.bountyBoardChannel.noBountiesMessage = None
                    b.techLevel = newLevel
                    newDiv._addBounty(b, dbReload=True)
                    
                b.division = newDiv
                await message.reply("moved division")
        else:
            b.techLevel = newLevel


    elif fieldName == "respawnTime":
        try:
            newTime = datetime.utcfromtimestamp(float(newValue))
        except Exception as e:
            await message.reply(f"{type(e).__name__} error converting timestamp str to datetime: {e}")
            botState.client.logger.log("dev_misc", "dev_cmd_edit_bounty", exception=e, event="")
            return

        if b.respawnTT is not None and newTime == b.respawnTT.expiryTime:
            await message.reply("No change. Writing anyway.")
        
        if b.respawnTT is not None:
            await b.respawnTT.forceExpire(callExpiryFunc=False)

        respawnTT = timedTask.TimedTask(expiryDelta=timedelta(minutes=len(b.route)), 
                                        expiryFunction=b._respawn,
                                        rescheduleOnExpiryFuncFailure=True)

        if not b.isEscaped():
            b.escape()
            if b.division.bountyBoardChannel is not None:
                await bGuild.updateBountyBoardChannel(b, bountyComplete=True)
                await b.division.bountyBoardChannel.updateEscapedBountiesMessage()

        b.respawnTT = respawnTT
        botState.client.taskScheduler.scheduleTask(b.respawnTT)
        b.endTime = newTime.timestamp()

    await message.reply("Success!")
    if updateBBC and b.division.bountyBoardChannel is not None:
        if b.isEscaped():
            await b.division.bountyBoardChannel.updateEscapedBountiesMessage()
            if b.division.bountyBoardChannel.hasMessageForBounty(b):
                await b.division.bountyBoardChannel.removeBounty(b)
        else:
            if b.division.bountyBoardChannel.hasMessageForBounty(b):
                await b.division.bountyBoardChannel.updateBountyMessage(b)
            else:
                await b.division.bountyBoardChannel._sendBountyMsg(b)


botCommands.register("edit-bounty", dev_cmd_edit_bounty, 3, signatureStr="**edit-bounty <guild id or here> <criminal name> +<field> +<value>**", useDoc=True, forceKeepArgsCasing=True)


async def dev_cmd_force_update_listing(message: discord.Message, args: str, isDM: bool):
    """developer command forcing a BBC listing update on a bounty

    :param discord.Message message: the discord message calling the command
    :param str args: a guild id or 'here' followed by a criminal name
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    argsSplit = args.split(" ")
    if len(argsSplit) < 2:
        await message.reply("Invalid args. Give guild id or 'here' and a criminal name")
        return

    guildRef = argsSplit[0]
    criminalRef = " ".join(argsSplit[1:])

    if guildRef == "here":
        guildId = message.guild.id
    elif not lib.stringTyping.isInt(guildRef):
        await message.reply(f"Invalid guild id: {guildRef}")
        return
    else:
        guildId = int(guildRef)

    # look up the criminal object
    criminalObj = None
    for crim in bbData.builtInCriminalObjs.keys():
        if bbData.builtInCriminalObjs[crim].isCalled(criminalRef):
            criminalObj = bbData.builtInCriminalObjs[crim]

    # report unrecognised criminal names
    if criminalObj is None:
        await message.reply(f"Unknown criminal '{criminalRef}`")
        return

    try:
        bGuild: basedGuild.BasedGuild = botState.client.guildsDB.getGuild(guildId)
    except KeyError:
        await message.reply(f"Unknown guild: {guildRef}")
        return
    if bGuild.bountiesDisabled:
        await message.reply("Bounties disabled here")
        return
    if not bGuild.hasBountyBoardChannels:
        await message.reply("Guild has bounty board channels disabled")
        return

    try:
        b = bGuild.bountiesDB.getBountyByCrim(criminalObj)
    except KeyError:
        try:
            b = bGuild.bountiesDB.getEscapedBountyByCrim(criminalObj)
        except KeyError:
            await message.reply("Bounty is not wanted in this server")
            return

    if b.division.bountyBoardChannel.hasMessageForBounty(b):
        await b.division.bountyBoardChannel.updateBountyMessage(b)
    else:
        await b.division.bountyBoardChannel._sendBountyMsg(b)
    await message.reply("success!")

botCommands.register("force-update-listing", dev_cmd_force_update_listing, 3, signatureStr="**force-update-listing <guild id or here> <criminal name>**", useDoc=True, forceKeepArgsCasing=True)
