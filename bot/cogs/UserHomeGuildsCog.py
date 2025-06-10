from typing import cast
from discord import Guild, app_commands, Interaction

from bot import client
from bot.lib.timeUtil import td_format_noYM
from bot.lib.discordUtil import timestamp, TimeStampStyle
from bot.cfg import cfg
from bot.cfg.cfg import basicAccessLevels
from bot.interactions import basedCommand
from bot.interactions.basedApp import BasedCog
from bot.views.confirmView import ConfirmView


class UserHomeGuildsCog(BasedCog):
    @app_commands.guild_only
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="home servers",
                            formattedDesc="To improve balance and to prevent unfair farming/botting, BountyBot " \
                                        + "commands marked with the 🌎 icon can only be used from a single server, " \
                                        + "called your 'home server'.\nUse this command to move your home " \
                                        + "server, so that you can play there instead. Use `/home-server` to " \
                                        + "find your current home server.\n\n" \
                                        + "*If you don't have a home server, using a home server-only " \
                                        + "command will set your home server automatically.*")
    @app_commands.command(name="set-home-server",
                            description="Set this server as your home server. This command has a long cooldown!")
    async def cmd_transfer(self, interaction: Interaction):
        """Transfer the calling user's home guild to the guild where the command was sent.
        """
        user = self.bot.usersDB.getOrAddID(interaction.user.id)
        # Casting here because this command is decorated with @guild_only
        guild = cast(Guild, interaction.guild)
        if user.hasHomeGuild() and guild.id == user.homeGuildID:
            await interaction.response.send_message(":x: This is already your home server!", ephemeral=True)
        elif not user.canTransferGuild():
            await interaction.response.send_message(f":x: This command is still on cooldown. (ends {timestamp(user.guildTransferCooldownEnd, TimeStampStyle.LongDateTime)})", ephemeral=True)
        else:
            view = ConfirmView(timeout=cfg.timeouts.homeGuildTransferCooldown.total_seconds())
            await interaction.response.send_message(f"Move your home server to '{guild.name}'?\n" \
                                                    + f"This command has a cooldown of **{td_format_noYM(cfg.timeouts.homeGuildTransferCooldown)}**.",
                                                    view=view)
            
            view.disableAll()
            if await view.wait():
                await view.interaction.response.edit_message(content="🛑 Out of time! Please try this command again.", view=view)
                return

            if view.cancelled:
                await view.interaction.response.edit_message(content="🛑 Transfer cancelled.", view=view)
                return

            await user.transferGuild(guild)
            await view.interaction.response.edit_message(content=f":airplane_arriving: You transferred your home server to **{guild.name}**!", view=view)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="home servers",
                            formattedDesc="To improve balance and to prevent unfair farming/botting, BountyBot " \
                                        + "commands marked with the 🌎 icon can only be used from a single server, " \
                                        + "called your 'home server'.\nUse this command to find out what your " \
                                        + "home server is currently. Use `/set-home-server` to change your home server.\n\n" \
                                        + "*If you don't have a home server, using a home server-only " \
                                        + "command will set your home server automatically.*")
    @app_commands.command(name="home-server",
                            description="Find your current home server.")
    async def cmd_home(self, interaction: Interaction):
        """Display the name of the calling user's home guild, if they have one.
        """
        if self.bot.usersDB.idExists(interaction.user.id):
            user = self.bot.usersDB.getUser(interaction.user.id)
            if interaction.guild is not None and interaction.guild.id == user.homeGuildID:
                await interaction.response.send_message("🌍 This is your home server.", ephemeral=True)
                return
            elif user.hasHomeGuild():
                home = self.bot.get_guild(user.homeGuildID)
                if home is not None:
                    await interaction.response.send_message(f"🪐 Your home server is currently **{home.name}**.", ephemeral=True)
                    return
                
                await interaction.response.send_message("🌑 I can't find your home server - I may have been removed from it.\n" \
                                                        + "Set your home server with the `/set-home-server` command.",
                                                ephemeral=True)

        await interaction.response.send_message("🌑 Your home server has not yet been set.\nSet your home server by " \
                                                + "using a home server-only comand, or with the `/set-home-server` command.",
                                                ephemeral=True)


async def setup(bot: client.BasedClient):
    await bot.add_cog(UserHomeGuildsCog(bot))
