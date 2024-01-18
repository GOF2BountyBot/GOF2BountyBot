from __future__ import annotations
from typing import Any, Awaitable, Callable, Optional, Protocol, Type, TypeVar, Union, TYPE_CHECKING, Tuple, Dict, cast, overload
from enum import Enum

from ..entities.guild import basedGuild

if TYPE_CHECKING:
    from ..entities.user import basedUser
    from ..gameObjects.bounties import criminal
    from .. import client

import discord
from discord.errors import NotFound
from discord import Interaction, PartialMessageable, User, Member, ClientUser, Guild, Message, PartialMessage, Client, VoiceChannel, Thread
from discord import Embed, Colour, HTTPException, Forbidden, RawReactionActionEvent
from discord import DMChannel, GroupChannel, TextChannel
from discord.abc import Messageable, Snowflake
from discord.enums import ChannelType

from . import emojis, exceptions, graphics, stringUtil
from .. import botState
import discord
from discord import Embed, Colour, HTTPException, Forbidden, RawReactionActionEvent, User, File
from discord import DMChannel, GroupChannel, TextChannel
from ..cfg import cfg
from ..userAlerts import userAlerts

import asyncio
from enum import Enum
from datetime import datetime
from PIL.Image import Image
from io import BytesIO
from contextlib import AbstractAsyncContextManager

from ..logging import LogCategory
from ..baseClasses.serializable import Serializable


def findBUserDCGuild(user: basedUser.BasedUser, client = None) -> Union[Guild, None]:
    """Attempt to find a discord.guild containing the given BasedUser.
    If a guild is found, it will be returned as a discord.guild. If no guild can be found, None will be returned.

    :param BasedUser user: The user to attempt to locate
    :return: A discord.Guild where user is a member, if one can be found. None if no such guild can be found.
    :rtype: discord.guild or None
    """
    if user.hasHomeGuild():
        homeGuild = (client or botState.client).get_guild(user.homeGuildID)
        if homeGuild is not None:
            return homeGuild

    dcUser = (client or botState.client).get_user(user.id)
    if dcUser is not None and dcUser.mutual_guilds:
        return dcUser.mutual_guilds[0]

    return None


def userOrMemberName(dcUser: Union[User, Member], dcGuild: Optional[Guild]) -> str:
    """If dcUser is a member of dcGuild, return dcUser's display name in dcGuild
    (their nickname if they have one, or their user name otherwise), Otherwise, returm dcUser's discord user name.

    :param discord.User dcUser: The user whose name to get
    :return: dcUser's display name in dcGuild if dcUser is a member of dcGuild, dcUser.name otherwise
    :rtype: str
    :raise ValueError: When given a None dcUser
    """
    if dcUser is None:
        botState.client.logger.log("Main", "usrMmbrNme",
                            "None dcUser given", eventType="USR_NONE")
        raise ValueError("Null dcUser given")

    if dcGuild is None:
        return dcUser.name

    guildMember = dcGuild.get_member(dcUser.id)
    if guildMember is None:
        return dcUser.name
    return guildMember.display_name


def memberDisplayNameOrUserNameAndDiscrim(dcUser: Union[User, Member], dcGuild: Optional[Guild]) -> str:
    """If `dcUser` is a member of `dcGuild`, return their `display_name` in `dcGuild`.
    Otherwise, return their global username and discriminator.
    """
    if dcGuild is None: return str(dcUser)
    if isinstance(dcUser, Member) and dcUser.guild == dcGuild: return dcUser.display_name
    
    member = dcGuild.get_member(dcUser.id)
    if member is not None: return member.display_name

    return str(dcUser)


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
    if stringUtil.isMention(uRef):
        return dcGuild.get_member(int(uRef.lstrip("<@!").rstrip(">")))
    # Handle IDs
    elif stringUtil.isInt(uRef):
        userAttempt = dcGuild.get_member(int(uRef))
        # handle the case where uRef may be the username (without discrim) of a user whose name consists only of digits.
        if userAttempt is not None:
            return userAttempt
    # Handle user names and user name+discrim combinations
    return dcGuild.get_member_named(uRef)


def userTagOrDiscrim(userID: str, guild: Optional[Guild] = None) -> str:
    """If the given guild has a user with the given ID, return their mention.
    Otherwise, if the bot shares any server with the user with the given ID,
    return their name and discriminator. TODO: Should probably change this to display name
    Otherwise, return userID.

    :param str userID: A user mention or ID in string form, to attempt to convert to name and discrim
    :param discord.Guild guild: Optional guild in which to search for the user rather than searching over the client,
                                improving efficiency. (default None)
    :return: The user's name and discriminator if the user is reachable, userID otherwise
    :rtype: str
    """
    if guild is not None:
        userObj = guild.get_member(int(userID.lstrip("<@!").rstrip(">")))
        if userObj is not None:
            return userObj.mention

    userObj = botState.client.get_user(int(userID.lstrip("<@!").rstrip(">")))

    if userObj is not None:
        return userObj.name + "#" + userObj.discriminator
        
    # Return the given mention as a fall back - might replace this with '#UNKNOWNUSER#' at some point.
    botState.client.logger.log("Main", "uTgOrDscrm", "Unknown user requested." + (("Guild:" + guild.name + "#" + str(str(guild.id)))
                        if guild is not None else "Global/NoGuild") + ". uID:" + str(userID), eventType="UKNWN_USR")
    return userID


def criminalNameOrDiscrim(criminal: criminal.Criminal) -> str:
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


def getMemberByRefOverDB(uRef: str, dcGuild: Optional[Guild] = None) -> Optional[Member]:
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
    if userAttempt is None and stringUtil.isInt(uRef):
        if botState.client.usersDB.idExists(int(uRef)):
            userGuild = findBUserDCGuild(botState.client.usersDB.getUser(int(uRef)))
            if userGuild is not None:
                return userGuild.get_member(int(uRef))
    return userAttempt


def typeAlertedUserMentionOrName(alertType: Type[userAlerts.UABase], dcUser: Optional[Union[User, Member]] = None,
                                    basedUser: Optional[basedUser.BasedUser] = None, basedGuild: Optional[basedGuild.BasedGuild] = None,
                                    dcGuild: Optional[Guild] = None) -> str:
    """If the given user has subscribed to the given alert type, return the user's mention.
    Otherwise, return their display name and discriminator. At least one of dcUser or basedUser must be provided.
    BasedGuild and dcGuild are both optional. If neither are provided then the joined guilds will be searched for
    the given user. This means that giving at least one of BasedGuild or dcGuild will drastically improve efficiency.
    TODO: rename basedGuild and basedUser so it doesnt match the class name

    :param Type[userAlerts.UABase] alertType: The type of alert to check the state of
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
    if dcUser is None and basedUser is None:
        raise ValueError("At least one of dcUser or basedUser must be given.")

    if basedGuild is None and dcGuild is None:
        dcGuild = findBUserDCGuild(basedUser if basedUser is not None else botState.client.usersDB.getUser(cast(Union[User, Member], dcUser).id))
        if dcGuild is None:
            raise KeyError("user does not share any guilds with the bot")
    dcGuild = cast(Guild, dcGuild)

    if basedGuild is None:
        basedGuild = botState.client.guildsDB.getGuild(cast(Guild, dcGuild).id)
    elif dcGuild is None:
        dcGuild = cast(Guild, botState.client.get_guild(basedGuild.id))

    if basedUser is None:
        basedUser = botState.client.usersDB.getOrAddID(cast(Union[User, Member], dcUser).id)
    elif dcUser is None:
        dcUser = botState.client.get_user(basedUser.id)
    dcUser = cast(Union[User, Member], dcUser)

    guildMember = dcGuild.get_member(basedUser.id)
    if guildMember is None:
        return dcUser.name + "#" + str(dcUser.discriminator)
    if basedUser.isAlertedForType(alertType, dcGuild, basedGuild, guildMember):
        return guildMember.mention
    return guildMember.display_name + "#" + str(guildMember.discriminator)


def IDAlertedUserMentionOrName(alertID: str, dcUser: Optional[Union[Member, User]] = None, basedUser: Optional[basedUser.BasedUser] = None,
        basedGuild: Optional[basedGuild.BasedGuild] = None, dcGuild: Optional[Guild] = None) -> str:
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
        # ClientUser is pretty much guaranteed not to be null
        await message.remove_reaction(cfg.defaultEmojis.longProcess.sendable, cast(discord.ClientUser, botState.client.user))
    except (HTTPException, Forbidden):
        pass


async def reactionFromRaw(payload: RawReactionActionEvent) -> Tuple[Optional[Message], Optional[Union[User, Member, ClientUser]],
                                                                    Optional[emojis.BasedEmoji]]:
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
            if channel.recipient is None:
                return None, None, None
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
        # Casting to Messageable here because RawReactionActionEvent will only ever be constructed from Messageable channels
        message = await cast(Messageable, payload.member.guild.get_channel(payload.channel_id)) \
                    .fetch_message(payload.message_id)

    if message is None:
        return None, None, None

    # Convert reacted emoji to BasedEmoji
    try:
        emoji = emojis.BasedEmoji.fromPartial(payload.emoji, rejectInvalid=True)
    except exceptions.UnrecognisedCustomEmoji:
        return None, None, None

    return message, user, emoji


def messageArgsFromStr(msgStr: str) -> Dict[str, Union[str, Union[Embed, None]]]:
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
    try:
        embedIndex = msgStr.index("embed=")
    except ValueError:
        msgText = msgStr
        msgEmbed = None
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
    

def messageDescriptor(m: Message) -> str:
    """Construct a string detailing a message, its channel and guild.

    :param Message m: The message to describe
    :return: A string identifying m, its channel and guild
    :rtype: str
    """
    if isinstance(m.channel, DMChannel):
        return f"DM m:{m.id} u:{'None' if m.channel.recipient is None else m.channel.recipient.id}#{m.channel.id}"
    elif isinstance(m.channel, GroupChannel):
        return f"gDM m:{m.id} c:{'None' if m.channel.name is None else m.channel.name}#{m.channel.id}"
    elif isinstance(m.channel, PartialMessageable):
        return f"UNKNOWN m:{m.id} c:#{m.channel.id}"
    return f"m:{m.id} g:{m.channel.guild.name}#{m.channel.guild.id} c:{m.channel.name}#{m.channel.id}"


TResult = TypeVar("TResult")

async def discordOperationWithRetry(f: Callable[..., Awaitable[TResult]], opName: str, logCategory: LogCategory, className: str, meta: str,
                                    *fArgs: Any, **fKwargs: Any) -> Optional[TResult]:
    """Perform an asynchronous operation with a fixed retry, as defined in cfg.

    :param f: The coroutine to execute
    :type f: AnyCoroutine
    :param opName: The name of the operation, to be used in error logging
    :type opName: str
    :param logCategory: The category to log errors into
    :type logCategory: str
    :param className: The name of the class calling this function, to be used in error logging
    :type className: str
    :param meta: An extra string to describe the operation, to be used in error logging
    :param fArgs: All positional arguments to pass to f
    :param fKwargs: All keyword arguments to pass to f
    :type meta: str
    :return: The result of the operation, None if an error occurred
    :rtype: Optional[Message]
    """
    camelFName = opName.title()
    if len(opName) > 1:
        camelFName = camelFName[0].lower() + camelFName[1:]

    def logError(e: Exception):
        eName = type(e).__name__
        botState.client.logger.log(className, camelFName,
                            f"{eName} thrown on {opName}. Meta: " + meta,
                            category=logCategory, eventType=eName)

    try:
        return await f(*fArgs, **fKwargs)
    except (Forbidden, NotFound) as e:
        logError(e)
    except HTTPException as e:
        for tryNum in range(cfg.httpErrRetries):
            try:
                result = await f(*fArgs, **fKwargs)
                botState.client.logger.log(className, camelFName,
                                    f"{opName} successful, but only after " \
                                        + f"{tryNum} retr{'y' if tryNum == 1 else 'ies'}. Meta: " + meta,
                                    category=logCategory, eventType="RETRY-SUCCESS")
                return result
            except HTTPException:
                await asyncio.sleep(cfg.httpErrRetryDelaySeconds)

        logError(e)

    return None


class SerializableDiscordObject(discord.Object, Serializable):
    """A version of discord.Object with basic serializing, to support adding in configs.
    """
    def serialize(self, **kwargs) -> int:
        return self.id

    
    @classmethod
    def deserialize(cls, data: int, **kwargs) -> SerializableDiscordObject:
        return SerializableDiscordObject(data)


EMPTY_IMAGE = "https://cdn.discordapp.com/attachments/700683544103747594/979495873190969424/empty.png"
ZWSP = "​"


def embedEmpty(embed: Embed, includeFields = True) -> bool:
    return not any((includeFields and embed.fields, embed.title, embed.author.name if embed.author else None,
                    embed.author.icon_url if embed.author else None, embed.description,
                    embed.footer.text if embed.footer else None, embed.footer.icon_url if embed.footer else None))


class SupportsOptionalChannelUncached(Protocol):
    @property
    def channel(self) -> Optional[discord.interactions.InteractionChannel]: ...


class SupportsOptionalChannelCached(Protocol):
    channel: discord.utils.CachedSlotProperty[Any, Optional[discord.interactions.InteractionChannel]]

SupportsOptionalChannel = Union[SupportsOptionalChannelUncached, SupportsOptionalChannelCached]


def textChannel(o: SupportsOptionalChannel, e: Optional[Exception] = None) -> discord.abc.Messageable:
    """Get the channel from `o`. If the channel cannot be used for sending messages, then raise `e`.

    :param o: The object whose channel to retrieve
    :type o: SupportsChannel
    :param e: The exception to raise if `o`'s channel is not messageable (default IncorrectInteractionContext)
    :type e: Exception
    :raises e: If `o` is not messegeable
    :return: `o`'s channel
    :rtype: discord.abc.Messageable
    """
    if not isinstance(o.channel, discord.abc.Messageable):
        raise e if e is not None else exceptions.IncorrectInteractionContext("This operation is not valid here.")
    return o.channel


class TimeStampStyle(Enum):
    ShortTime = "t"
    LongTime = "T"
    ShortDate = "d"
    LongDate = "D"
    ShortDateTime = "f"
    LongDateTime = "F"
    Relative = "R"


def timestamp(t: datetime, format=TimeStampStyle.ShortDateTime) -> str:
    """Construct a discord timestamp string.
    Time divisions smaller than a second are ignored.

    :param t: The datetime
    :type t: datetime
    :param format: The style of the timestamp (Default ShortDateTime)
    :type format: TimeStampFormat, optional
    :return: A discord timestamp, i.e `<t:TIMESTAMP:STYLE>`
    :rtype: str
    """
    return f"<t:{int(t.timestamp())}:{format.value}>"


class ImageFile:
    """A container for a Pillow image.
    This class wraps the image in a `BytesIO` stream, and wraps that stream in a `discord.File` object.
    Calling `closeAll` will close the image that you passed in, as well as the byte stream and `discord.File`.
    """
    def __init__(self, image: Image, fileName: str):
        self.fileName = fileName
        self.image = image
        self.imageBytes = BytesIO()
        image.save(self.imageBytes, fileName.split(".")[-1])
        self.imageBytes.seek(0)
        self.file = File(self.imageBytes, filename=fileName)
        self.closed = False
    

    def closeAll(self):
        if self.closed: return
        # No isOpen check available for discord.File
        self.file.close()
        if not self.imageBytes.closed: self.imageBytes.close()
        if graphics.imageIsOpen(self.image):
            self.image.close()
        self.closed = True


    def __enter__(self):
        return self

    
    def __exit__(self, cls, value, traceback):
        self.closeAll()
        return False


def userNameIn(client: "client.BasedClient", userId: int, dcGuild: Optional[Guild]) -> str:
    if dcGuild is not None:
        member = dcGuild.get_member(userId)
        if member is not None: return member.display_name
    user = client.get_user(userId)
    if user is not None: return str(user)
    return f"<unknown user {userId}>"


async def interactionSend(interaction: Interaction, respond: bool, followup: bool, *sendArgs, **sendKwargs):
    if respond:
        return await interaction.response.send_message(*sendArgs, **sendKwargs)
    elif followup:
        return await interaction.followup.send(*sendArgs, **sendKwargs)
    else:
        sendKwargs.pop("ephemeral", None)
        return await textChannel(interaction).send(*sendArgs, **sendKwargs)


class ApiError(Enum):
    unknown_emoji = 10014


class LazyChannel():
    @overload
    def __init__(self, client: Client, channelId: int, /, guildId: Optional[int] = None, type: Optional[ChannelType] = None) -> None: ...
    
    @overload
    def __init__(self, client: Client, partialChannel: PartialMessageable, /) -> None: ...
    
    def __init__(self, client: Client, channelIdOrPartial: Union[int, PartialMessageable], guildId: Optional[int] = None, type: Optional[ChannelType] = None) -> None:
        self.client = client
        if isinstance(channelIdOrPartial, PartialMessageable):
            self.partial: Union[VoiceChannel, Thread, PartialMessageable, TextChannel] = channelIdOrPartial
        else:
            self.partial = client.get_partial_messageable(channelIdOrPartial, guild_id=guildId, type=type)

    
    async def fetch(self):
        if isinstance(self.partial, PartialMessageable):
            self.partial = await self._fetch()
        return self.partial
    

    async def _fetch(self):
        c = self.client.get_channel(self.partial.id) or await self.client.fetch_channel(self.partial.id)
        if not isinstance(c, Messageable):
            raise exceptions.NoLongerExists(self.partial.id)
        return c


    async def call(self, f: Callable[[Messageable], Awaitable[TResult]]) -> TResult:
        try:
            return await f(self.partial)
        except NotFound:
            c = await self._fetch()
            v = await f(c)
            self.partial = c
            return v
        

    def withRetry(self, f: Callable[[Messageable], Awaitable[TResult]],
                  opName: str, logCategory: LogCategory, className: str, meta: str,
                  *fArgs: Any, **fKwargs: Any) -> Awaitable[Optional[TResult]]:
        return discordOperationWithRetry(lambda: self.call(f), opName, logCategory, className, meta,
                                         *fArgs, **fKwargs)