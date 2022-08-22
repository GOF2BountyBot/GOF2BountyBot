from typing import List, cast

from discord import app_commands, Interaction
from discord.abc import Snowflake
from discord.app_commands import Range

from .. import client
from ..cfg import cfg
from ..cfg.cfg import basicAccessLevels
from ..interactions import basedCommand
from ..interactions.basedApp import BasedCog


class DevEconomyCog(BasedCog):
    def __init__(self, bot: client.BasedClient, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="economy")
    @app_commands.command(name="set-balance",
                            description="Set a user's credits balance")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_setbalance(self, interaction: Interaction, balance: Range[int, 1, ...], user_id: str = ""):
        """developer command setting the requested user's balance.
        """
        requestedBUser, _, _, _ = await self.UsersUtilCog.getOrCreateBasedUserOrAuthor(interaction, user_id)
        if requestedBUser is None: return

        # update the balance
        requestedBUser.credits = balance
        await interaction.response.send_message("Done!", ephemeral=True)


async def setup(bot: client.BasedClient):
    # Casting here because for some reason pyright doesn't think SerializableDiscordObject is a Snowflake,
    # even though it extends discord.Object
    await bot.add_cog(DevEconomyCog(bot), guilds=cast(List[Snowflake], cfg.developmentGuilds))
