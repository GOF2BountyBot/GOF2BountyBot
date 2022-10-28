from enum import Enum
from inspect import iscoroutinefunction, signature
from typing import Any, Awaitable, Callable, Dict, Generic, Optional, Protocol, Set, Type, TypeVar, TYPE_CHECKING, Union, cast
from functools import wraps

from discord.ext.commands.cog import Cog
from discord import app_commands

from . import basedCommand, basedComponent
from .. import client, lib

if TYPE_CHECKING:
    from ..cogs.util import EmbedEditorCog, CommonStaticComponentsCog, GuildsUtilCog, UsersUtilCog, GithubUtilCog

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

_basedAppIgnored: Set[str] = set()
_TIgnoredMethod = TypeVar("_TIgnoredMethod", bound=Callable)

def _basedAppIgnore(method: _TIgnoredMethod) -> _TIgnoredMethod:
    _basedAppIgnored.add(method.__name__)
    return method

def _isIgnored(methodName: str) -> bool:
    return methodName in _basedAppIgnored

TStaticComponentCallback = TypeVar("TStaticComponentCallback", bound="basedComponent.StaticComponentCallbackType")

class BasedCog(Cog):
    """An extension of `Cog` to allow for housing of BASED apps.
    This current includes BASED commands and static component callbacks.

    :var basedCommands: All BASED commands defined within the cog
    :type basedCommands: Dict[app_commands.Command, basedCommand.BasedCommandMeta]
    :var staticComponentCallbacks: All static component callbacks defined within the cog, by ID
    :type staticComponentCallbacks: Dict[basedComponent.StaticComponents, basedComponent.StaticComponentCallbackMeta]
    """
    @_basedAppIgnore
    def __init__(self, bot: "client.BasedClient", *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)
        self._basedCommands: Optional[Dict[app_commands.Command, "basedCommand.BasedCommandMeta"]] = None
        self._staticComponentCallbacks: Optional[Dict["basedComponent.StaticComponents", "basedComponent.StaticComponentCallbackMeta"]] = None

    @property
    @_basedAppIgnore
    def basedCommands(self):
        if self._basedCommands is None:
            raise ValueError("basedCommands is only available after cog injection")
        return self._basedCommands

    @property
    @_basedAppIgnore
    def staticComponentCallbacks(self):
        if self._staticComponentCallbacks is None:
            raise ValueError("staticComponentCallbacks is only available after cog injection")
        return self._staticComponentCallbacks

    @_basedAppIgnore
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
        
        for methodName in [n for n in dir(self) \
                            if not _isIgnored(n) and \
                                (not hasattr(type(self), n) or not isinstance(getattr(type(self), n), property))]:
            method = getattr(self, methodName)
            if appType(method) == BasedAppType.StaticComponent:
                meta = basedComponent.staticComponentCallbackMeta(method)
                self.staticComponentCallbacks[meta.ID] = meta
                setCogApp(method, type(self))
                self.bot.addStaticComponent(meta.callback)

        return await super().cog_load()

    @_basedAppIgnore
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
    @_basedAppIgnore
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

            return cast(TStaticComponentCallback, func)

        return decorator

    @_basedAppIgnore
    def tryGetCog(self, cogName: str, callingFuncName: Optional[str] = None) -> Optional[Cog]:
        foundCog = self.bot.get_cog(cogName)
        if foundCog is None:
            self.bot.logger.log("DevMiscCog", callingFuncName or "tryGetCog", f"Unable to find cog on self.bot: {cogName}", eventType="COG_NOT_FOUND")
        return foundCog

    @_basedAppIgnore
    def getEmbedEditorCog(self, callingFuncName: Optional[str] = None) -> Optional["EmbedEditorCog.EmbedEditorCog"]:
        """Get the loaded instance of the shared 'EmbedEditorCog' cog.

        :param callingFuncName: The name of the calling function, for logging purposes (Default None)
        """
        return cast(Optional["EmbedEditorCog.EmbedEditorCog"], self.tryGetCog("EmbedEditorCog", callingFuncName=callingFuncName))

    @property
    @_basedAppIgnore
    def EmbedEditorCog(self) -> "EmbedEditorCog.EmbedEditorCog":
        """Get the loaded instance of the shared 'EmbedEditorCog' cog.

        :param callingFuncName: The name of the calling function, for logging purposes (Default None)
        :raises SharedCogNotLoaded: If the cog is not loaded.
        """
        c = self.getEmbedEditorCog()
        if c is None:
            raise lib.exceptions.SharedCogNotLoaded("EmbedEditorCog")
        return cast("EmbedEditorCog.EmbedEditorCog", c)

    @_basedAppIgnore
    def getCommonStaticComponentsCog(self, callingFuncName: Optional[str] = None) -> Optional["CommonStaticComponentsCog.CommonStaticComponentsCog"]:
        """Get the loaded instance of the shared 'CommonStaticComponentsCog' cog.

        :param callingFuncName: The name of the calling function, for logging purposes (Default None)
        """
        return cast(Optional["CommonStaticComponentsCog.CommonStaticComponentsCog"], self.tryGetCog("CommonStaticComponentsCog", callingFuncName=callingFuncName))

    @property
    @_basedAppIgnore
    def CommonStaticComponentsCog(self) -> "CommonStaticComponentsCog.CommonStaticComponentsCog":
        """Get the loaded instance of the shared 'CommonStaticComponentsCog' cog.

        :param callingFuncName: The name of the calling function, for logging purposes (Default None)
        :raises SharedCogNotLoaded: If the cog is not loaded.
        """
        c = self.getCommonStaticComponentsCog()
        if c is None:
            raise lib.exceptions.SharedCogNotLoaded("CommonStaticComponentsCog")
        return cast("CommonStaticComponentsCog.CommonStaticComponentsCog", c)

    @_basedAppIgnore
    def getGuildsUtilCog(self, callingFuncName: Optional[str] = None) -> Optional["GuildsUtilCog.GuildsUtilCog"]:
        """Get the loaded instance of the shared 'GuildsUtilCog' cog.

        :param callingFuncName: The name of the calling function, for logging purposes (Default None)
        """
        return cast(Optional["GuildsUtilCog.GuildsUtilCog"], self.tryGetCog("GuildsUtilCog", callingFuncName=callingFuncName))

    @property
    @_basedAppIgnore
    def GuildsUtilCog(self) -> "GuildsUtilCog.GuildsUtilCog":
        """Get the loaded instance of the shared 'GuildsUtilCog' cog.

        :param callingFuncName: The name of the calling function, for logging purposes (Default None)
        :raises SharedCogNotLoaded: If the cog is not loaded.
        """
        c = self.getGuildsUtilCog()
        if c is None:
            raise lib.exceptions.SharedCogNotLoaded("GuildsUtilCog")
        return cast("GuildsUtilCog.GuildsUtilCog", c)

    @_basedAppIgnore
    def getUsersUtilCog(self, callingFuncName: Optional[str] = None) -> Optional["UsersUtilCog.UsersUtilCog"]:
        """Get the loaded instance of the shared 'UsersUtilCog' cog.

        :param callingFuncName: The name of the calling function, for logging purposes (Default None)
        """
        return cast(Optional["UsersUtilCog.UsersUtilCog"], self.tryGetCog("UsersUtilCog", callingFuncName=callingFuncName))

    @property
    @_basedAppIgnore
    def UsersUtilCog(self) -> "UsersUtilCog.UsersUtilCog":
        """Get the loaded instance of the shared 'UsersUtilCog' cog.

        :param callingFuncName: The name of the calling function, for logging purposes (Default None)
        :raises SharedCogNotLoaded: If the cog is not loaded.
        """
        c = self.getUsersUtilCog()
        if c is None:
            raise lib.exceptions.SharedCogNotLoaded("UsersUtilCog")
        return cast("UsersUtilCog.UsersUtilCog", c)

    @property
    @_basedAppIgnore
    def GithubUtilCog(self) -> "GithubUtilCog.GithubUtilCog":
        """Get the loaded instance of the shared 'GithubUtilCog' cog.

        :param callingFuncName: The name of the calling function, for logging purposes (Default None)
        :raises SharedCogNotLoaded: If the cog is not loaded.
        """
        c = self.getGithubUtilCog()
        if c is None:
            raise lib.exceptions.SharedCogNotLoaded("GithubUtilCog")
        return cast("GithubUtilCog.GithubUtilCog", c)

    @_basedAppIgnore
    def getGithubUtilCog(self, callingFuncName: Optional[str] = None) -> Optional["GithubUtilCog.GithubUtilCog"]:
        """Get the loaded instance of the shared 'GithubUtilCog' cog.

        :param callingFuncName: The name of the calling function, for logging purposes (Default None)
        """
        return cast(Optional["GithubUtilCog.GithubUtilCog"], self.tryGetCog("GithubUtilCog", callingFuncName=callingFuncName))


TCog = TypeVar("TCog", bound=BasedCog, contravariant=True)
class _CogMethodNoArgs(Protocol, Generic[TCog]):
    __name__: str

    # Ignoring a warning here for the self name.
    # Since this is an instance method, it needs its own 'self' argument.
    def __call__(protocolSelf, self: TCog, **kwargs) -> Any: ... # type: ignore[reportSelfClsParameterName]


class _CogMethodNoKwargs(Protocol):
    __name__: str

    # Ignoring a warning here for the self name.
    # Since this is an instance method, it needs its own 'self' argument.
    def __call__(protocolSelf, self: TCog, *args) -> Any: ... # type: ignore[reportSelfClsParameterName]

class _CogMethodBothArgs(Protocol):
    __name__: str

    # Ignoring a warning here for the self name.
    # Since this is an instance method, it needs its own 'self' argument.
    def __call__(protocolSelf, self: TCog, *args, **kwargs) -> Any: ... # type: ignore[reportSelfClsParameterName]

TMethod = TypeVar("TMethod", bound=Union[_CogMethodBothArgs, _CogMethodNoArgs, _CogMethodNoKwargs])

def useCog(failCallback: Optional[Callable] = None, **paramCogNames: str):
    """Cog method decorator, requiring a cog instance for the method to execute.
    Give your cog names as kwargs to the decorator, e.g:

    ```
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from cogs.MyCogClass import MyCogClass

    class MyCog(BasedCog):
        def throwForMissingCog(self):
            raise RuntimeError("Couldn't find required cog")

        @useCog(myCog="MyCogClass", failCallback=throwForMissingCog)
        def myMethod(self, myCog: "MyCogClass")
            ...

        async def doNothingAsyncFailCallback(self):
            pass
        
        # Here I'm using doNothingAsyncFailCallback because otherwise None will be returned for `myAsyncMethod` on fail instead of a `Coroutine`.
        # If `None` is returned, then `await myAsyncMethod()` would not work!
        @useCog(myCog="MyCogClass", failCallback=doNothingAsyncFailCallback)
        async def myAsyncMethod(self, myCog: "MyCogClass"):
            ...
    ```

    It is recommended that you make your cog parameters optional, so that you needn't provide anything when calling the method.
    If some but not all of the cogs are found, then they will be present in the arguments for `failCallback`.

    :param failCallback: If the cog does not exist, then this function will be called instead, with the same arguments as the original method (including self)
    :param paramCogNames: Mapping of method parameter names to cog names.
    """
    if not paramCogNames:
        raise ValueError("At least one parameter must be specified. See the docs for this decorator for more information")

    def wrapper(func: TMethod) -> TMethod:
        sig = signature(func)
        for paramName in paramCogNames:
            if paramName not in sig.parameters:
                raise ValueError(f"function {func.__name__} does not have a parameter called {paramName}")

        # Clear this out from the closure, only needed for validation
        del sig

        @wraps(func)
        def run(self: BasedCog, *args, **kwargs):
            for paramName, cogName in paramCogNames.items():
                c = self.tryGetCog(cogName)
                if c is None:
                    if failCallback is not None:
                        return failCallback(self, *args, **kwargs)
                    return
                kwargs[paramName] = c
            return func(self, *args, **kwargs)

        return cast(TMethod, run)
    return wrapper
