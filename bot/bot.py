# Set up bot config

from typing import List, Literal, Optional, Union, cast
from bot.cfg import cfg

# Discord Imports

import discord
from discord import Embed, InteractionResponded, Member, app_commands, Interaction
from discord.ext.commands import ExtensionNotLoaded
from discord.abc import GuildChannel
from discord.app_commands import AppCommandError
from discord.utils import utcnow, MISSING
from discord.ui import View

# Util imports

from datetime import datetime, timedelta
import os
import traceback
import asyncio


# BASED Imports

from bot import lib, botState
from bot.lib import BASED_version
from bot.lib.discordUtil import timestamp, TimeStampStyle
from bot.databases import bountyDB
from bot.scheduling.timedTask import TimedTask
from bot.gameObjects.bounties.bountyBoards.bountyBoardChannel import BountyBoardChannel

# register as spawnable
from .gameObjects.items.tools import creditsTool, throwSnowballTool

from bot import lib, botState
from bot.lib import BASED_version
from bot.client import BasedClient
from bot.logging import LogCategory


def setHelpEmbedThumbnails():
    """Loads the bot application's profile picture into all help menu embeds as the embed thumbnail.
    If no profile picture is set for the application, the default profile picture is used instead.
    """
    if botState.client.user is None:
        raise ValueError("Cannot set help embed thumbs because the client is not yet logged in")
    avatar = botState.client.user.display_avatar.url
    for levelSection in botCommands.helpSectionEmbeds:
        for helpSection in levelSection.values():
            for embed in helpSection:
                embed.set_thumbnail(url=avatar)


async def initializeBountyBoardChannels():
    for guild in botState.client.guildsDB.getGuilds():
        if guild.hasBountyBoardChannels:
            # Casting here because the guild is guaranteed to have a BountyDB if hasBountyBaordChannels is true
            for div in cast(bountyDB.BountyDB, guild.bountiesDB).divisions.values():
                try:
                    # Casting here because each division in the db is guaranteed to have a bountyBoardChannel if hasBountyBoardChannels is true at the guild level
                    await cast(BountyBoardChannel, div.bountyBoardChannel).init(botState.client)
                except lib.exceptions.NoLongerExists:
                    botState.client.logger.log("main", "initializeBountyBoardChannels",
                                        # Casting here because each division in the db is guaranteed to have a bountyBoardChannel if hasBountyBoardChannels is true at the guild level
                                        f"failed to load bountyboard channel {cast(BountyBoardChannel, div.bountyBoardChannel).channelIDToBeLoaded}" \
                                            + f" for guild {guild.id}, division {bountyDB.nameForDivision(div)}. Removing.",
                                        category=LogCategory.bountyBoards, eventType="UKWN_CHAN")
                    div.removeBountyBoardChannel()


def inferUserPermissions(message: discord.Message) -> int:
    """Get the commands access level of the user that sent the given message.

    :return: message.author's access level, as an index of cfg.userAccessLevels
    :rtype: int
    """
    if message.author.id in cfg.developers:
        return 3
    # Performing a Member cast here, because we already know that the channel is in a guild, so the author must be a member.
    elif isinstance(message.channel, GuildChannel) and message.channel.permissions_for(cast(Member, message.author)).administrator:
        return 2
    else:
        return 0


####### GLOBAL VARIABLES #######

# interface into the discord servers
botState.client = BasedClient()

async def loadExtensions():
    for c in cfg.includedCogs:
        await botState.client.load_extension(c)


# commands DB
from . import commands
botCommands = commands.loadCommands()


###### ERROR HANDLING ######

async def _errorResponse(interaction: Interaction, content: Optional[str] = "", embed: Embed = MISSING, view: View = MISSING):
    if content == "":
        content = "🥴 An unexpected error occured when processing this action.\n" \
                    + "The error has been logged, this probably won't work until we've looked into it.\n" \
                    + f"When reporting this issue, please quote interaction ID: `{interaction.id}`"
    if interaction.response.is_done():
        try:
            await interaction.followup.send(content=content or MISSING, embed=embed, view=view)
        except InteractionResponded:
            pass
        except Exception as e:
            botState.client.logger.log("MAIN", _errorResponse.__name__, f"Failed to inform user of failed interaction: {e}", exception=e, interaction=interaction)
    else:
        try:
            await interaction.response.send_message(content=content, embed=embed, view=view)
        except Exception as e:
            botState.client.logger.log("MAIN", _errorResponse.__name__, f"Failed to inform user of failed interaction: {e}", exception=e, interaction=interaction)

@botState.client.tree.error
async def on_app_command_error(interaction: Interaction, error: AppCommandError):
    # Casting here because this code is only reached for app command errors
    command = cast(Union[app_commands.Command, app_commands.ContextMenu], interaction.command)

    if isinstance(error, app_commands.NoPrivateMessage):
        await interaction.response.send_message(":x: This command cannot be used from DMs.", ephemeral=True)
    elif isinstance(error, (app_commands.MissingRole, app_commands.MissingAnyRole, app_commands.MissingPermissions)):
        await interaction.response.send_message(":x: You do not have permission to use this command.", ephemeral=True)
    elif isinstance(error, app_commands.BotMissingPermissions):
        await interaction.response.send_message(f":x: This command cannot be processed, because I am missing the following permissions: {', '.join(error.missing_permissions)}", ephemeral=True)
    elif isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f":x: This command is on cooldown. Try again after: {timestamp(utcnow() + timedelta(seconds=error.retry_after), TimeStampStyle.Relative)}", ephemeral=True)
    elif isinstance(error, app_commands.CommandNotFound):
        parentsStr = ":".join(error.parents)
        qualified = (f"{parentsStr}:" if parentsStr else "") + error.name
        botState.client.logger.log("MAIN", qualified, "Unknown command called. Please re-sync commands to fix this error.", exception=error, interaction=interaction)
        await interaction.response.send_message("🥴 This command could not be found, the error has been logged. Please refresh your window to retrive the latest set of commands.", ephemeral=True)
    elif isinstance(error, app_commands.CommandAlreadyRegistered):
        botState.client.logger.log("MAIN", on_app_command_error.__name__, f"Error loading app command '{error}': already registered.", exception=error, interaction=interaction)
        await _errorResponse(interaction, content=f"Error loading app command '{error}': already registered.")
        raise error
    elif isinstance(error, app_commands.CommandLimitReached):
        botState.client.logger.log("MAIN", on_app_command_error.__name__, f"Error loading app command '{error}': maximum number of commands reached.", exception=error, interaction=interaction)
        await _errorResponse(interaction, content=f"Error loading app command '{error}': maximum number of commands reached.")
        raise error
    elif isinstance(error, app_commands.CommandSignatureMismatch):
        botState.client.logger.log(command.module or "MAIN", command.callback.__name__, "Command signature mismatch on call. Please re-sync commands to fix this error.", exception=error, interaction=interaction)
        await interaction.response.send_message("🥴 Unexpected arguments were supplied, the error has been logged. Please refresh your window to retrive the latest set of commands.", ephemeral=True)
    elif isinstance(error, app_commands.CommandSyncFailure):
        botState.client.logger.log("MAIN", on_app_command_error.__name__, f"Error loading synchronizing commands: {error.code}{error.text}", exception=error, interaction=interaction)
        await _errorResponse(interaction, content=f"Error loading synchronizing commands: {error.code}{error.text}")
        raise error
    else:
        await _errorResponse(interaction)
        botState.client.logger.log(command.module or "MAIN", command.callback.__name__, "", exception=error, interaction=interaction)


####### UTIL FUNCTIONS #######

async def announceNewShopStock(guildID: int = -1):
    """Announce the refreshing of shop stocks to one or all joined guilds.
    Messages will be sent to the playChannels of all guilds in the botState.client.guildsDB, if they have one

    :param int guildID: The guild to announce to. If guildID is -1, the shop refresh will be announced to all joined guilds.
                        (Default -1)
    """
    if guildID == -1:
        # loop over all guilds
        for guild in botState.client.guildsDB.guilds.values():
            # ensure guild has a valid playChannel
            if not guild.shopsDisabled:
                await guild.announceNewShopStock()
    else:
        guild = botState.client.guildsDB.getGuild(guildID)
        # ensure guild has a valid playChannel
        if not guild.shopsDisabled:
            await guild.announceNewShopStock()


async def refreshAndAnnounceAllShopStocks():
    """Generate new tech levels and inventories for the shops of all joined guilds,
    and announce the stock refresh to those guilds.
    """
    botState.client.guildsDB.refreshAllShopStocks()
    await announceNewShopStock()



####### SYSTEM COMMANDS #######

async def err_nodm(message: discord.Message, args: str, isDM: bool):
    """Send an error message when a command is requested that cannot function outside of a guild

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: ignored
    """
    await message.reply("This command can only be used from inside of a server.", mention_author=False)


async def err_tempDisabled(message: discord.Message, args: str, isDM: bool):
    """Send an error message when a bounties command is requested - all bounty and shop related behaviour is
    currently disabled.

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: ignored
    """
    await message.reply(":x: All bounty/shop behaviour is currently disabled while I work on new features \\:)",
                        mention_author=False)


async def err_tempPerfDisabled(message: discord.Message, args: str, isDM: bool):
    """Send an error message when a command is requested that is disabled for perfornance reasons.

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: ignored
    """
    await message.reply(":x: This command has been temporarily disabled as it requires too much processing power. " \
                                + "It may return in the future once hosting hardware has been upgraded! \\:)",
                        mention_author=False)


async def dummy_command(message: discord.Message, args: str, isDM: bool):
    """Dummy command doing nothing at all.
    Useful when waiting for commands with client.wait_for from a non-blocking process.

    :param discord.Message message: ignored
    :param str args: ignored
    :param bool isDM: ignored
    """
    pass

botCommands.register("cancel", dummy_command, 0, allowDM=True, noHelp=True)



####### MAIN FUNCTIONS #######

@botState.client.event
async def on_guild_join(guild: discord.Guild):
    """Create a database entry for new guilds when one is joined.
    TODO: Once deprecation databases are implemented, if guilds now store important information consider searching for
    them in deprecated

    :param discord.Guild guild: the guild just joined.
    """
    if not (guildExists := botState.client.guildsDB.idExists(guild.id)):
        botState.client.guildsDB.addDcGuild(guild)

    botState.client.logger.log("Main", "guild_join", "I joined a new guild! " + guild.name + "#" + str(guild.id) +
                            ("\n -- The guild was added to botState.client.guildsDB" if not guildExists else ""),
                            category=LogCategory.guildsDB, eventType="NW_GLD")


@botState.client.event
async def on_guild_remove(guild: discord.Guild):
    """Remove the database entry for any guilds the bot leaves.
    TODO: Once deprecation databases are implemented, if guilds now store important information consider moving
    them to deprecated.

    :param discord.Guild guild: the guild just left.
    """
    guildExists = False
    if botState.client.guildsDB.idExists(guild.id):
        guildExists = True
        botState.client.guildsDB.removeID(guild.id)

    botState.client.logger.log("Main", "guild_remove", "I left a guild! " + guild.name + "#" + str(guild.id) +
                            ("\n -- The guild was removed from botState.client.guildsDB" if guildExists else ""),
                            category=LogCategory.guildsDB, eventType="NW_GLD")


@botState.client.event
async def on_ready():
    botState.utcOffset = datetime.now() - datetime.utcnow()
    print(f"System time UTC offset measured at: {lib.timeUtil.td_format_noYM(botState.utcOffset) or 'None'}")


    ##### SCHEDULING #####

    botState.shopRefreshTT = TimedTask(expiryDelta=cfg.timeouts.shopRefresh,
                                        autoReschedule=True,
                                        expiryFunction=refreshAndAnnounceAllShopStocks)
                                        
    botState.client.taskScheduler.scheduleTask(botState.shopRefreshTT)


    ##### SCHEDULING CONTINUED #####
    # to be moved
    # Schedule guild activity measurement decaying
    botState.temperatureDecayTT = TimedTask(expiryDelta=cfg.timeouts.guildActivityDecay,
                                            autoReschedule=True, expiryFunction=botState.client.guildsDB.decayAllTempsAsync)
    botState.client.taskScheduler.scheduleTask(botState.temperatureDecayTT)


    ##### CLEANUP #####

    await initializeBountyBoardChannels()

    # Set help embed thumbnails
    setHelpEmbedThumbnails()

    print(f"BASED {BASED_version.BASED_VERSION} loaded.\nClient logged in as {botState.client.user}")

    # Set custom bot status
    if cfg.statusMessage:
        await botState.client.change_presence(activity=discord.Game(cfg.statusMessage))
    else:
        await botState.client.change_presence(activity=discord.Game("Galaxy on Fire 2 HD™"))


@botState.client.event
async def on_message(message: discord.Message):
    """Called every time a message is sent in a server that the bot has joined
    Currently handles:
    - command calling

    :param discord.Message message: The message that triggered this command on sending
    """
    if not botState.client.loggedIn:
        return
        
    # ignore messages sent by bots
    if message.author.bot:
        return
    
    # if message.author.id in cfg.developers and message.content.lower() == "$bbinitslashcommandsync":
    #     if not cfg.developmentGuilds:
    #         await message.reply("No development guilds are configured.")
    #         return
        
    #     await message.reply(f"performing initial app commands sync in {len(cfg.developmentGuilds)} development guilds...")
    #     for guild in cfg.developmentGuilds:
    #         try:
    #             syncedCommands = await botState.client.tree.sync(guild=guild)
    #         except discord.DiscordException as ex:
    #             await message.reply(f"Failed to sync to guild {guild.id}: {type(ex).__name__} \"{ex}\"")
    #         else:
    #             await message.reply(f"{len(syncedCommands)} commands synced to guild {guild.id}")

    # React to messages containing or mentioning bountybot
    try:
        if "bountybot" in message.content or botState.client.user in message.mentions:
            await message.add_reaction("👀")
        if "<:tex:723331420919169036>" in message.content:
            await message.add_reaction("<:tex:723331420919169036>")
    except discord.Forbidden:
        pass
    except discord.HTTPException:
        pass


@botState.client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    """Called every time a reaction is added to a message.
    If the message is a reaction menu, and the reaction is an option for that menu, trigger the menu option's behaviour.

    :param discord.RawReactionActionEvent payload: An event describing the message and the reaction added
    """
    if not botState.client.loggedIn:
        return

    # ignore bot reactions
    # ignoring a warning here that Client.user can be None, if the client is not logged in.
    # The client will always be logged in here, because this event can only be triggered by discord reactions.
    if payload.user_id != botState.client.user.id: # type: ignore[reportOptionalMemberAccess] 
        # Get rich, useable reaction data
        _, user, emoji = await lib.discordUtil.reactionFromRaw(payload)
        if user is None or emoji is None:
            return

        # If the message reacted to is a reaction menu
        if payload.message_id in botState.client.reactionMenusDB and \
                botState.client.reactionMenusDB[payload.message_id].hasEmojiRegistered(emoji):
            # Envoke the reacted option's behaviour
            await botState.client.reactionMenusDB[payload.message_id].reactionAdded(emoji, user)


@botState.client.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    """Called every time a reaction is removed from a message.
    If the message is a reaction menu, and the reaction is an option for that menu, trigger the menu option's behaviour.

    :param discord.RawReactionActionEvent payload: An event describing the message and the reaction removed
    """
    if not botState.client.loggedIn:
        return
        
    # ignore bot reactions
    # ignoring a warning here that Client.user can be None, if the client is not logged in.
    # The client will always be logged in here, because this event can only be triggered by discord reactions.
    if payload.user_id != botState.client.user.id: # type: ignore[reportOptionalMemberAccess] 
        # Get rich, useable reaction data
        _, user, emoji = await lib.discordUtil.reactionFromRaw(payload)
        if user is None or emoji is None:
            return

        # If the message reacted to is a reaction menu
        if payload.message_id in botState.client.reactionMenusDB and \
                botState.client.reactionMenusDB[payload.message_id].hasEmojiRegistered(emoji):
            # Envoke the reacted option's behaviour
            await botState.client.reactionMenusDB[payload.message_id].reactionRemoved(emoji, user)


@botState.client.event
async def on_raw_message_delete(payload: discord.RawMessageDeleteEvent):
    """Called every time a message is deleted.
    If the message was a reaction menu, deactivate and unschedule the menu.

    :param discord.RawMessageDeleteEvent payload: An event describing the message deleted.
    """
    if not botState.client.loggedIn:
        return
        
    if payload.message_id in botState.client.reactionMenusDB:
        await botState.client.reactionMenusDB[payload.message_id].delete()


@botState.client.event
async def on_raw_bulk_message_delete(payload: discord.RawBulkMessageDeleteEvent):
    """Called every time a group of messages is deleted.
    If any of the messages were a reaction menus, deactivate and unschedule those menus.

    :param discord.RawBulkMessageDeleteEvent payload: An event describing all messages deleted.
    """
    if not botState.client.loggedIn:
        return
        
    for msgID in payload.message_ids:
        if msgID in botState.client.reactionMenusDB:
            await botState.client.reactionMenusDB[msgID].delete()


def removeViewFromMessageCallback(message: discord.Message):
    async def removeViewFromMessage(interaction: Interaction):
        await message.edit(content="🛑 Cancelled.", view=None)
    return removeViewFromMessage


def loadExtensionCallback(extensionName: str):
    async def loadExtension(interaction: Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await botState.client.load_extension(extensionName)
        except Exception as e:
            await interaction.followup.send(f"{type(e).__name__}: {e}", ephemeral=True)
        else:
            await interaction.followup.send(f"reloaded successfully!", ephemeral=True)
    return loadExtension


COMMON_EXTENSION_PATHS = ("bot.cogs", "bot.cogs.util")
def lookupExtension(extensionName: str) -> Optional[str]:
    """Look for a loaded extension with the given name, checking in folders where extensions are commonly kept.
    If the extension is found, the qualified name for the extension is returned. Otherwise, `None` is returned.

    :param str extensionName: The name of the extension to find
    :return: The qualified name of the loaded extension with name `extensionName` if one is loaded, `None` otherwise
    """
    if extensionName in botState.client.extensions:
        return extensionName
    for base in COMMON_EXTENSION_PATHS:
        if f"{base}.{extensionName}" in botState.client.extensions:
            return f"{base}.{extensionName}"
    return None


@botState.client.basedCommand(accessLevel=cfg.basicAccessLevels.developer, helpSection="extensions")
@app_commands.describe(extension_name="The name of the extension module. Can be just the name, or can be the qualified path.")
@app_commands.command(name="reload-extension",
                        description="Unload and re-load a cog or other extension.")
@app_commands.guilds(*cfg.developmentGuilds)
async def dev_cmd_reload_extension(interaction: Interaction, extension_name: str):
    await interaction.response.defer(ephemeral=True, thinking=True)
    _extension_name = lookupExtension(extension_name)
    found = _extension_name is not None

    if found:
        try:
            await botState.client.reload_extension(_extension_name)
        except ExtensionNotLoaded:
            found = False
        except Exception as e:
            await interaction.followup.send(f"{type(e).__name__}: {e}", ephemeral=True)
            return
        else:
            await interaction.followup.send(f"reloaded successfully!", ephemeral=True)
            return
            
    if not found:
        view = discord.ui.View()
        cancelButton = discord.ui.Button(style=discord.ButtonStyle.red, label="cancel")
        cancelButton.callback = removeViewFromMessageCallback(await interaction.original_response())
        acceptButton = discord.ui.Button(style=discord.ButtonStyle.green, label="load")
        acceptButton.callback = loadExtensionCallback(extension_name)
        view.add_item(cancelButton).add_item(acceptButton)
        await interaction.followup.send("No such extension is currently loaded. Load it?", ephemeral=True, view=view)

botState.client.tree.add_command(dev_cmd_reload_extension, guilds=cfg.developmentGuilds)


@botState.client.basedCommand(accessLevel=cfg.basicAccessLevels.developer, helpSection="extensions")
@app_commands.describe(extension_name="The fully qualified path to the extension module")
@app_commands.command(name="unload-extension",
                        description="Unload a cog or other extension.")
@app_commands.guilds(*cfg.developmentGuilds)
async def dev_cmd_unload_extension(interaction: Interaction, extension_name: str):
    await interaction.response.defer(ephemeral=True, thinking=True)
    _extension_name = lookupExtension(extension_name)
    found = _extension_name is not None

    if found:
        try:
            await botState.client.unload_extension(_extension_name)
        except Exception as e:
            await interaction.followup.send(f"{type(e).__name__}: {e}", ephemeral=True)
        else:
            await interaction.followup.send(f"unloaded successfully!", ephemeral=True)
    else:
        await interaction.followup.send(f"No such extension is currently loaded. Load it with `/reload-extension`.")

botState.client.tree.add_command(dev_cmd_unload_extension, guilds=cfg.developmentGuilds)


@botState.client.basedCommand(accessLevel=cfg.basicAccessLevels.developer, helpSection="commands",
                        formattedDesc="Sync app commands with guilds. Give no args to sync global commands, or give exactly one of `spec` or `guilds`",
                        formattedParamDescs=dict(spec="`here` to sync this guild, `copy to here` to copy global commands to this guild and sync"))
@app_commands.command(name="sync",
                        description="Sync app commands with guilds. Give no args to sync global commands, or give one of 'spec'/'guilds'")
@app_commands.describe(guilds="comma separated list of guild IDs to sync",
                        spec="'here' to sync this guild, 'copy to here' to copy global commands to this guild and sync")
@app_commands.guilds(*cfg.developmentGuilds)
async def dev_cmd_sync_app_commands(interaction: Interaction, guilds: Optional[str] = None, spec: Optional[Literal["here", "copy to here"]] = None) -> None:
    await interaction.response.defer(ephemeral=True, thinking=True)
    if not guilds:
        if not spec:
            try:
                fmt = await botState.client.tree.sync()
            except discord.app_commands.CommandSyncFailure as e:
                await interaction.followup.send(f"Failed to sync: {e.status} {e.text}")
            else:
                await interaction.followup.send(f"Synced {len(fmt)} commands globally")
        else:
            if interaction.guild is None:
                await interaction.followup.send("The spec option is only valid when used from within a guild")
                return
            if spec == "copy to here":
                botState.client.tree.copy_global_to(guild=interaction.guild)
            try:
                fmt = await botState.client.tree.sync(guild=interaction.guild)
            except discord.app_commands.CommandSyncFailure as e:
                await interaction.followup.send(f"Failed to sync: {e.status} {e.text}")
            else:
                await interaction.followup.send(f"{'Copied' if spec == 'copy to here' else 'Synced'} {len(fmt)} commands to the current guild")
        return

    synced: List[None] = []
    async def syncGuild(guild):
        try:
            await botState.client.tree.sync(guild=guild)
        except discord.HTTPException as e:
            raise e
        else:
            synced.append(None) # scoping workaround, can't use an int

    _guilds = set(map(lambda x: discord.Object(int(x)), guilds.split(", ")))

    tasks = lib.discordUtil.BasicScheduler()
    for guild in _guilds:
        tasks.add(syncGuild(guild))
    
    if tasks.any():
        await tasks.wait()
        if exceptions := tasks.getExceptions():
            tasks.logExceptions()
            await interaction.followup.send(f"Synced the tree to {len(synced)}/{len(_guilds)} guilds. {len(exceptions)} guild(s) failed to sync, exceptions have been logged.")
        else:
            await interaction.followup.send(f"Synced the tree to {len(synced)}/{len(_guilds)} guilds.")
    else:
        await interaction.followup.send(f"No syncing was performed: No guilds to sync to")

botState.client.tree.add_command(dev_cmd_sync_app_commands, guilds=cfg.developmentGuilds)


async def runAsync():
    """Runs the bot.
    If you wish to use a toml config file, ensure that you have loaded it first with carica.loadCfg.

    :return: A description of what behaviour should follow shutdown
    :rtype: int
    """
    # Ensure a bot token is provided
    if not (bool(cfg.botToken) ^ bool(cfg.botToken_envVarName)):
        raise ValueError("You must give exactly one of either cfg.botToken or cfg.botToken_envVarName")

    if cfg.botToken_envVarName and cfg.botToken_envVarName not in os.environ:
        raise KeyError("Bot token environment variable " + cfg.botToken_envVarName + " not set (cfg.botToken_envVarName")

    async with botState.client:
        await loadExtensions()
        # Launch bot
        await botState.client.start(cfg.botToken if cfg.botToken else os.environ[cfg.botToken_envVarName])
    
    return botState.client.shutDownState


def run():
    """Runs the bot.
    If you wish to use a toml config file, ensure that you have loaded it first with carica.loadCfg.

    :return: A description of what behaviour should follow shutdown
    :rtype: int
    """
    return asyncio.run(runAsync())
