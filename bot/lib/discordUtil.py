from __future__ import annotations
from typing import Union, TYPE_CHECKING, Tuple, Dict
if TYPE_CHECKING:
    from discord import Member, Guild, Message
    from ..users import basedUser, basedGuild
    from ..gameObjects.bounties import criminal

from . import stringTyping, emojis, exceptions
from .. import botState
from discord import Embed, Colour, HTTPException, Forbidden, RawReactionActionEvent, User
from discord import DMChannel, GroupChannel, TextChannel
from ..cfg import cfg
from ..userAlerts import userAlerts


def findBUserDCGuild(user : basedUser.BasedUser) -> Union[Guild, None]:
    """Attempt to find a discord.guild containing the given BasedUser.
    If a guild is found, it will be returned as a discord.guild. If no guild can be found, None will be returned.

    :param BasedUser user: The user to attempt to locate
    :return: A discord.Guild where user is a member, if one can be found. None if no such guild can be found.
    :rtype: discord.guild or None
    """
    if user.hasLastSeenGuildId:
        lastSeenGuild = botState.client.get_guild(user.lastSeenGuildId)
        if lastSeenGuild is None or lastSeenGuild.get_member(user.id) is None:
            user.hasLastSeenGuildId = False
        else:
            return lastSeenGuild

    if not user.hasLastSeenGuildId:
        for guild in botState.guildsDB.guilds.values():
            lastSeenGuild = botState.client.get_guild(guild.id)
            if lastSeenGuild is not None and lastSeenGuild.get_member(user.id) is not None:
                user.lastSeenGuildId = guild.id
                user.hasLastSeenGuildId = True
                return lastSeenGuild
    return None


def userOrMemberName(dcUser : User, dcGuild : Guild) -> str:
    """If dcUser is a member of dcGuild, return dcUser's display name in dcGuild
    (their nickname if they have one, or their user name otherwise), Otherwise, returm dcUser's discord user name.

    :param discord.User dcUser: The user whose name to get
    :return: dcUser's display name in dcGuild if dcUser is a member of dcGuild, dcUser.name otherwise
    :rtype: str
    :raise ValueError: When given a None dcUser
    """
    if dcUser is None:
        botState.logger.log("Main", "usrMmbrNme",
                            "Null dcUser given", eventType="USR_NONE")
        raise ValueError("Null dcUser given")

    if dcGuild is None:
        return dcUser.name

    guildMember = dcGuild.get_member(dcUser.id)
    if guildMember is None:
        return dcUser.name
    return guildMember.display_name


def getMemberFromRef(uRef: str, dcGuild: Guild) -> Union[Member, None]:
    """Attempt to find a member of a given discord guild object from a string or integer.
    uRef can be one of:
    - A user mention <@123456> or <@!123456>
    - A user ID 123456
    - A user name Carl
    - A user name and discriminator Carl#0324

    If the passed user reference is none of the above, or a matching user cannot be found in the requested guild,
    None is returned.

    :param str uRef: A string or integer indentifying a user within dcGuild either by mention, ID, name,
                    or name and discriminator
    :param discord.Guild dcGuild: A discord.guild in which to search for a member matching uRef
    :return: Either discord.member of a member belonging to dcGuild and matching uRef, or None if uRef is invalid
                or no matching user could be found
    :rtype: discord.Member or None
    """
    # Handle user mentions
    if stringTyping.isMention(uRef):
        return dcGuild.get_member(int(uRef.lstrip("<@!").rstrip(">")))
    # Handle IDs
    elif stringTyping.isInt(uRef):
        userAttempt = dcGuild.get_member(int(uRef))
        # handle the case where uRef may be the username (without discrim) of a user whose name consists only of digits.
        if userAttempt is not None:
            return userAttempt
    # Handle user names and user name+discrim combinations
    return dcGuild.get_member_named(uRef)


def userTagOrDiscrim(userID : str, guild : Guild = None) -> str:
    """If a passed user mention or ID is valid and shares a common server with the bot,
    return the user's name and discriminator. TODO: Should probably change this to display name
    Otherwise, return the passed userID.

    :param str userID: A user mention or ID in string form, to attempt to convert to name and discrim
    :param discord.Guild guild: Optional guild in which to search for the user rather than searching over the client,
                                improving efficiency.
    :return: The user's name and discriminator if the user is reachable, userID otherwise
    :rtype: str
    """
    if guild is None:
        userObj = botState.client.get_user(int(userID.lstrip("<@!").rstrip(">")))
    else:
        userObj = guild.get_member(int(userID.lstrip("<@!").rstrip(">")))
    if userObj is not None:
        return userObj.name + "#" + userObj.discriminator
    # Return the given mention as a fall back - might replace this with '#UNKNOWNUSER#' at some point.
    botState.logger.log("Main", "uTgOrDscrm", "Unknown user requested." + (("Guild:" + guild.name + "#" + str(str(guild.id)))
                        if guild is not None else "Global/NoGuild") + ". uID:" + str(userID), eventType="UKNWN_USR")
    return userID


def criminalNameOrDiscrim(criminal : criminal.Criminal) -> str:
    """If a passed criminal is a player, attempt to return the user's name and discriminator.
    Otherwise, return the passed criminal's name. TODO: Should probably change this to display name

    :param criminal criminal: criminal whose name to attempt to convert to name and discrim
    :return: The user's name and discriminator if the criminal is a player, criminal.name otherwise
    :rtype: str
    """
    if not criminal.isPlayer:
        return criminal.name
    return userTagOrDiscrim(criminal.name)


def makeEmbed(titleTxt: str = "", desc: str = "", col: Colour = Colour.blue(), footerTxt: str = "", footerIcon: str = "",
              img: str = "", thumb: str = "", authorName: str = "", icon: str = "") -> Embed:
    """Factory function building a simple discord embed from the provided arguments.

    :param str titleTxt: The title of the embed (Default "")
    :param str desc: The description of the embed; appears at the top below the title (Default "")
    :param discord.Colour col: The colour of the side strip of the embed (Default discord.Colour.blue())
    :param str footerTxt: Secondary description appearing at the bottom of the embed (Default "")
    :param str footerIcon: small Image appearing to the left of the footer text (Default "")
    :param str img: Large icon appearing as the content of the embed, left aligned like a field (Default "")
    :param str thumb: larger image appearing to the right of the title (Default "")
    :param str authorName: Secondary title for the embed (Default "")
    :param str icon: smaller image to the left of authorName. AuthorName is required for this to be displayed. (Default "")
    :return: a new discord embed as described in the given parameters
    :rtype: discord.Embed
    """
    embed = Embed(title=titleTxt, description=desc, colour=col)
    if footerTxt != "":
        embed.set_footer(text=footerTxt, icon_url=footerIcon)
    embed.set_image(url=img)
    if thumb != "":
        embed.set_thumbnail(url=thumb)
    if icon != "":
        embed.set_author(name=authorName, icon_url=icon)
    return embed


def getMemberByRefOverDB(uRef : str, dcGuild : Guild = None) -> User:
    """Attempt to get a user object from a given string user reference.
    a user reference can be one of:
    - A user mention <@123456> or <@!123456>
    - A user ID 123456
    - A user name Carl
    - A user name and discriminator Carl#0324

    If uRef is not a user mention or ID, dcGuild must be provided, to be searched for the given name.
    When validating a name uRef, the process is much more efficient when also given the user's discriminator.

    :param str uRef: A string or integer indentifying the user object to look up
    :param discord.Guild dcGuild: The guild in which to search for a user identified by uRef.
                                    Required if uRef is not a mention or ID. (Default None)
    :return: Either discord.member of a member belonging to dcGuild and matching uRef,
                or None if uRef is invalid or no matching user could be found
    :rtype: discord.Member or None
    """
    if dcGuild is not None:
        userAttempt = getMemberFromRef(uRef, dcGuild)
    else:
        userAttempt = None
    if userAttempt is None and stringTyping.isInt(uRef):
        if botState.usersDB.idExists(int(uRef)):
            userGuild = findBUserDCGuild(botState.usersDB.getUser(int(uRef)))
            if userGuild is not None:
                return userGuild.get_member(int(uRef))
    return userAttempt


def typeAlertedUserMentionOrName(alertType : userAlerts.UABase, dcUser : Union[User, Member] = None,
        basedUser : basedUser.BasedUser = None, basedGuild : basedGuild.BasedGuild = None, dcGuild : Guild = None) -> str:
    """If the given user has subscribed to the given alert type, return the user's mention.
    Otherwise, return their display name and discriminator. At least one of dcUser or basedUser must be provided.
    BasedGuild and dcGuild are both optional. If neither are provided then the joined guilds will be searched for
    the given user. This means that giving at least one of BasedGuild or dcGuild will drastically improve efficiency.
    TODO: rename basedGuild and basedUser so it doesnt match the class name

    :param userAlerts.UABase alertType: The type of alert to check the state of
    :param discord.User dcUser: The user to check the alert state of. One of dcUser or basedUser is required. (Default None)
    :param BasedUser basedUser: The user to check the alert state of. One of dcUser or basedUser is required. (Default None)
    :param BasedGuild BasedGuild: The guild in which to check the alert state. Optional, but improves efficiency.
                                    (Default None)
    :param dcGuild dcGuild: The guild in which to check the alert state. Optional, but improves efficiency. (Default None)
    :return: If the given user is alerted for the given type in the selected guild, the user's mention.
                The user's display name and discriminator otherwise.
    :rtype: str
    :raise ValueError: When given neither dcUser nor basedUser
    :raise KeyError: When given neither BasedGuild nor dcGuild,
                        and the user could not be located in any of the bot's joined guilds.
    """
    if dcUser is None and basedGuild is None:
        raise ValueError("At least one of dcUser or basedUser must be given.")

    if basedGuild is None and dcGuild is None:
        dcGuild = findBUserDCGuild(dcUser)
        if dcGuild is None:
            raise KeyError("user does not share an guilds with the bot")
    if basedGuild is None:
        basedGuild = botState.guildsDB.getGuild(dcGuild.id)
    elif dcGuild is None:
        dcGuild = botState.client.get_guild(basedGuild.id)
    if basedUser is None:
        basedGuild = botState.usersDB.getOrAddID(dcUser.id)

    guildMember = dcGuild.get_member(dcUser.id)
    if guildMember is None:
        return dcUser.name + "#" + str(dcUser.discriminator)
    if basedUser.isAlertedForType(alertType, dcGuild, basedGuild, dcUser):
        return guildMember.mention
    return guildMember.display_name + "#" + str(guildMember.discriminator)


def IDAlertedUserMentionOrName(alertID : str, dcUser : Union[Member, User] = None, basedUser : basedUser.BasedUser = None,
        basedGuild : basedGuild.BasedGuild = None, dcGuild : Guild = None) -> str:
    """If the given user has subscribed to the alert type of the given ID, return the user's mention
    Otherwise, return their display name and discriminator. At least one of dcUser or basedUser must be provided.
    BasedGuild and dcGuild are both optional. If neither are provided then the joined guilds will be searched for
    the given user. This means that giving at least one of BasedGuild or dcGuild will drastically improve efficiency.
    TODO: rename basedUser and basedGuild so it doesnt match the class name

    :param userAlerts.UABase alertType: The ID, according to userAlerts.userAlertsIDsTypes,
                                        of type of alert to check the state of
    :param discord.User dcUser: The user to check the alert state of. One of dcUser or basedUser is required. (Default None)
    :param BasedUser basedUser: The user to check the alert state of. One of dcUser or basedUser is required. (Default None)
    :param basedGuild basedUser: The guild in which to check the alert state. Optional, but improves efficiency. (Default None)
    :param dcGuild dcGuild: The guild in which to check the alert state. Optional, but improves efficiency. (Default None)
    :return: If the given user is alerted for the given type in the selected guild, the user's mention.
                The user's display name otherwise.
    :rtype: str
    """
    return typeAlertedUserMentionOrName(userAlerts.userAlertsIDsTypes[alertID], dcUser=dcUser, basedUser=basedUser,
                                        basedGuild=basedGuild, dcGuild=dcGuild)


async def startLongProcess(message: Message):
    """Indicates that a long process is starting, by adding a reaction to the given message.

    :param discord.Message message: The message to react to
    """
    try:
        await message.add_reaction(cfg.defaultEmojis.longProcess.sendable)
    except (HTTPException, Forbidden):
        pass


async def endLongProcess(message: Message):
    """Indicates that a long process has finished, by removing a reaction from the given message.

    :param discord.Message message: The message to remove the reaction from
    """
    try:
        await message.remove_reaction(cfg.defaultEmojis.longProcess.sendable, botState.client.user)
    except (HTTPException, Forbidden):
        pass


async def reactionFromRaw(payload: RawReactionActionEvent) -> Tuple[Message, Union[User, Member], emojis.BasedEmoji]:
    """Retrieve complete Reaction and user info from a RawReactionActionEvent payload.

    :param RawReactionActionEvent payload: Payload describing the reaction action
    :return: The message whose reactions changed, the user who completed the action, and the emoji that changed.
    :rtype: Tuple[Message, Union[User, Member], BasedEmoji]
    """
    emoji = None
    user = None
    message = None

    if payload.member is None:
        # Get the channel containing the reacted message
        if payload.guild_id is None:
            channel = botState.client.get_channel(payload.channel_id)
        else:
            guild = botState.client.get_guild(payload.guild_id)
            if guild is None:
                return None, None, None
            channel = guild.get_channel(payload.channel_id)

        # Individual handling for each channel type for efficiency
        if isinstance(channel, DMChannel):
            if channel.recipient.id == payload.user_id:
                user = channel.recipient
            else:
                user = channel.me
        elif isinstance(channel, GroupChannel):
            # Group channels should be small and far between, so iteration is fine here.
            for currentUser in channel.recipients:
                if currentUser.id == payload.user_id:
                    user = currentUser
                if user is None:
                    user = channel.me
        # Guild text channels
        elif isinstance(channel, TextChannel):
            user = channel.guild.get_member(payload.user_id)
        else:
            return None, None, None

        # Fetch the reacted message (api call)
        message = await channel.fetch_message(payload.message_id)

    # If a reacting member was given, the guild can be inferred from the member.
    else:
        user = payload.member
        message = await payload.member.guild.get_channel(payload.channel_id).fetch_message(payload.message_id)

    if message is None:
        return None, None, None

    # Convert reacted emoji to BasedEmoji
    try:
        emoji = emojis.BasedEmoji.fromPartial(payload.emoji, rejectInvalid=True)
    except exceptions.UnrecognisedCustomEmoji:
        return None, None, None

    return message, user, emoji


def messageArgsFromStr(msgStr: str) -> Dict[str, Union[str, Embed]]:
    """Transform a string description of the arguments to pass to a discord.Message constructor into type-correct arguments.

    To specify message content, simply place it at the beginning of msgStr.
    To specify an embed, give the kwarg embed=
        To give kwargs for the embed, give the kwarg name, an equals sign, then value of the kwarg encased in single quotes.

        Use makeEmbed-compliant kwarg names as follows:
            titleTxt for the embed title
            desc for the embed description
            footerTxt for the text content of the footer
            footerIcon for the URL to the image to display to the left of footerTxt
            thumb for the URL to the image to display in the top right of the embed
            img for the URL to the image to display in the main embed content
            authorName for smaller text to display in place of the title
            icon for the URL to the image to display to the left of authorName

        To give fields for the embed, give field names and values separated by a new line.
        {NL} in any field will be replaced with a new line.

    :param str msgStr: A string description of the message args to create, as defined above
    :return: The message content from msgStr, and an embed as described by the kwargs and fields in msgStr.
    :rtype: Dict[str, Union[str, Embed]]
    """
    msgEmbed = None

    try:
        embedIndex = msgStr.index("embed=")
    except ValueError:
        msgText = msgStr
    else:
        msgText, msgStr = msgStr[:embedIndex], msgStr[embedIndex + len("embed="):]

        embedKwargs = { "titleTxt":     "",
                        "desc":         "",
                        "footerTxt":    "",
                        "footerIcon":   "",
                        "thumb":        "",
                        "img":          "",
                        "authorName":   "",
                        "icon":         ""}

        for argName in embedKwargs:
            try:
                startStr = argName + "='"
                startIndex = msgStr.index(startStr) + len(startStr)
                endIndex = startIndex + msgStr[msgStr.index(startStr) + len(startStr):].index("'")
                embedKwargs[argName] = msgStr[startIndex:endIndex]
                msgStr = msgStr[endIndex + 2:]
            except ValueError:
                pass

        msgEmbed = makeEmbed(**embedKwargs)

        try:
            msgStr.index('\n')
            fieldsExist = True
        except ValueError:
            fieldsExist = False
        while fieldsExist:
            nextNL = msgStr.index('\n')
            try:
                closingNL = nextNL + msgStr[nextNL + 1:].index('\n')
            except ValueError:
                fieldsExist = False
            else:
                msgEmbed.add_field(name=msgStr[:nextNL].replace("{NL}", "\n"),
                                            value=msgStr[nextNL + 1:closingNL + 1].replace("{NL}", "\n"),
                                            inline=False)
                msgStr = msgStr[closingNL + 2:]

            if not fieldsExist:
                msgEmbed.add_field(name=msgStr[:nextNL].replace("{NL}", "\n"),
                                            value=msgStr[nextNL + 1:].replace("{NL}", "\n"),
                                            inline=False)

    return {"content": msgText, "embed": msgEmbed}
