from .. import client
from discord import app_commands, Interaction
from discord.ext import commands
from ..cfg import cfg
from ..cfg.cfg import basicAccessLevels
from time import perf_counter
from ..interactions import basedCommand, basedApp
from typing import List, cast
from discord.abc import Snowflake


class AdminMiscCog(basedApp.BasedCog):
    def __init__(self, bot: client.BasedClient, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.serverAdmin)
    @app_commands.command(name="ping",
                            description="Measure the latency between the bot sending a message, and receiving a response from discord.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def admin_cmd_ping(self, interaction: Interaction):
        """admin command testing bot latency.

        :param discord.Message message: the discord message calling the command
        :param str args: ignored
        :param bool isDM: Whether or not the command is being called from a DM channel
        """
        start = perf_counter()
        await interaction.response.send_message("Ping...")
        end = perf_counter()
        duration = (end - start) * 1000
        msg = await interaction.original_message()
        await msg.edit(content='Pong! {:.2f}ms'.format(duration))


async def setup(bot: client.BasedClient):
    # Casting here because for some reason pyright doesn't think SerializableDiscordObject is a Snowflake,
    # even though it extends discord.Object
    await bot.add_cog(AdminMiscCog(bot), guilds=cast(List[Snowflake], cfg.developmentGuilds))
