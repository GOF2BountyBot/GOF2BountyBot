from typing import Optional, cast
from discord.ui import button, Button
from discord import ButtonStyle, Interaction

from bot.views.viewBase import ViewBase, ViewCleanup

class CancelView(ViewBase):
    """Just a `Cancel` button.
    """
    def __init__(self, *, timeout: Optional[float] = 180, cleanup: Optional[ViewCleanup] = None, respondOnCleanup: bool = False, cancelLabel: str = "Cancel", cancelRow: int = 1, awaitCleanup: bool = True):
        """
        :param timeout: The menu timeout in seconds, defaults to 180
        :type timeout: Optional[float]
        :param clearView: When the interaction is responded to, clear the view from the menu, defaults to False
        :type clearView: bool, defaults to False
        :param respond: If clearView is True, clear the view as the interction response, defaults to False
        :type respond: bool, defaults to False
        :param awaitCleanup: If cleanup is set, await the cleanup. Otherwise, schedule a task for it. defaults to True
        type awaitCleanup: bool, defaults to True
        """
        super().__init__(timeout=timeout, cleanup=cleanup, respondOnCleanup=respondOnCleanup, awaitCleanup=awaitCleanup)
        self._cancelled = None
        self.cancel.label = cancelLabel
        self.cancel.row = cancelRow


    @property
    def cancelled(self):
        """If the `cancel` button was selected.
        Raises `ValueError` if the menu timed out.
        """
        if not self.done:
            raise RuntimeError("This menu is still active")
        if self.timedOut:
            raise ValueError("This menu has timed out")
        return cast(bool, self._cancelled)


    @button(style=ButtonStyle.red, label="cancel")
    async def cancel(self, interaction: Interaction, _: Button):
        """Cancel button"""
        self._cancelled = True
        await self.endView(interaction)
