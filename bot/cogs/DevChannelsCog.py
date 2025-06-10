from typing import List, cast
from bot import client, lib
from discord import app_commands, Interaction, Embed
from discord.abc import GuildChannel, Snowflake
from bot.cfg import cfg
from bot.cfg.cfg import basicAccessLevels
from bot.interactions import basedCommand
from bot.interactions.basedApp import BasedCog
from bot.databases.bountyDB import nameForDivision
from typing import List, cast


def formatChannel(c: GuildChannel):
    return "Enabled but None" if c is None else f"[{c.name}]({c.jump_url})\n*{c.id}*"


class DevChannelsCog(BasedCog):
#region commands

    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer)
    @app_commands.command(name="guild-channels",
                            description="See the special channels set in this server (bounty, play, accounce...)")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_guild_channels(self, interaction: Interaction, guild_id: str = "here"):
        """See the special channels set in this server (bounty, play, accounce...)
        """
        if guild_id == "here":
            if interaction.guild is None:
                await interaction.response.send_message(":x: Please either give a `guild_id`, or use this command from within a guild.", ephemeral=False)
                return
            guildId = interaction.guild.id
        else:
            if not lib.stringTyping.isInt(guild_id):
                await interaction.response.send_message(":x: Invalid `guild_id`: Not a number", ephemeral=False)
                return
            guildId = int(guild_id)

        if not self.bot.guildsDB.idExists(guildId):
            await interaction.response.send_message(f":x: Guild {guildId} is not in the guildsDB.", ephemeral=True)
            return

        dcGuild = self.bot.get_guild(guildId)
        guild = self.bot.guildsDB.getGuild(guildId)
        embed = Embed(title=dcGuild.name if dcGuild is not None else "<Unknown Guild>", description=("I am not a member of this guild.\n" if dcGuild is None else "") + "BountyBot channels:")
        
        embed.add_field(name="Announce", value=formatChannel(guild.getAnnounceChannel()) if guild.hasAnnounceChannel() else "None")
        embed.add_field(name="Play", value=formatChannel(guild.getPlayChannel()) if guild.hasPlayChannel() else "None")
        embed.add_field(name="Renders", value=formatChannel(guild.getRendersChannel()) if guild.hasRendersChannel() else "None")

        if guild.bountiesDisabled:
            bbcStr = "Bounties disabled"
        else:
            if guild.hasBountyBoardChannels:
                if guild.bountiesDB is None:
                    bbcStr = "Bounties enabled, but None bountiesDB"
                else:
                    bbcStr = "\n".join(f"- {nameForDivision(d)}: {'None' if d.bountyBoardChannel is None else formatChannel(d.bountyBoardChannel.channel)}" for d in guild.bountiesDB.divisions.values())
            else:
                bbcStr = "None"
        embed.add_field(name="Bounty Boards", value=bbcStr)

        await interaction.response.send_message(embed=embed, ephemeral=True)

#endregion

async def setup(bot: client.BasedClient):
    # Casting here because for some reason pyright doesn't think SerializableDiscordObject is a Snowflake,
    # even though it extends discord.Object
    await bot.add_cog(DevChannelsCog(bot), guilds=cast(List[Snowflake], cfg.developmentGuilds))
