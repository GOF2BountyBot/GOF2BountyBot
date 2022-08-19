from typing import List, cast
from discord import Forbidden, HTTPException, TextChannel, app_commands, Interaction, Guild
from discord.abc import GuildChannel, Snowflake

from .. import client, lib
from ..cfg import cfg
from ..cfg.cfg import basicAccessLevels
from ..interactions import basedCommand, basedApp
from ..users.basedGuild import GuildChannelType
from ..databases.bountyDB import BountyDB, nameForDivision
from ..gameObjects.bounties.bountyBoards.bountyBoardChannel import BountyBoardChannel

class AdminChannelsCog(basedApp.BasedCog):
    def __init__(self, bot: client.BasedClient, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)


    async def setGuildChannel(self, interaction: Interaction, channelType: GuildChannelType, friendlyName: str):
        requestedBBGuild = self.bot.guildsDB.fromInteraction(interaction)
        if not isinstance(interaction.channel, TextChannel):
            await interaction.response.send_message(":x: Invalid channel. Only text channels are accepted.", ephemeral=True)
        else:
            requestedBBGuild.setChannel(channelType, interaction.channel)
            await interaction.response.send_message(f":ballot_box_with_check: {friendlyName} channel set!", ephemeral=True)


    async def removeGuildChannel(self, interaction: Interaction, channelType: GuildChannelType, friendlyName: str):
        requestedBBGuild = self.bot.guildsDB.fromInteraction(interaction)
        if requestedBBGuild.hasChannel(channelType):
            requestedBBGuild.removeChannel(channelType)
            await interaction.response.send_message(f":ballot_box_with_check: {friendlyName} channel removed!", ephemeral=True)
        else:
            await interaction.response.send_message(f":x: This server has no {friendlyName} channel set!", ephemeral=True)


    @app_commands.guild_only
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.serverAdmin, helpSection="channels")
    @app_commands.command(name="set-announcements-channel",
                            description="Set the channel where BountyBot will send announcements (e.g new bounties)")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def admin_cmd_set_announce_channel(self, interaction: Interaction):
        """admin command for setting the current guild's announcements channel
        """
        await self.setGuildChannel(interaction, GuildChannelType.Announcements, "announcements")


    @app_commands.guild_only
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.serverAdmin, helpSection="channels")
    @app_commands.command(name="remove-announcements-channel",
                            description="Disable BountyBot announcements in the server's announcements channel (e.g new bounties)")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def admin_cmd_remove_announce_channel(self, interaction: Interaction):
        """admin command for removing the current guild's announcements channel
        """
        await self.removeGuildChannel(interaction, GuildChannelType.Announcements, "announcements")


    @app_commands.guild_only
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.serverAdmin, helpSection="channels")
    @app_commands.command(name="set-play-channel",
                            description="Set the channel where BountyBot will send info about completed bounties")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def admin_cmd_set_play_channel(self, interaction: Interaction):
        """admin command for setting the current guild's play channel
        """
        await self.setGuildChannel(interaction, GuildChannelType.BountyPlay, "bounty play")


    @app_commands.guild_only
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.serverAdmin, helpSection="channels")
    @app_commands.command(name="remove-play-channel",
                            description="Disable completed bounties info messages in the server's play channel")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def admin_cmd_remove_play_channel(self, interaction: Interaction):
        """admin command for removing the current guild's play channel
        """
        await self.removeGuildChannel(interaction, GuildChannelType.BountyPlay, "bounty play")


    @app_commands.guild_only
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.serverAdmin, helpSection="channels",
                                formattedDesc="Restrict custom skin rendering with the `showme ship` command to this channel")
    @app_commands.command(name="set-renders-channel",
                            description="Restrict custom skin rendering with the showme ship command to this channel")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def admin_cmd_set_renders_channel(self, interaction: Interaction):
        """admin command for setting the current guild's renders channel
        """
        await self.setGuildChannel(interaction, GuildChannelType.Renders, "skin renders")


    @app_commands.guild_only
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.serverAdmin, helpSection="channels",
                                formattedDesc="Stop restricting custom skin rendering with the `showme ship` command to the server's renders channel")
    @app_commands.command(name="remove-renders-channel",
                            description="Stop restricting custom skin rendering with the showme ship command to the server's renders channel")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def admin_cmd_remove_renders_channel(self, interaction: Interaction):
        """admin command for removing the current guild's renders channel
        """
        await self.removeGuildChannel(interaction, GuildChannelType.BountyPlay, "skin renders")


    @app_commands.guild_only
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.serverAdmin, helpSection="channels",
                                formattedDesc=f"Create {len(cfg.bountyDivisionNames)} new channels, and activate them as *bountyboards*.\n" \
                                            + "BountyBoard channels show *all* information about active bounties, continuously update " \
                                            + "their listings (e.g cross through checked systems), and only show *active* bounties " \
                                            + "(listings for located bounties are removed).")
    @app_commands.command(name="make-bounty-board-channels",
                            description=f"Create {len(cfg.bountyDivisionNames)} new channels, and activate them as bountyboards.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def admin_cmd_make_bounty_board_channels(self, interaction: Interaction):
        """admin command for creating and activating new channels for each division, as bounty board channels
        """
        # Casting here because message.guild can be none, but this command has AllowDM set to False, so it will never be None
        dcGuild = cast(Guild, interaction.guild)
        guild = self.bot.guildsDB.fromInteraction(interaction)
        if guild.bountiesDisabled:
            await interaction.response.send_message(":x: Bounties are disabled in this server! You can re-enable them with " \
                                                    "the `/config` command.", ephemeral=True)
            return
            
        # Casting here because guild.bountiesDB can be None, but this is checked for in the guild.bountiesDisabled check above
        bountiesDB = cast(BountyDB, guild.bountiesDB)

        if guild.hasBountyBoardChannels:
            await interaction.response.send_message(":x: This server already has bounty board channels!", ephemeral=True)
            return
        
        if isinstance(interaction.channel, GuildChannel) and (category := interaction.channel.category):
            if not category.permissions_for(dcGuild.me).manage_channels:
                await interaction.response.send_message(":x: I don't have permission to create new channels here!", ephemeral=True)
                return
        else:
            category = None
            if not dcGuild.me.guild_permissions.manage_channels:
                await interaction.response.send_message(":x: I don't have permission to create new channels here!", ephemeral=True)
                return

        await interaction.response.defer(ephemeral=True, thinking=True)
        
        try:
            for div in bountiesDB.divisions.values():
                divChannel = await dcGuild.create_text_channel(nameForDivision(div) + "-bounty-board", category=category,
                                                                reason="admin requested creation of bountyboard channels")
                await div.addBountyBoardChannel(divChannel, self.bot)
        except (Forbidden, HTTPException, lib.exceptions.NoLongerExists):
            await interaction.followup.send(":woozy_face: Creation of a channel failed. "
                                            "Please make sure I have permission to make channels, and try again.", ephemeral=True)
            for div in bountiesDB.divisions.values():
                if div.bountyBoardChannel is not None:
                    div.removeBountyBoardChannel()
        else:
            await interaction.followup.send(":ballot_box_with_check: Bounty board channels created and activated:\n" \
                                            # Casting here because division.bountyBoardChannel cannot be none after we've just assigned them
                                            + ", ".join(cast(BountyBoardChannel, div.bountyBoardChannel).channel.mention
                                                        for div in bountiesDB.divisions.values()), ephemeral=True)
            guild.hasBountyBoardChannels = True


    @app_commands.guild_only
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.serverAdmin, helpSection="channels",
                                formattedDesc="Disable updating of the server's bounty board channels. "
                                                "The channels themselves will not be deleted, they will simply become inactive.")
    @app_commands.command(name="disable-bounty-board-channels",
                            description="Send from any channel to disable the server's bountyboard channels, without deleting them.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def admin_cmd_remove_bounty_board_channels(self, interaction: Interaction):
        """admin command for removing the current guild's bounty board channels
        """
        guild = self.bot.guildsDB.fromInteraction(interaction)
        if guild.bountiesDisabled:
            await interaction.response.send_message(":x: Bounties are disabled in this server! You can re-enable them with " \
                                                    + "`/config bounties enable`", ephemeral=True)
        elif not guild.hasBountyBoardChannels:
            await interaction.response.send_message(":x: This server does not have bounty board channels!", ephemeral=True)
        else:
            # Casting here because guild.bountiesDB can be None, but this is checked for in the guild.bountiesDisabled check above
            for div in cast(BountyDB, guild.bountiesDB).divisions.values():
                div.removeBountyBoardChannel()
            guild.hasBountyBoardChannels = False
            await interaction.response.send_message(":ballot_box_with_check: All bounty board channels disabled!", ephemeral=True)

    
    @app_commands.guild_only
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.serverAdmin, helpSection="channels",
                                formattedDesc="Completely rebuilds the bountyboard, removing known listing messages. " \
                                            + "This will not remove any other messages.")
    @app_commands.command(name="bbc-rebuild",
                            description="Completely rebuilds the bountyboard, removing known listing messages.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def admin_cmd_rebuild_bounty_board_channel(self, interaction: Interaction):
        """admin command to rebuild bounty board channel where the message was sent
        """
        guild = self.bot.guildsDB.fromInteraction(interaction)
        if guild.bountiesDisabled:
            await interaction.response.send_message(":x: Bounties are disabled in this server! You can re-enable them with " \
                                                    + "`/config bounties enable`", ephemeral=True)
        elif not guild.hasBountyBoardChannels:
            await interaction.response.send_message(":x: This server does not have bounty board channels!", ephemeral=True)
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            found = False
            # Casting here because guild.bountiesDB can be None, but this is checked for in the guild.bountiesDisabled check above
            for div in cast(BountyDB, guild.bountiesDB).divisions.values():
                # Casting here because division.bountyBoardChannel can be None, but this is checked for with the
                # guild.hasBountyBoardChannels check above.
                if cast(BountyBoardChannel, div.bountyBoardChannel).channel == interaction.channel:
                    found = True
                    await cast(BountyBoardChannel, div.bountyBoardChannel).rebuild()
                    break
            if found:
                await interaction.followup.send(":ballot_box_with_check: Bounty board rebuilt!", ephemeral=True)
            else:
                await interaction.followup.send(":x: This is not a bountyboard! Please call the command from " \
                                                + "within the board you wish to rebuild.", ephemeral=True)


async def setup(bot: client.BasedClient):
    # Casting here because for some reason pyright doesn't think SerializableDiscordObject is a Snowflake,
    # even though it extends discord.Object
    await bot.add_cog(AdminChannelsCog(bot), guilds=cast(List[Snowflake], cfg.developmentGuilds))
