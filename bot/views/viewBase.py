from typing import Optional, cast, Protocol, runtime_checkable
from discord.ui import View, Modal
from discord import Enum, Interaction
import asyncio

@runtime_checkable
class Disableable(Protocol):
    disabled: bool


class ViewCleanup(Enum):
    clearView = 1
    disableAll = 2


class ViewBase(View):
    """Adds automatic clearing of the view after stopping, and tracking of the user's responding interaction,
    so that it can be responded to outside of the view
    """
    def __init__(self, *, timeout: Optional[float] = 180, cleanup: Optional[ViewCleanup] = None, respondOnCleanup: bool = False, awaitCleanup: bool = True, **kwargs):
        """
        :param timeout: The menu timeout in seconds, defaults to 180
        :type timeout: Optional[float]
        :param cleanup: Action to take when the view ends, e.g clear the view from the message, defaults to None
        :type clearView: Optional[ViewCleanup], defaults to None
        :param respondOnCleanup: If cleanup is set, perform cleanup as the interaction response, defaults to False
        :type respondOnCleanup: bool, defaults to False
        :param awaitCleanup: If cleanup is set, await the cleanup. Otherwise, schedule a task for it. defaults to True
        type awaitCleanup: bool, defaults to True
        """
        super().__init__(timeout=timeout, **kwargs)
        self._interaction = None
        self._timedOut = None
        self._cleanup = cleanup
        self._respondOnCleanup = respondOnCleanup
        self._awaitCleanup = awaitCleanup


    def disableAll(self):
        """Disables all children that can be disabled.
        This does not disable all child types.
        """
        for child in self.children:
            if isinstance(child, Disableable):
                child.disabled = True


    def enableAll(self):
        """Enables all children that can be disabled.
        This does not enable all child types.
        """
        for child in self.children:
            if isinstance(child, Disableable):
                child.disabled = False


    @property
    def done(self):
        """Whether or not the menu has completed.
        This is `True` if the menu has been reponded to or has timed out, and is `False` otherwise.
        """
        return self._timedOut is not None


    @property
    def interaction(self):
        """The interaction that responded to this menu.
        Raises `ValueError` if the menu timed out.
        """
        if not self.done:
            raise RuntimeError("This menu is still active")
        if self.timedOut:
            raise ValueError("This menu has timed out")
        return cast(Interaction, self._interaction)


    @property
    def timedOut(self):
        """Whether or not the menu timed out.
        """
        if not self.done:
            raise RuntimeError("This menu is still active")
        return cast(bool, self._timedOut)


    async def endView(self, interaction: Interaction):
        """Call this to stop the view from listening for interactions.
        This method will maintain the view's tracker variables (e.g the response interaction), and perform post-interaction view cleanup (if any)
        """
        self._interaction = interaction
        self._timedOut = False
        if self._cleanup is not None:
            if self._cleanup == ViewCleanup.clearView:
                _view = None
            elif self._cleanup == ViewCleanup.disableAll:
                _view = self
                self.disableAll()
            else:
                raise ValueError(f"Unsupported view cleanup method: {self._cleanup}")

            if self._respondOnCleanup:
                cleanupCoro = interaction.response.edit_message(view=_view)
            else:
                cleanupCoro = interaction.edit_original_response(view=_view)

            if self._awaitCleanup:
                await cleanupCoro
            else:
                asyncio.create_task(cleanupCoro)

        self.stop()


    async def on_timeout(self) -> None:
        """Sets the menu's `timedOut` tracker. Do not override.
        """
        self._timedOut = True


class ModalBase(ViewBase, Modal):
    def __init__(self, *, timeout: Optional[float] = 180, **kwargs):
        super().__init__(timeout=timeout, cleanup=None, **kwargs)
        

    async def on_submit(self, interaction: Interaction, /):
        """Do not override.
        This method will maintain the view's tracker variables (e.g the response interaction), and perform post-interaction view cleanup (if any)
        """
        await super().endView(interaction)
