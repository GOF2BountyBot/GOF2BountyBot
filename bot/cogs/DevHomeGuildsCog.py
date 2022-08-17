from typing import List, cast
from .. import client, lib
from discord import app_commands, Interaction, Embed
from discord.abc import GuildChannel, Snowflake
from discord.utils import utcnow
from ..cfg import cfg
from ..cfg.cfg import basicAccessLevels
from ..interactions import basedCommand
from ..interactions.basedApp import BasedCog
from ..databases.bountyDB import nameForDivision
from typing import List, cast


class DevHomeGuildsCog(BasedCog):
    def __init__(self, bot: client.BasedClient, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)

#region commands

    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer)
    @app_commands.command(name="reset-transfer-cooldown",
                            description="Reset the requested user's cmd_transfer cooldown")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_reset_transfer_cooldown(self, interaction: Interaction, user_id: str = ""):
        """Reset the requested user's cmd_transfer cooldown.
        """
        requestedUser, _ = await self.UsersUtilCog.getBasedUserOrAuthor(interaction, user_id)
        if requestedUser is None: return

        now = utcnow()
        if requestedUser.canTransferGuild(now=now):
            await interaction.response.send_message(":x: User not on transfer cooldown!", ephemeral=True)
        else:
            requestedUser.guildTransferCooldownEnd = now
            await interaction.response.send_message("✅ Done!", ephemeral=True)

#endregion

async def setup(bot: client.BasedClient):
    # Casting here because for some reason pyright doesn't think SerializableDiscordObject is a Snowflake,
    # even though it extends discord.Object
    await bot.add_cog(DevHomeGuildsCog(bot), guilds=cast(List[Snowflake], cfg.developmentGuilds))
