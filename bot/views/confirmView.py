from typing import Optional
from discord.ui import button, Button
from discord import ButtonStyle, Interaction
from bot.views.cancelView import CancelView
from bot.views.viewBase import ViewCleanup

class ConfirmView(CancelView):
    """`Accept` or `Cancel` buttons.
    """
    def __init__(self, *, timeout: Optional[float] = 180, cleanup: Optional[ViewCleanup] = None, respondOnCleanup: bool = False, confirmLabel: str = "Confirm", cancelLabel: str = "Cancel", confirmRow: int = 1, cancelRow: int = 1, awaitCleanup: bool = True):
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
        super().__init__(timeout=timeout, cleanup=cleanup, respondOnCleanup=respondOnCleanup, cancelLabel=cancelLabel, cancelRow=cancelRow, awaitCleanup=awaitCleanup)
        self.confirm.label = confirmLabel
        self.confirm.row = confirmRow


    @property
    def confirmed(self):
        """If the `confirm` button was selected.
        This is `False` if the `cancel` button was selected.
        Raises `ValueError` if the menu timed out.
        """
        return not self.cancelled


    @button(style=ButtonStyle.green, label="confirm")
    async def confirm(self, interaction: Interaction, _: Button):
        """Confirm button"""
        self._cancelled = False
        await self.endView(interaction)
