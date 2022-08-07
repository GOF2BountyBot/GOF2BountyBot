from enum import Enum
from inspect import iscoroutinefunction
from typing import Any, Awaitable, Callable, Coroutine, Dict, Iterable, List, Optional, Tuple, Type, TypeVar, TYPE_CHECKING, Union, cast

from discord.ext.commands.cog import Cog
from discord import app_commands, Interaction, Component

from . import basedCommand, basedComponent
from .. import client, lib

if TYPE_CHECKING:
    from .basedCommand import CallBackType, TClass, TParams
    from ..cogs.util import EmbedEditorCog, CommonStaticComponentsCog, GuildsUtilCog, UsersUtilCog

TAnyCallback = Callable[..., Awaitable[Any]]

class DelayedPropogationFlag: pass

COG_INSTANCE = DelayedPropogationFlag()

class BasedAppType(Enum):
    """Identifies a callback as a particular type of BASED app.
    """
    none = 0
    AppCommand = 1
    StaticComponent = 2


def appType(callback: TAnyCallback) -> BasedAppType:
    """Decide the BASED app type for a callback, if any

    :param callback: The callback to examine
    :type callback: TAnyCallback
    :return: The BASED app type for `callback`
    :rtype: BasedAppType
    """
    try:
        return callback.__based_app_type__
    except AttributeError:
        return BasedAppType.none


def _ensureAppType(callback: TAnyCallback, basedAppType: BasedAppType):
    """Raise an exception of `callback` is a BASED app type other than `basedAppType` or `none`.

    :param callback: The callback to examine
    :type callback: TAnyCallback
    :param basedAppType: The basedAppType to allow `callback` to be
    :type basedAppType: BasedAppType
    :raises ValueError: If `callback` is any BASED app type other than `basedAppType` or `none`
    """
    callbackType = appType(callback)
    if callbackType not in (basedAppType, BasedAppType.none):
        raise ValueError(f"callback {callback.__name__} is already based app type {callbackType}")


def basedApp(callback: TAnyCallback, basedAppType: BasedAppType):
    """Mark a callback as a BASED app. This does not add the behaviour of the BASED app, it only
    marks the callback as of that type.

    :param callback: The callback to mark
    :type callback: TAnyCallback
    :param basedAppType: The BASED app type to mark `callback` as
    :type basedAppType: BasedAppType
    """
    _ensureAppType(callback, basedAppType)
    setattr(callback, "__based_app_type__", basedAppType)


def isBasedApp(callback: Callable) -> bool:
    """Decide whether `callback` has been marked as a BASED app

    :param callback: The callback
    :type callback: Callable
    :return: `True` if `callback` is a BASED app, `False` otherwise
    :rtype: bool
    """
    return appType(callback) != BasedAppType.none


def isCogApp(callback: Callable) -> bool:
    """Decide whether `callback` is a BASED app created within a `BasedCog`.

    :param callback: The callback
    :type callback: Callable
    :return: `True` if `callback` is a BASED app created within a `BasedCog`, `False` otherwise
    :rtype: bool
    """
    return "__cog_name__" in callback.__dict__ and callback.__dict__["__cog_name__"] is not None


def setCogApp(callback: Callable, cog: Type["BasedCog"]):
    """Mark a BASED app as belonging to a cog

    :param callback: The callback
    :type callback: Callable
    :param cog: The cog type to mark the callback as belonging to
    :type cog: Type[&quot;BasedCog&quot;]
    """
    callback.__dict__["__cog_name__"] = cog.__name__
    # setattr(callback, "__cog_name__", cog.__name__)


def setNotCogApp(callback: Callable):
    """Remove a BASED app's assignment to a cog

    :param callback: The callback
    :type callback: Callable
    """
    callback.__dict__["__cog_name__"] = None
    # setattr(callback, "__cog_name__", None)


def getCogAppCogName(callback: Callable) -> str:
    """Get the name of the cog that a BASED app has been assigned to

    :param callback: The callback
    :type callback: Callable
    :raises ValueError: If `callback` is not a BASED app created within a `BasedCog`
    :return: The name of the cog that defined `callback`
    :rtype: str
    """
    if not isCogApp(callback):
        raise ValueError(f"The callback {callback.__name__} is not a cog app")
    # return callback.__cog_name__
    return callback.__dict__["__cog_name__"]

TStaticComponentCallback = TypeVar("TStaticComponentCallback", bound="basedComponent.StaticComponentCallbackType")

class BasedCog(Cog):
    """An extension of `Cog` to allow for housing of BASED apps.
    This current includes BASED commands and static component callbacks.

    :var basedCommands: All BASED commands defined within the cog
    :type basedCommands: Dict[app_commands.Command, basedCommand.BasedCommandMeta]
    :var staticComponentCallbacks: All static component callbacks defined within the cog, by ID
    :type staticComponentCallbacks: Dict[basedComponent.StaticComponents, basedComponent.StaticComponentCallbackMeta]
    """
    def __init__(self, bot: client.BasedClient, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)
        self._basedCommands: Optional[Dict[app_commands.Command, "basedCommand.BasedCommandMeta"]] = None
        self._staticComponentCallbacks: Optional[Dict["basedComponent.StaticComponents", "basedComponent.StaticComponentCallbackMeta"]] = None


    @property
    def basedCommands(self):
        if self._basedCommands is None:
            raise ValueError("basedCommands is only available after cog injection")
        return self._basedCommands


    @property
    def staticComponentCallbacks(self):
        if self._staticComponentCallbacks is None:
            raise ValueError("staticComponentCallbacks is only available after cog injection")
        return self._staticComponentCallbacks


    async def cog_load(self) -> None:
        """Registers all BASED apps, e.g static components callbacks, based commands, etc.
        """
        self._basedCommands = {}
        self._staticComponentCallbacks = {}
        for command in self.walk_commands():
            if isinstance(command, app_commands.Command) and appType(command.callback) == BasedAppType.AppCommand:
                self.basedCommands[command] = basedCommand.commandMeta(command)
                setCogApp(command.callback, type(self))
                self.bot.addBasedCommand(command)
        
        for methodName in dir(self):
            method = getattr(self, methodName)
            if appType(method) == BasedAppType.StaticComponent:
                meta = basedComponent.staticComponentCallbackMeta(method)
                self.staticComponentCallbacks[meta.ID] = meta
                setCogApp(method, type(self))
                self.bot.addStaticComponent(meta.callback)

        return await super().cog_load()

    
    async def cog_unload(self) -> None:
        """Unregisters all BASED apps in the cog from the provided client
        """
        """Un-registers all BASED apps, e.g static components callbacks, based commands, etc.
        """
        for command in self.basedCommands:
            self.bot.removeBasedCommand(command)

        for meta in self.staticComponentCallbacks.values():
            self.bot.removeStaticComponent(meta.ID)
            
        self._basedCommands = None
        self._staticComponentCallbacks = None

        return await super().cog_unload()


    @classmethod
    def staticComponentCallback(cls, ID: "basedComponent.StaticComponents"):
        """Decorator marking a coroutine as a static component callback.
        The callback for static components identifying this callback by ID will be preserved across bot restarts

        Example usage:
        ```
        class MyCog(BasedCog):
            @BasedCog.staticComponentCallback(StaticComponents.myCallback)
            async def myCallback(self, interaction: Interaction, args: str):
                await interaction.response.send_message(f"This static callback received args: {args}")

            @app_commands.command(name="send-static-menu")
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
        def decorator(func: TStaticComponentCallback, ID=ID) -> TStaticComponentCallback:
            if not iscoroutinefunction(func):
                raise TypeError("Decorator can only be applied to coroutines")

            # This special variation on the staticComponentCallback decorator delays setting of the 'cbSelf' meta field
            #   until cog instantiation. This usually would be a bad idea, because every class instance would try to
            #   register their static components against the client, causing a conflict. This issue is not present
            #   with Cogs, because they are effectively singular, meaning that this delayed propogation will only
            #   occur once per class
            if hasattr(func, "__self__"):
                cbSelf = basedComponent.validateStaticComponentCallbackSelf(func)
            else:
                cbSelf = COG_INSTANCE

            basedApp(func, BasedAppType.StaticComponent)
            setattr(func, "__static_component_meta__", basedComponent.StaticComponentCallbackMeta(func, ID, cbSelf))

            return func

        return decorator

    
    def tryGetCog(self, cogName: str, callingFuncName: Optional[str] = None) -> Optional[Cog]:
        foundCog = self.bot.get_cog(cogName)
        if foundCog is None:
            self.bot.logger.log("DevMiscCog", callingFuncName or "tryGetCog", f"Unable to find cog on self.bot: {cogName}", eventType="COG_NOT_FOUND")
        return foundCog


    def getEmbedEditorCog(self, callingFuncName: Optional[str] = None) -> Optional["EmbedEditorCog.EmbedEditorCog"]:
        """Get the loaded instance of the shared 'EmbedEditorCog' cog.

        :param callingFuncName: The name of the calling function, for logging purposes (Default None)
        """
        return cast(Optional["EmbedEditorCog.EmbedEditorCog"], self.tryGetCog("EmbedEditorCog", callingFuncName=callingFuncName))


    @property
    def EmbedEditorCog(self) -> "EmbedEditorCog.EmbedEditorCog":
        """Get the loaded instance of the shared 'EmbedEditorCog' cog.

        :param callingFuncName: The name of the calling function, for logging purposes (Default None)
        :raises SharedCogNotLoaded: If the cog is not loaded.
        """
        c = self.getEmbedEditorCog()
        if c is None:
            raise lib.exceptions.SharedCogNotLoaded("EmbedEditorCog")
        return cast("EmbedEditorCog.EmbedEditorCog", c)


    def getCommonStaticComponentsCog(self, callingFuncName: Optional[str] = None) -> Optional["CommonStaticComponentsCog.CommonStaticComponentsCog"]:
        """Get the loaded instance of the shared 'CommonStaticComponentsCog' cog.

        :param callingFuncName: The name of the calling function, for logging purposes (Default None)
        """
        return cast(Optional["CommonStaticComponentsCog.CommonStaticComponentsCog"], self.tryGetCog("CommonStaticComponentsCog", callingFuncName=callingFuncName))


    @property
    def CommonStaticComponentsCog(self) -> "CommonStaticComponentsCog.CommonStaticComponentsCog":
        """Get the loaded instance of the shared 'CommonStaticComponentsCog' cog.

        :param callingFuncName: The name of the calling function, for logging purposes (Default None)
        :raises SharedCogNotLoaded: If the cog is not loaded.
        """
        c = self.getCommonStaticComponentsCog()
        if c is None:
            raise lib.exceptions.SharedCogNotLoaded("CommonStaticComponentsCog")
        return cast("CommonStaticComponentsCog.CommonStaticComponentsCog", c)

    
    def getGuildsUtilCog(self, callingFuncName: Optional[str] = None) -> Optional["GuildsUtilCog.GuildsUtilCog"]:
        """Get the loaded instance of the shared 'GuildsUtilCog' cog.

        :param callingFuncName: The name of the calling function, for logging purposes (Default None)
        """
        return cast(Optional["GuildsUtilCog.GuildsUtilCog"], self.tryGetCog("GuildsUtilCog", callingFuncName=callingFuncName))


    @property
    def GuildsUtilCog(self) -> "GuildsUtilCog.GuildsUtilCog":
        """Get the loaded instance of the shared 'GuildsUtilCog' cog.

        :param callingFuncName: The name of the calling function, for logging purposes (Default None)
        :raises SharedCogNotLoaded: If the cog is not loaded.
        """
        c = self.getGuildsUtilCog()
        if c is None:
            raise lib.exceptions.SharedCogNotLoaded("GuildsUtilCog")
        return cast("GuildsUtilCog.GuildsUtilCog", c)


    def getUsersUtilCog(self, callingFuncName: Optional[str] = None) -> Optional["UsersUtilCog.UsersUtilCog"]:
        """Get the loaded instance of the shared 'UsersUtilCog' cog.

        :param callingFuncName: The name of the calling function, for logging purposes (Default None)
        """
        return cast(Optional["UsersUtilCog.UsersUtilCog"], self.tryGetCog("UsersUtilCog", callingFuncName=callingFuncName))


    @property
    def UsersUtilCog(self) -> "UsersUtilCog.UsersUtilCog":
        """Get the loaded instance of the shared 'UsersUtilCog' cog.

        :param callingFuncName: The name of the calling function, for logging purposes (Default None)
        :raises SharedCogNotLoaded: If the cog is not loaded.
        """
        c = self.getUsersUtilCog()
        if c is None:
            raise lib.exceptions.SharedCogNotLoaded("UsersUtilCog")
        return cast("UsersUtilCog.UsersUtilCog", c)
