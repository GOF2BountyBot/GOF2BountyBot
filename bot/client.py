import asyncio
from inspect import iscoroutinefunction
import signal
from typing import Any, Callable, Coroutine, List, Optional, Dict, Tuple, Union, cast, overload
from pathlib import Path
import aiohttp
import discord
from discord import Interaction, NotFound, User, app_commands, TextChannel
from discord.ext.commands import Bot as ClientBaseClass
from discord.ext import tasks
from discord.utils import MISSING
from datetime import datetime, timedelta
import os
from github.Repository import Repository

from bot.persistence import get_storage
from bot.persistence.repositories.user_repository import UserRepository
from bot.persistence.repositories.guild_repository import GuildRepository
from bot.interactions import accessLevels, commandChecks
from bot.databases import userDB, guildDB, reactionMenuDB
from bot import lib
from bot.cfg import cfg
from bot import logging
from bot.scheduling import timedTaskHeap
from bot.interactions import basedCommand, basedComponent, basedApp
from bot.users.basedGuild import BasedGuild
from bot.users import basedUser
from bot.cfg import gameConfigurator
from bot.reactionMenus import reactionMenu
from bot.baseClasses.serializable import SerializesToJson


class ShutDownState:
    restart = 0
    shutdown = 1
    update = 2


class GracefulKiller:
    """Class tracking receipt of SIGINT and SIGTERM signals under linux.
    This is used during the main loop to put the bot to sleep when requested.

    :var kill_now: Whether or not a termination signal has been received
    :vartype kill_now: bool
    """

    def __init__(self):
        """Register signal handlers"""
        self.kill_now = False
        signal.signal(signal.SIGINT, self.exit_gracefully) # keyboard interrupt
        signal.signal(signal.SIGTERM, self.exit_gracefully) # graceful exit request

    def exit_gracefully(self, signum, frame):
        """Termination signal received, mark kill indicator"""
        self.kill_now = True

def loadUsersDB(filePath: Union[Path, str]) -> userDB.UserDB:
    user_repo = UserRepository()
    users = user_repo.get_all()
    return users #userDB.UserDB(users)
    
    
    #storage = get_storage()

    #raw = storage.get_users_db_raw()
    #if raw:
    #    # convert raw dict → UserDB instance
    #    return userDB.UserDB.deserialize(raw)

    ## first run, file did not exist yet
    #return userDB.UserDB()


def loadGuildsDB(filePath: Union[Path, str]) -> guildDB.GuildDB:
    storage = get_storage()

    raw = storage.get_guilds_db_raw()
    if raw:
        # convert raw dict → UserDB instance
        return guildDB.GuildDB.deserialize(raw)

    # first run, file did not exist yet
    return guildDB.GuildDB()


async def loadReactionMenusDB(filePath: Union[Path, str]) -> reactionMenuDB.ReactionMenuDB:
    storage = get_storage()

    raw = storage.get_reaction_menus_raw()
    if raw:
        # convert raw dict → UserDB instance
        return reactionMenuDB.ReactionMenuDB.deserialize(raw)

    # first run, file did not exist yet
    return reactionMenuDB.ReactionMenuDB()


def waitBeforeStartingTask(task: tasks.Loop):
    async def inner():
        await asyncio.sleep(timedelta(seconds=task.seconds or 0, minutes=task.minutes or 0, hours=task.hours or 0).total_seconds())
    
    task.before_loop(inner)
    return task


class BasedClient(ClientBaseClass):
    """A minor extension to discord.ext.commands.Bot to include database saving and extended shutdown procedures.

    A command_prefix is assigned to this bot, but no commands are registered to it, so this is effectively meaningless.
    I chose to assign a zero-width character, as this is unlikely to ever be chosen as the bot's actual command prefix,
    minimising erroneous commands.Bot command recognition. 

    :var bot_loggedIn: Tracks whether or not the bot is currently logged in
    :vartype bot_loggedIn: bool
    :vartype launchTime: datetime
    :var killer: Indicator of when OS termination signals are received
    :vartype killer: GracefulKiller
    """

    def __init__(self, usersDB: Optional[userDB.UserDB] = None,
                        guildsDB: Optional[guildDB.GuildDB] = None,
                        reactionMenusDB: Optional[reactionMenuDB.ReactionMenuDB] = None,
                        logger: Optional[logging.Logger] = None,
                        httpClient: Optional[aiohttp.ClientSession] = None):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="‎", intents=intents)

        self._usersDB = usersDB
        self._guildsDB = guildsDB
        self._reactionMenusDB = reactionMenusDB
        self._dbsLoaded = None not in (usersDB, guildsDB, reactionMenusDB)

        self.loggedIn = False
        self.launchTime = discord.utils.utcnow()
        self.killer = GracefulKiller()

        self._taskScheduler = None
        self._schedulerLoaded = False
        self.shutDownState = ShutDownState.restart
        
        self.logger = logger if logger is not None else logging.Logger()
        self._httpClient = httpClient

        self.basedCommands: Dict[discord.app_commands.Command, "basedCommand.BasedCommandMeta"] = {}
        self.staticComponentCallbacks: Dict["basedComponent.StaticComponents", "basedComponent.StaticComponentCallbackMeta"] = {}

        self.helpSections: Dict[str, List[discord.app_commands.Command]] = {}

        self.add_listener(self.on_interaction)
        
        self._skinStorageChannel: Optional[TextChannel] = None
        self._skinRendersChannel: Optional[TextChannel] = None
        self._bountyRouteImagesChannel: Optional[TextChannel] = None
        self._mediaServersLoaded = False

        self._githubRepo = None
        self._githubClient = None
        self._githubLoaded = False


    async def on_interaction(self, interaction: discord.Interaction):
        customId = None if interaction.data is None else interaction.data.get("custom_id", None)
        if interaction.type != discord.InteractionType.component \
                or customId is None \
                or not basedComponent.customIdIsStaticComponent(customId):
            return
        componentMeta = basedComponent.staticComponentMeta(customId)
        if not self.hasStaticComponent(componentMeta.ID):
            return
        
        callbackMeta = self.getStaticComponentCallbackMeta(componentMeta.ID)
        cbArgs = (interaction, componentMeta.args) if callbackMeta.takesArgs else (interaction,)

        # Pass the owning object (e.g self/cls) to the callback if it needs one
        if basedApp.isCogApp(callbackMeta.callback):
            cogName = basedApp.getCogAppCogName(callbackMeta.callback)
            cog = self.get_cog(cogName)
            if cog is None:
                raise ValueError(f"unable to find cog '{cogName}' for static component: {callbackMeta.callback.__qualname__}")

        # Ignoring some warnings here for incorrect call syntax - pyright can't see that the tuple will always contain
        # the correct arguments, because we can't unpack a tuple until runtime
            await callbackMeta.callback(cog, *cbArgs) # type: ignore[reportGeneralTypeIssues]
        elif callbackMeta.hasSelf():
            await callbackMeta.callback(callbackMeta.cbSelf, *cbArgs) # type: ignore[reportGeneralTypeIssues]
        else:
            await callbackMeta.callback(*cbArgs) # type: ignore[reportGeneralTypeIssues]


    def addBasedCommand(self, command: discord.app_commands.Command):
        """Register a based command's metadata with the bot.
        This does not register for command calling. Use the default discord.py behaviour for this.

        :param command: The command to register
        :type command: discord.app_commands.Command
        :raises KeyError: If the command is already registered
        :raises ValueError: If the command has not been made into a BASED command with the `basedCommand` decorator
        """
        if basedApp.appType(command.callback) != basedApp.BasedAppType.AppCommand:
            raise ValueError(f"command {command.qualified_name} is not a BASED command")
        if command in self.basedCommands:
            raise KeyError(f"Command {command.qualified_name} is already registered")
        meta = basedCommand.commandMeta(command)
        if meta.helpSection not in self.helpSections:
            self.helpSections[meta.helpSection] = [command]
        elif len(self.helpSections) == 99:
            raise ValueError("Maximum help sections exceeded. Only 99 help sections are supported.")
        else:
            self.helpSections[meta.helpSection].append(command)
        self.basedCommands[command] = meta


    def addStaticComponent(self, callback: "basedComponent.StaticComponentCallbackType"):
        """Register a static component callback's metadata with the bot.
        This enables static component behaviour as described by the `staticComponentCallback` decorator.

        :param callback: The static component to register
        :type command: basedComponent.StaticComponentCallbackType
        :raises KeyError: If the component is already registered
        :raises ValueError: If the callback has not been made into a static component callback with the `staticComponentCallback` decorator
        """
        if basedApp.appType(callback) != basedApp.BasedAppType.StaticComponent:
            raise ValueError(f"callback {callback.__qualname__} is not a static component callback")
        
        meta = basedComponent.staticComponentCallbackMeta(callback)
        if meta.ID in self.staticComponentCallbacks:
            raise KeyError(f"Static component callback {callback.__qualname__} is already registered")

        self.staticComponentCallbacks[meta.ID] = meta


    def basedCommand(self,
        *,
        accessLevel: Union["accessLevels.AccessLevelType", str] = MISSING,
        showInHelp: bool = True,
        helpSection: Optional[str] = None,
        formattedDesc: Optional[str] = None,
        formattedParamDescs: Optional[Dict[str, str]] = None
    ):
        """Decorator that marks a discord app command as a BASED command.

        :param accessLevel: The access level required to use the command. A check will be added for this.
        :type accessLevel: Union[AccessLevelType, str], optional
        :param showInHelp: Whether or not to show the command in help listings, defaults to True
        :type showInHelp: bool, optional
        :param helpSection: The section of the help command in which to list this command, defaults to None
        :type helpSection: str, optional
        :param formattedDesc: A description of the command with more allowed length and markdown formatting, to be used in help commands, defaults to None
        :type formattedDesc: str, optional
        :param formattedParamDescs: Descriptions for each parameter of the command with more allowed length and markdown formatting, to be used in help commands, defaults to None
        :type formattedParamDescs: Dict[str, str], optional
        """
        def decorator(func, accessLevel=accessLevel, showInHelp=showInHelp, helpSection=helpSection, formattedDesc=formattedDesc, formattedParamDescs=formattedParamDescs):
            if not isinstance(func, app_commands.Command):
                raise TypeError("decorator can only be applied to app commands")

            if isinstance(accessLevel, str):
                accessLevel = accessLevels.accessLevelNamed(accessLevel)

            if helpSection is not None:
                basedCommand.validateHelpSection(helpSection)

            basedApp.basedApp(func.callback, basedApp.BasedAppType.AppCommand)
            setattr(func.callback, "__based_command_meta__", basedCommand.BasedCommandMeta(accessLevel, showInHelp, helpSection, formattedDesc, formattedParamDescs))
            self.addBasedCommand(func)

            if accessLevel is not MISSING:
                func.add_check(commandChecks.create_requireAccess(accessLevel))

            return func

        return decorator


    def staticComponentCallback(self, ID: "basedComponent.StaticComponents"):
        """Decorator marking a coroutine as a static component callback.
        The callback for static components identifying this callback by ID will be preserved across bot restarts

        Example usage:
        ```
        @bot.staticComponentCallback(StaticComponents.myCallback)
        async def myCallback(interaction: Interaction, args: str):
            await interaction.response.send_message(f"This static callback received args: {args}")

        @bot.app_commands.command(name="send-static-menu")
        async def sendStaticMenu(interaction: Interaction):
            staticButton = Button(label="send callback")
            staticButton = StaticComponents.myCallback(staticButton, args="hello")
            view.add_item(staticButton)
            await interaction.response.send_message(view=view)
        ```
        If the `send-static-menu` app command is sent, then a message will be sent in return with a button to trigger `myCallback`.
        Clicking this button will send another message with the content "hello".
        If the bot is restarted, then the button will still work.
        This works by attaching a known `custom_id` to the button, containing the static component ID and args.

        :var ID: The ID of the static component in the `StaticComponents` enum
        :type ID: StaticComponents
        """
        def decorator(func, ID=ID):
            if not iscoroutinefunction(func):
                raise TypeError("Decorator can only be applied to coroutines")

            cbSelf = basedComponent.validateStaticComponentCallbackSelf(func)
            basedApp.basedApp(func, basedApp.BasedAppType.StaticComponent)
            setattr(func, "__static_component_meta__", basedComponent.StaticComponentCallbackMeta(func, ID, cbSelf))
            self.addStaticComponent(func)

            return func

        return decorator


    def removeBasedCommand(self, command: discord.app_commands.Command):
        """Un-register a based command's metadata from the bot.
        This does not un-register for command calling. Use the default discord.py behaviour for this.

        :param command: The command to un-register
        :type command: discord.app_commands.Command
        :raises KeyError: If the command is not registered
        :raises ValueError: If the command has not been made into a BASED command with the `basedCommand` decorator
        """
        if basedApp.appType(command.callback) != basedApp.BasedAppType.AppCommand:
            raise ValueError(f"command {command.qualified_name} is not a BASED command")
        if command not in self.basedCommands:
            raise KeyError(f"Command {command.qualified_name} is not registered")
        meta = basedCommand.commandMeta(command)
        del self.basedCommands[command]
        if meta.helpSection in self.helpSections:
            self.helpSections[meta.helpSection].remove(command)
            if len(self.helpSections[meta.helpSection]) == 0:
                del self.helpSections[meta.helpSection]


    @overload
    def removeStaticComponent(self, callback: "basedComponent.StaticComponentCallbackType"):
        """Un-register a static component callback's metadata with the bot.
        This disables static component behaviour as described by the `staticComponentCallback` decorator.

        :param callback: The static component to un-register
        :type command: basedComponent.StaticComponentCallbackType
        :raises KeyError: If the component is not registered
        :raises ValueError: If the callback has not been made into a static component callback with the `staticComponentCallback` decorator
        """

    @overload
    def removeStaticComponent(self, ID: "basedComponent.StaticComponents"):
        """Un-register a static component callback's metadata with the bot.
        This disables static component behaviour as described by the `staticComponentCallback` decorator.

        :param ID: The ID of the component in the `StaticComponents` enum
        :type ID: basedComponent.StaticComponents
        :raises KeyError: If the component is not registered
        :raises ValueError: If the callback has not been made into a static component callback with the `staticComponentCallback` decorator
        """

    # ignoring a warning here bceause the two overloads for this method correctly use different names for their parameters
    def removeStaticComponent(self, val: Union["basedComponent.StaticComponentCallbackType", "basedComponent.StaticComponents"]): # type: ignore[reportGeneralTypeIssues]
        if not isinstance(val, basedComponent.StaticComponents):
            if basedApp.appType(val) != basedApp.BasedAppType.StaticComponent:
                raise ValueError(f"callback {val.__qualname__} is not a static component callback")
        
            meta = basedComponent.staticComponentCallbackMeta(val)
            ID = meta.ID
        else:
            ID = val

        if ID not in self.staticComponentCallbacks:
            raise KeyError(f"Static component callback {ID.name} is not registered")
        
        del self.staticComponentCallbacks[ID]


    def commandsInSectionForAccessLevel(self, section: str, level: "accessLevels.AccessLevelType") -> List[discord.app_commands.Command]:
        """Get the commands in help section `section` that require access level `level`

        :param section: The help section for commands to look up
        :type section: str
        :param level: The access level that commands should require
        :type level: accessLevels.AccessLevelType
        :return: A list of commands in help section `section` requiring access level `level`
        :rtype: List[discord.app_commands.Command]
        """
        return [c for c in self.helpSections[section] if basedCommand.accessLevel(c) is level and basedCommand.commandMeta(c).showInHelp]


    def helpSectionsForAccessLevel(self, level: "accessLevels.AccessLevelType") -> Dict[str, List[discord.app_commands.Command]]:
        """Get the commands for a particular access level, organized by help section

        :param level: The access level of commands to look up
        :type level: accessLevels.AccessLevelType
        :return: The commands that require `level`, organized by help section
        :rtype: Dict[str, List[discord.app_commands.Command]]
        """
        result = {section: self.commandsInSectionForAccessLevel(section, level) for section in self.helpSections}
        return {s: c for s, c in result.items() if c}


    @property
    def httpClient(self) -> aiohttp.ClientSession:
        if self._httpClient is None:
            raise lib.exceptions.NotReady("httpClient not yet loaded. BasedClient.httpClient is only available after on_ready.")
        return self._httpClient


    async def setup_hook(self):
        if self._httpClient is None:
            self._httpClient = aiohttp.ClientSession()

    
    @property
    def usersDB(self):
        """The bot's database of users.
        Databases are only available after on_ready.

        :raises lib.exceptions.NotReady: Databases not loaded yet
        :return: The bot's database of user metadata.
        :rtype: databases.userDB.UserDB
        """
        if not self._dbsLoaded:
            raise lib.exceptions.NotReady("Databases not yet loaded. BasedClient.usersDB is only available after on_ready.")
        return cast(userDB.UserDB, self._usersDB)


    @property
    def guildsDB(self):
        """The bot's database of guilds.
        Databases are only available after on_ready.

        :raises lib.exceptions.NotReady: Databases not loaded yet
        :return: The bot's database of user metadata.
        :rtype: databases.guildDB.GuildDB
        """
        if not self._dbsLoaded:
            raise lib.exceptions.NotReady("Databases not yet loaded. BasedClient.usersDB is only available after on_ready.")
        return cast(guildDB.GuildDB, self._guildsDB)


    @property
    def reactionMenusDB(self) -> reactionMenuDB.ReactionMenuDB:
        """The bot's database of reaction menus.
        Databases are only available after on_ready.

        :raises lib.exceptions.NotReady: Databases not loaded yet
        :return: The bot's database of user metadata.
        :rtype: databases.reactionMenuDB.ReactionMenuDB
        """
        if not self._dbsLoaded:
            raise lib.exceptions.NotReady("Databases not yet loaded. BasedClient.usersDB is only available after on_ready.")
        return cast(reactionMenuDB.ReactionMenuDB, self._reactionMenusDB)


    @property
    def skinStorageChannel(self):
        """A discord text channel for storing skin images.
        Only available after on_ready.

        :raises lib.exceptions.NotReady: Channel not loaded yet
        :return: A discord text channel for storing skin images.
        :rtype: TextChannel
        """
        if not self._dbsLoaded:
            raise lib.exceptions.NotReady("Not yet loaded. BasedClient.skinStorageChannel is only available after on_ready.")
        return cast(TextChannel, self._skinStorageChannel)


    @property
    def showmeRendersChannel(self):
        """A discord text channel for storing custom skin renders.
        Only available after on_ready.

        :raises lib.exceptions.NotReady: Channel not loaded yet
        :return: A discord text channel for storing custom skin renders.
        :rtype: TextChannel
        """
        if not self._dbsLoaded:
            raise lib.exceptions.NotReady("Not yet loaded. BasedClient.showmeRendersChannel is only available after on_ready.")
        return cast(TextChannel, self._skinRendersChannel)


    @property
    def bountyRouteImagesChannel(self):
        """A discord text channel for storing bounty route images.
        Only available after on_ready.

        :raises lib.exceptions.NotReady: Channel not loaded yet
        :return: A discord text channel for storing bounty route images.
        :rtype: TextChannel
        """
        if not self._dbsLoaded:
            raise lib.exceptions.NotReady("Not yet loaded. BasedClient.bountyRouteImagesChannel is only available after on_ready.")
        return cast(TextChannel, self._bountyRouteImagesChannel)

    
    @property
    def taskScheduler(self):
        """The bot's running task scheduler
        Only available after on_ready.

        :raises lib.exceptions.NotReady: scheduler not loaded yet
        :return: The bot's task scheduler.
        :rtype: TimedTaskHeap
        """
        if not self._schedulerLoaded:
            raise lib.exceptions.NotReady("Task scheduler not yet loaded. BasedClient.taskScheduler is only available after on_ready.")
        return cast(timedTaskHeap.AutoCheckingTimedTaskHeap, self._taskScheduler)


    @property
    def githubClient(self):
        """The bot's authenticated GitHub API client
        Only available after on_ready.

        :raises lib.exceptions.NotReady: client not loaded yet
        :return: The bot's authenticated GitHub API client.
        :rtype: Github
        """
        if not self._githubLoaded:
            raise lib.exceptions.NotReady("GitHub client not yet loaded. BasedClient.githubClient is only available after on_ready.")
        return cast(lib.github.BasedGithub, self._githubClient)


    @property
    def githubRepo(self):
        """The bot's authenticated GitHub repository API client
        Only available after on_ready.

        :raises lib.exceptions.NotReady: client not loaded yet
        :return: The bot's authenticated GitHub repository API client.
        :rtype: Repository
        """
        if not self._githubLoaded:
            raise lib.exceptions.NotReady("GitHub repo not yet loaded. BasedClient.githubRepo is only available after on_ready.")
        return cast(Repository, self._githubRepo)


    async def reloadDBs(self):
        """Load all savedata from file, and start the db saving task if it is not running.
        """
        self._dbsLoaded = True

        self._usersDB = loadUsersDB(cfg.paths.usersDB)
        print(f"{len(self._usersDB.users)} users loaded")
    
        self._guildsDB = loadGuildsDB(cfg.paths.guildsDB)
        async for guild in self.fetch_guilds(limit=None):
            if not self._guildsDB.idExists(guild.id):
                newGuild = BasedGuild.deserialize({}, guildID=guild.id)
                self._guildsDB.addBasedGuild(newGuild)
                
        print(f"{len(self._guildsDB.guilds)} guilds loaded")

        self._reactionMenusDB = await loadReactionMenusDB(cfg.paths.reactionMenusDB)

        print(f"{len(self._reactionMenusDB)} reaction menus loaded")

        if not self.dbSaveTask.is_running():
            self.dbSaveTask.start()


    def saveAllDBs(self):
        """Save all of the bot's savedata to file.
        This currently saves:
        - the users database
        - the guilds database
        - the reaction menus database
        - logs
        """
        storage = get_storage()
        storage.save_users_db_raw(self.usersDB.serialize())
        storage.save_guilds_db_raw(self.guildsDB.serialize())
        storage.save_reaction_menus_raw(self.reactionMenusDB.serialize())
        self.logger.save()


    async def shutdown(self):
        """Cleanly prepare for, and then perform, shutdown of the bot.

        This currently:
        - expires all non-saveable reaction menus
        - logs out of discord
        - saves all savedata to file
        """
        print("shutdown signal received, shutdown scheduled.")
        self.taskScheduler.stopTaskChecking()
        tasks = lib.discordUtil.BasicScheduler()
        # expire non-saveable reaction menus
        for menu in self.reactionMenusDB.values():
            if not reactionMenu.isSaveableMenuInstance(menu):
                tasks.add(menu.delete())
        await tasks.wait()
        tasks.logExceptions()
        
        # save bot save data
        self.saveAllDBs()

        # log out of discord
        self.loggedIn = False
        await self.close()
        # close the bot's aiohttp session
        await self.httpClient.close()
        print(datetime.now().strftime("%H:%M:%S: Shutdown complete."))


    @tasks.loop(seconds=cfg.timeouts.shutdownCheckPeriod.total_seconds())
    async def shutdownCheckTask(self):
        if self.killer.kill_now:
            print("begin shutdown...")
            self.shutDownState = ShutDownState.shutdown
            await self.shutdown()


    @waitBeforeStartingTask
    @tasks.loop(**lib.timeUtil.td_secondsMinutesHours(cfg.timeouts.dataSaveFrequency))
    async def dbSaveTask(self):
        self.saveAllDBs()
        print(datetime.now().strftime("%H:%M:%S: Data saved!"))


    def dispatch(self, event_name, *args, **kwargs):
        if event_name == "ready" and not self.loggedIn:
            asyncio.create_task(self._asyncInit(True, *args, **kwargs))
        else:
            return super().dispatch(event_name, *args, **kwargs)

    
    async def _asyncInit(self, dispatchReady: bool = True, *args, **kwargs):
        if not self._mediaServersLoaded:
            mediaServer = self.get_guild(cfg.mediaServer)
            if mediaServer is None:
                raise ValueError(f"Unknown guild ID for cfg.mediaServer: {cfg.mediaServer}")

            skinsChannel = mediaServer.get_channel(cfg.skinRendersChannel)
            if skinsChannel is None:
                raise ValueError(f"Unknown channel ID for cfg.skinRendersChannel: {cfg.skinRendersChannel}")
            if not isinstance(skinsChannel, TextChannel):
                raise ValueError(f"Channel is not a TextChannel for cfg.skinRendersChannel: {cfg.skinRendersChannel}")
            self._skinStorageChannel = skinsChannel

            rendersChannel = mediaServer.get_channel(cfg.showmeSkinRendersChannel)
            if rendersChannel is None:
                raise ValueError(f"Unknown channel ID for cfg.showmeSkinRendersChannel: {cfg.showmeSkinRendersChannel}")
            if not isinstance(rendersChannel, TextChannel):
                raise ValueError(f"Channel is not a TextChannel for cfg.showmeSkinRendersChannel: {cfg.showmeSkinRendersChannel}")
            self._skinRendersChannel = rendersChannel

            routesChannel = mediaServer.get_channel(cfg.bbcRouteImageChannel)
            if routesChannel is None:
                raise ValueError(f"Unknown channel ID for cfg.bbcRouteImageChannel: {cfg.bbcRouteImageChannel}")
            if not isinstance(routesChannel, TextChannel):
                raise ValueError(f"Channel is not a TextChannel for cfg.bbcRouteImageChannel: {cfg.bbcRouteImageChannel}")
            self._bountyRouteImagesChannel = routesChannel

            self._mediaServersLoaded = True

        # TODO: Need to refactor this to not attempt initializing github 
        # if the cogs are not included in the bot launch config
        if not self._githubLoaded and cfg.githubAccessToken != "":
            self._githubClient = lib.github.BasedGithub(cfg.githubAccessToken)
            self._githubRepo = self._githubClient.get_repo(cfg.githubIssuesRepo)
            self._githubLoaded = True

        # Create missing directories
        cfg.paths.createMissingDirectories()

        gameConfigurator.loadAllGameObjectData()
        gameConfigurator.loadAllGameObjects()

        if not self._schedulerLoaded:
            self._taskScheduler = timedTaskHeap.AutoCheckingTimedTaskHeap(asyncio.get_running_loop())
            self._taskScheduler.startTaskChecking()
            self._schedulerLoaded = True

        if not self.shutdownCheckTask.is_running():
            self.shutdownCheckTask.start()

        # Convert all UninitializedBasedEmojis in config to BasedEmoji
        cfg.defaultEmojis.initializeEmojis()

        self.loggedIn = True

        await self.reloadDBs()

        if dispatchReady:
            self.dispatch("ready", *args, **kwargs)


    def getStaticComponentCallbackMeta(self, ID: "basedComponent.StaticComponents") -> "basedComponent.StaticComponentCallbackMeta":
        """Look up a registered static component callback by ID

        :param ID: The ID of the component in the `StaticComponents` enum
        :type ID: basedComponent.StaticComponents
        :return: The metadata recorded about the callback that is registered with id `ID`
        :rtype: basedComponent.StaticComponentCallbackMeta
        """
        return self.staticComponentCallbacks[ID]


    def getStaticComponentCallback(self, ID: "basedComponent.StaticComponents") -> "basedComponent.StaticComponentCallbackType":
        """Look up a registered static component callback by ID

        :param ID: The ID of the component in the `StaticComponents` enum
        :type ID: basedComponent.StaticComponents
        :return: The callback that is registered with id `ID`. This may or may not belong to a Cog
        :rtype: basedComponent.StaticComponentCallbackType
        """
        return self.getStaticComponentCallbackMeta(ID).callback


    def hasStaticComponent(self, ID: "basedComponent.StaticComponents") -> bool:
        """Decide whether the client has a static component callback registered, whether in a loaded Cog or not.
        Does not consider unloaded Cogs

        :param ID: The ID of the component in the `StaticComponents` enum
        :type ID: basedComponent.StaticComponents
        :return: `True` if a static component is registered with id `ID`, `False` otherwise
        :rtype: bool
        """
        return ID in self.staticComponentCallbacks


    def tryFetchUser(self, id: int) -> Coroutine[Any, Any, Optional[User]]:
        """Try to execute self.fetch_user. If the user is not found, return None.
        This returns a coroutine that must be awaited.

        :param id: The id of the user to look up
        :type id: int
        :return: The user if one is found, or None
        :rtype: Optional[User]
        """
        try:
            return self.fetch_user(id)
        except NotFound:
            return lib.discordUtil.dummyCoroutine(None)


    async def multiWaitFor(self, eventTypes: Union[List[str], Tuple[str]], timeout: float, check: Optional[Callable[..., bool]] = None) -> Any:
        done, pending = await asyncio.wait(
            [asyncio.create_task(self.wait_for(eventType, check=check)) for eventType in eventTypes],
            return_when=asyncio.FIRST_COMPLETED,
            timeout=timeout
        )

        if timedout := not done:
            stuff = None
        else:
            stuff = done.pop().result()

        for future in done:
            # If any exception happened in any other done tasks
            # we don't care about the exception, but don't want the noise of
            # non-retrieved exceptions
            future.exception()

        for future in pending:
            future.cancel()  # we don't need these anymore

        if timedout:
            raise asyncio.TimeoutError()
        
        return stuff


def ensureBasedClient(interaction: Interaction) -> BasedClient:
    if not isinstance(interaction.client, BasedClient):
        raise TypeError(f"This interaction is only supported when handled by a {BasedClient.__name__}")
    return interaction.client


def interactionBasedUser(interaction: Interaction) -> Optional["basedUser.BasedUser"]:
    client = ensureBasedClient(interaction)
    if client.usersDB.idExists(interaction.user.id):
        return client.usersDB.getUser(interaction.user.id)
    return None


def onboardInteractionBasedUser(interaction: Interaction) -> "basedUser.BasedUser":
    client = ensureBasedClient(interaction)
    return client.usersDB.getOrAddID(interaction.user.id)
