from discord import app_commands, Interaction
from discord.app_commands import Range

from .. import client
from ..cfg.cfg import basicAccessLevels
from ..interactions import basedCommand
from ..interactions.basedApp import BasedCog
from .util.CommonAutocomplete import shipAutoComplete


class UserAutoskinCog(BasedCog):
    @shipAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="Autoskin")
    @app_commands.command(name="autoskin-render",
                            description="Generate a ship skin, and render it.")
    async def usr_cmd_autoskin(self, interaction: Interaction, ship: str):
        """developer command setting the requested user's balance.
        """
        requestedBUser, _, _, _ = await self.UsersUtilCog.getOrCreateBasedUserOrAuthor(interaction, user_id)
        if requestedBUser is None: return

        # update the balance
        requestedBUser.credits = balance
        await interaction.response.send_message("Done!", ephemeral=True)


async def setup(bot: client.BasedClient):
    await bot.add_cog(UserAutoskinCog(bot))
