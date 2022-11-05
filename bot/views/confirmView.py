
from typing import Callable, Coroutine, Optional, cast
from discord.ui import View, button, Button, Item
from discord import ButtonStyle, Interaction

class ConfirmView(View):
    """`Accept` or `Cancel` buttons.
    """
    def __init__(self, *, timeout: Optional[float] = 180, clearView: bool = True, respond: bool = True, confirmLabel: str = "Confirm", cancelLabel: str = "Cancel", confirmRow: int = 1, cancelRow: int = 1):
        """
        :param timeout: The menu timeout in seconds, defaults to 180
        :type timeout: Optional[float]
        :param clearView: When the interaction is responded to, clear the view from the menu, defaults to True
        :type clearView: bool, defaults to True
        :param respond: If clearView is True, clear the view as the interction response, defaults to True
        :type respond: bool, defaults to True
        """
        super().__init__(timeout=timeout)
        self._confirmed = None
        self._interaction = None
        self._timedOut = None
        self._clearView = clearView
        self._respond = respond
        self.confirm.label = confirmLabel
        self.confirm.row = confirmRow
        self.cancel.label = cancelLabel
        self.cancel.row = cancelRow


    @property
    def done(self):
        """Whether or not the menu has completed.
        This is `True` if the menu has been reponded to or has timed out, and is `False` otherwise.
        """
        return self._timedOut is not None


    @property
    def confirmed(self):
        """If the `confirm` button was selected.
        This is `False` if the `cancel` button was selected.
        Raises `ValueError` if the menu timed out.
        """
        if not self.done:
            raise RuntimeError("This menu is still active")
        if self.timedOut:
            raise ValueError("This menu has timed out")
        return cast(bool, self._confirmed)


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


    async def _end(self, interaction: Interaction):
        self._interaction = interaction
        self._timedOut = False
        if self._clearView:
            if self._respond:
                await interaction.response.edit_message(view=None)
            else:
                await interaction.edit_original_response(view=None)
        self.stop()


    async def on_timeout(self) -> None:
        """Sets the menu's `timedOut` tracker. Do not override.
        """
        self._timedOut = True


    @button(style=ButtonStyle.green, label="confirm")
    async def confirm(self, interaction: Interaction, _: Button):
        """Confirm button"""
        self._confirmed = True
        await self._end(interaction)


    @button(style=ButtonStyle.red, label="cancel")
    async def cancel(self, interaction: Interaction, _: Button):
        """Cancel button"""
        self._confirmed = False
        await self._end(interaction)
