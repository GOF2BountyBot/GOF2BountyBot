import discord # type: ignore[import]

from . import commandsDB as botCommands
from .. import botState, lib
from ..cfg import bbData, cfg
from ..users.basedGuild import BasedGuild
from ..databases.bountyDB import nameForDivision

botCommands.addHelpSection(2, "channels")


async def admin_cmd_set_announce_channel(message : discord.Message, args : str, isDM : bool):
    """admin command for setting the current guild's announcements channel

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    requestedBBGuild = botState.guildsDB.getGuild(message.guild.id)
    if args == "off":
        if requestedBBGuild.hasAnnounceChannel():
            requestedBBGuild.removeAnnounceChannel()
            await message.reply(":ballot_box_with_check: Announcements channel removed!",
                                mention_author=False)
        else:
            await message.reply(":x: This server has no announce channel set!",
                                mention_author=False)
    elif args != "":
        await message.reply(":x: Invalid arguments! Can only be `off` to disable this server's announce channel, " \
                                    + "or no args to use this channel as the announce channel.",
                            mention_author=False)
    else:
        requestedBBGuild.setAnnounceChannel(message.channel)
        await message.reply(":ballot_box_with_check: Announcements channel set!",
                            mention_author=False)

botCommands.register("set-announce-channel", admin_cmd_set_announce_channel, 2, allowDM=False, helpSection="channels",
                    signatureStr="**set-announce-channel** *[off]*",
                    longHelp="Set the channel where BountyBot will send announcements (e.g new bounties)\n" \
                                + "> Use `set-announce-channel off` to disable announcements.")


async def admin_cmd_set_play_channel(message : discord.Message, args : str, isDM : bool):
    """admin command for setting the current guild's play channel

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    requestedBBGuild: BasedGuild = botState.guildsDB.getGuild(message.guild.id)
    if args == "off":
        if requestedBBGuild.hasPlayChannel():
            requestedBBGuild.removePlayChannel()
            await message.reply(mention_author=False, content=":ballot_box_with_check: Bounty play channel removed!")
        else:
            await message.reply(mention_author=False, content=":x: This server has no play channel set!")
    elif args != "":
        await message.reply(mention_author=False, content=":x: Invalid arguments! Can only be `off` to disable this server's play channel, " \
                                    + "or no args to use this channel as the play channel.")
    else:
        requestedBBGuild.setPlayChannel(message.channel)
        await message.reply(mention_author=False, content=":ballot_box_with_check: Bounty play channel set!")

botCommands.register("set-play-channel", admin_cmd_set_play_channel, 2, allowDM=False, helpSection="channels",
                    signatureStr="**set-play-channel** *[off]*",
                    longHelp="Set the channel where BountyBot will send info about completed bounties\n" \
                        + "> Use `set-play-channel off` to disable completed bounty announcements.")


async def admin_cmd_set_renders_channel(message : discord.Message, args : str, isDM : bool):
    """admin command for setting the current guild's autoskin renders channel

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    requestedBBGuild: BasedGuild = botState.guildsDB.getGuild(message.guild.id)
    if args == "off":
        if requestedBBGuild.hasRendersChannel():
            requestedBBGuild.removeRendersChannel()
            await message.reply(":ballot_box_with_check: Renders channel removed!",
                                mention_author=False)
        else:
            await message.reply(":x: This server has no renders channel set!",
                                mention_author=False)
    elif args != "":
        await message.reply(":x: Invalid arguments! Can only be `off` to disable this server's renders channel, " \
                                    + "or no args to use this channel as the renders channel.",
                            mention_author=False)
    else:
        requestedBBGuild.setRendersChannel(message.channel)
        await message.reply(":ballot_box_with_check: Renders channel set!",
                            mention_author=False)

botCommands.register("set-renders-channel", admin_cmd_set_renders_channel, 2, allowDM=False, helpSection="channels",
                    signatureStr="**set-renders-channel** *[off]*",
                    longHelp="Restrict custom skin rendering with `showme ship` to this channel.\n" \
                                + "> Use `set-renders-channel off` to disable this restriction again.")


async def admin_cmd_make_bounty_board_channels(message : discord.Message, args : str, isDM : bool):
    """admin command for creating and activating new channels for each division, as bounty board channels

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    """
    guild: BasedGuild = botState.guildsDB.getGuild(message.guild.id)
    if guild.bountiesDisabled:
        await message.reply(":x: Bounties are disabled in this server! You can re-enable them with: " \
                            + f"`{guild.commandPrefix}config bounties enable`")
        return
    if guild.hasBountyBoardChannels:
        await message.reply(mention_author=False,
                            content=":x: This server already has bounty board channels! Use `" + guild.commandPrefix \
                                    + "remove-bounty-board-channels` to remove them.")
        return
    
    if category := message.channel.category:
        if not message.guild.me.permissions_in(category).manage_channels:
            await message.reply(mention_author=False, content=":x: I don't have permission to create new channels here!")
            return
    elif not message.guild.me.guild_permissions.manage_channels:
        await message.reply(mention_author=False, content=":x: I don't have permission to create new channels here!")
        return
    
    try:
        for div in guild.bountiesDB.divisions.values():
            divChannel = await message.guild.create_text_channel(nameForDivision(div) + "-bounty-board", category=category,
                                                                    reason="admin requested creation of bountyboard channels")
            await div.addBountyBoardChannel(divChannel, botState.client)
    except (discord.Forbidden, discord.HTTPException, lib.exceptions.NoLongerExists):
        await message.channel.send(":woozy_face: Creation of a channel failed. " \
                                    + "Please make sure I've got permission to make channels, and try again.")
        for div in guild.bountiesDB.divisions.values():
            if div.bountyBoardChannel is not None:
                div.removeBountyBoardChannel()
    else:
        await message.reply(mention_author=False,
                            content=":ballot_box_with_check: Bounty board channels created and activated:\n" \
                                + ", ".join(div.bountyBoardChannel.channel.mention
                                            for div in guild.bountiesDB.divisions.values()))
        guild.hasBountyBoardChannels = True

botCommands.register("make-bounty-board-channels", admin_cmd_make_bounty_board_channels, 2, allowDM=False,
                    helpSection="channels", signatureStr="**make-bounty-board-channels**",
                    longHelp=f"Create {len(cfg.bountyDivisions)} new channels, and activate them as *bountyboards*.\n" \
                                + "BountyBoard channels show *all* information about active bounties, continuously update " \
                                + "their listings (e.g cross through checked systems), and only show *active* bounties " \
                                + "(listings for located bounties are removed).")


async def admin_cmd_remove_bounty_board_channels(message : discord.Message, args : str, isDM : bool):
    """admin command for removing the current guild's bounty board channels

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    guild: BasedGuild = botState.guildsDB.getGuild(message.guild.id)
    if guild.bountiesDisabled:
        await message.reply(":x: Bounties are disabled in this server! You can re-enable them with: " \
                            + f"`{guild.commandPrefix}config bounties enable`")
    elif not guild.hasBountyBoardChannels:
        await message.reply(":x: This server does not have bounty board channels!")
    else:
        for div in guild.bountiesDB.divisions.values():
            div.removeBountyBoardChannel()
        await message.reply(mention_author=False, content=":ballot_box_with_check: All bounty board channels disabled!")

botCommands.register("disable-bounty-board-channels", admin_cmd_remove_bounty_board_channels, 2, allowDM=False,
                    helpSection="channels", signatureStr="**disable-bounty-board-channels**",
                    shortHelp="Send from any channel to disable the server's bountyboard channels, without deleting them.")
