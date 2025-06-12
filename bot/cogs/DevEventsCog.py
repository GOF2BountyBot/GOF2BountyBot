from datetime import timedelta
from typing import List, Optional, cast

from discord import app_commands, Interaction, Colour
from discord.abc import Snowflake, Messageable
from discord.utils import utcnow
from discord.app_commands import Range

from bot import client
from bot.cfg import cfg
from bot.cfg.cfg import basicAccessLevels
from bot.interactions import basedCommand
from bot.interactions.basedApp import BasedCog
from bot.gameObjects.items.tools import crateTool
from bot.cogs.util.transformers import PlayOrAnnounceChannel
from bot.users.basedGuild import BasedGuild
from bot.reactionMenus.giveawayMenu import GiveawayMenu


class DevEventsCog(BasedCog):
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="events",
                                formattedDesc="Start a giveaway of the christmas stocking for this year, for 48 hours.\n" \
                                            + "When starting operating on all guilds, only guilds that have an announce channel (or play channel, if you specify), will receive the giveaway.")
    @app_commands.command(name="start-xmas-stocking-giveaway",
                            description="Start a giveaway of the christmas stocking for this year, for 48 hours")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_start_stocking_giveaway(self, interaction: Interaction, event_year: Optional[int] = None, guild_id: str = "here", channel_id: str = "", channel_type: Optional[PlayOrAnnounceChannel] = None, crate_type: str = "christmas", active_minutes: Range[int, 0] = 0, active_hours: Range[int, 0] = 48):
        """developer command starting a giveaway of the keith stocking crate for 48 hours
        """
        valid, guild = await self.GuildsUtilCog.guildWithBountiesByIdOrAllOrContext(interaction, guild_id)
        if not valid: return

        if active_minutes == 0 and active_hours == 0:
            await interaction.response.send_message(":x: `active_minutes` and `active_hours` cannot both be 0!", ephemeral=True)
            return

        event_year = event_year or utcnow().year

        if not crateTool.CrateTool.crateTypeExists(crate_type):
            await interaction.response.send_message(f":x: Unknwn crateType '{crate_type}'", ephemeral=True)
            return
        if not crateTool.CrateTool.crateTypeNumExists(crate_type, event_year):
            await interaction.response.send_message(f":x: No '{crate_type}' crate exists for year {event_year}", ephemeral=True)
            return


        async def startGiveawayForGuild(guild: BasedGuild, channel: Optional[Messageable] = None) -> Optional[GiveawayMenu]:
            if channel is None:
                if channel_type is PlayOrAnnounceChannel.bountyPlay:
                    if not guild.hasPlayChannel(): return None
                    channel = guild.getPlayChannel()
                else:
                    if not guild.hasAnnounceChannel(): return None
                    channel = guild.getAnnounceChannel()

            giveawayMsg = await channel.send("‎")
            stocking = crateTool.CrateTool.deserialize({"type": "CrateTool", "crateType": crate_type, "typeNum": event_year, "builtIn": True})
            menu = GiveawayMenu(giveawayMsg, [stocking], activeTime=timedelta(hours=active_hours, minutes=active_minutes),
                                                titleTxt="Merry Christmas!", 
                                                desc="React below to receive your stocking!\nFind it in your `$hangar tool`, and open it with the new `$use` command.",
                                                col=Colour.random())

            self.bot.reactionMenusDB[giveawayMsg.id] = menu
            await menu.updateMessage()
            return menu


        if guild is None:
            if channel_id != "":
                await interaction.response.send_message(":x: `channel_id` cannot be specified when announcing to all guilds - only one guild will have the channel id.", ephemeral=True)
                return

            await self.GuildsUtilCog.operateOverBasedGuildsAsync(self.dev_cmd_start_stocking_giveaway.callback.__name__, startGiveawayForGuild, "Giveaway started", interaction, guild, className=type(self).__name__)
            return

        if channel_id == "":
            if channel_type is None:
                channel_type = PlayOrAnnounceChannel.announcements
            channel = None
        else:
            channel = await self.GuildsUtilCog.textChannelOrThreadByIdOrContext(interaction, channel_id, guild.dcGuild)
            if channel is None: return

        await interaction.response.defer(ephemeral=True)
        menu = await startGiveawayForGuild(guild, channel=channel)
        if menu is None:
            await interaction.followup.send(f":x: The server does not have a {'play channel' if channel_type is PlayOrAnnounceChannel.bountyPlay else 'announce channel'}", ephemeral=True)
        else:
            await interaction.followup.send(f"✅ Giveaway created: {menu.msg.jump_url}")


async def setup(bot: client.BasedClient):
    # Casting here because for some reason pyright doesn't think SerializableDiscordObject is a Snowflake,
    # even though it extends discord.Object
    await bot.add_cog(DevEventsCog(bot), guilds=cast(List[Snowflake], cfg.developmentGuilds))
