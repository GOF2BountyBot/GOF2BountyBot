from __future__ import annotations
from typing import Any, Awaitable, Callable, Coroutine, Optional, Protocol, Set, Type, TypeVar, Union, TYPE_CHECKING, Tuple, Dict, cast
from typing_extensions import ParamSpec

if TYPE_CHECKING:
    from ..users import basedUser, basedGuild
    from ..gameObjects.bounties import criminal
    from .. import client

if TYPE_CHECKING:
    TParams = ParamSpec('TParams')
else:
    TParams = TypeVar('TParams')

import discord
from discord.errors import NotFound
from discord import Interaction, PartialMessageable, User, Member, ClientUser, Guild, Message
from discord import Embed, Colour, HTTPException, Forbidden, RawReactionActionEvent
from discord import DMChannel, GroupChannel, TextChannel
from discord.abc import Messageable

from . import stringTyping, emojis, exceptions
from .. import botState
import discord
from discord import Embed, Colour, HTTPException, Forbidden, RawReactionActionEvent, User, File
from discord import DMChannel, GroupChannel, TextChannel
from ..cfg import cfg
from ..userAlerts import userAlerts

from functools import wraps, partial
import asyncio
from enum import Enum
from datetime import datetime
from PIL.Image import Image
from io import BytesIO

from ..logging import LogCategory
from ..baseClasses.serializable import Serializable


class AnyCoroutine(Protocol):
    def __call__(*args, **kwargs) -> Awaitable: ...


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


def userOrMemberName(dcUser: User, dcGuild: Guild) -> str:
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
    if userAttempt is None and stringTyping.isInt(uRef):
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

TReturn = TypeVar("TReturn", covariant=True)

def asyncWrap(func: Callable[TParams, TReturn]) -> Callable[TParams, Coroutine[Any, Any, TReturn]]:
    """Function decorator wrapping a synchronous function into an asynchronous executor call.
    This is a last-resort expensive operation, as a new process is spawned off for each call of the funciton.
    Where possible, use natively asynchronous code, e.g aiohttp instead of requests.

    Author:
    https://stackoverflow.com/a/50450553/11754606

    :param Callable func: Function to wrap. Cannot be a coroutine. (any signature)
    :return: An awaitable wrapping func
    :rtype: Coroutine
    """
    @wraps(func)
    async def run(*args, loop=None, executor=None, **kwargs):
        if loop is None:
            loop = asyncio.get_event_loop()
        pfunc = partial(func, *args, **kwargs)
        return await loop.run_in_executor(executor, pfunc)
    
    # TODO: Ignoring here because I'm not sure how to type `run`, but it appears to be correct in practise
    return run # type: ignore


async def asyncOperationWithRetry(f: Callable[..., Coroutine], opName: str, logCategory: LogCategory, className: str, meta: str,
                                    *fArgs, **fKwargs) -> Optional[Message]:
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
    :return: The message if it was created, None if an error occurred
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
                msg = await f(*fArgs, **fKwargs)
                botState.client.logger.log(className, camelFName,
                                    f"{opName} successful, but only after " \
                                        + f"{tryNum} retr{'y' if tryNum == 1 else 'ies'}. Meta: " + meta,
                                    category=logCategory, eventType="RETRY-SUCCESS")
                return msg
            except HTTPException:
                await asyncio.sleep(cfg.httpErrRetryDelaySeconds)

        logError(e)

    return None
    

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


def extractFuncName(f: Union[Awaitable, Callable]) -> Tuple[str, str]:
    # https://stackoverflow.com/a/63933827
    if hasattr(f, "__qualname__"):
        name: str = f.__qualname__ # type: ignore
    else:
        name = str(f).split(" ", 3)[-2]
    
    if "." in name:
        i = len(name) - name[::-1].index(".")
        return name[:i-1], name[i:]
    else:
        if hasattr(f, "__module__"):
            return f.__module__, name
        return "main", name


def logException(task: asyncio.Task, exception: BaseException, logCategory: Optional[LogCategory] = None, className: Optional[str] = None,
                    funcName: Optional[str] = None, noPrintEvent: bool = False, noPrint: bool = False):
    """Convenience method to log an exception that occurred on `task`, using `botState.client.logger`.
    This method is intended to be called by `logExceptionsOnTask`. 
    All parameters other than `task` and `exception` are optional. If not given, they will be inferred from `task`.

    :param logCategory: The category to log into (Default None)
    :type logCategory: Optional[str]
    :param className: Override for the class name to log exceptions as. When excluded, this is inferred (Default None)
    :type className: Optional[str]
    :param funcName: Override for the function name to log exceptions as. When excluded, this is inferred (Default None)
    :type funcName: Optional[str]
    :param noPrintEvent: Give True to skip printing the event string (will still be logged to file) (Default False)
    :type noPrintEvent: Optional[bool]
    :param noPrint: Give True to skip printing the exception entirely (will still be logged to file) (Default False)
    :type noPrint: Optional[bool]
    """
    if logCategory is None:
        logCategory = LogCategory.misc

    if className is None or funcName is None:
        # TODO: Ignoring warning here on incorrect type return from get_coro
        # Theoretically this can return a Generator, but I can't see where in the code that would happen!
        # Also, Task.__init__ will validate that the task's coro is a Coroutine
        extractedClass, extractedFunc = extractFuncName(task.get_coro()) # type: ignore[reportGeneralTypeIssues]
        className = extractedClass if className is None else className
        funcName = extractedFunc if funcName is None else funcName

    botState.client.logger.log(className, funcName, str(exception), category=logCategory, exception=exception,
                                noPrint=noPrint, noPrintEvent=noPrintEvent)


def logExceptionsOnTask(task: asyncio.Task, logCategory: Optional[LogCategory] = None, className: Optional[str] = None, funcName: Optional[str] = None,
                        noPrintEvent: bool = False, noPrint: bool = False):
    """See if any exceptions occurred in `task`. If they did, then log them using `botState.client.logger`.
    If `task` has not finished execution, this is treated as an exception and is logged.
    If `task` has no exceptions set, do nothing.
    All parameters other than `task` are optional. If not given, they will be inferred from `task`.

    :param logCategory: The category to log into (Default None)
    :type logCategory: Optional[str]
    :param className: Override for the class name to log exceptions as. When excluded, this is inferred (Default None)
    :type className: Optional[str]
    :param funcName: Override for the function name to log exceptions as. When excluded, this is inferred (Default None)
    :type funcName: Optional[str]
    :param noPrintEvent: Give True to skip printing the event string (will still be logged to file) (Default False)
    :type noPrintEvent: Optional[bool]
    :param noPrint: Give True to skip printing the exception entirely (will still be logged to file) (Default False)
    :type noPrint: Optional[bool]
    """
    if e := cast(Optional[Exception], task.exception()):
        logException(task, e, logCategory=logCategory, className=className, funcName=funcName,
                        noPrintEvent=noPrintEvent, noPrint=noPrint)


class BasicScheduler:
    """A very basic handler for parallelizing coroutine executions and handling their exceptions.
    """
    def __init__(self) -> None:
        self.tasks: Set[asyncio.Task] = set()


    def any(self) -> bool:
        return bool(self.tasks)


    def add(self, coro: Union[Coroutine, asyncio.Task]) -> asyncio.Task:
        """Schedule a coroutine execution onto the event loop.
        Pass a normal parenthesized call to a coroutine, but without awaiting it.
        Execution begins immediately.

        :param coro: The coroutine execution to parallelize
        :type coro: Awaitable
        :return: A task wrapping the execution
        :rtype: asyncio.Task
        """
        t = asyncio.create_task(coro) if isinstance(coro, Coroutine) else coro
        self.tasks.add(t)
        return t


    async def wait(self):
        """Wait for all registered tasks to complete
        """
        if self.tasks:
            await asyncio.wait(self.tasks)


    def logExceptions(self, logCategory: Optional[LogCategory] = None, className: Optional[str] = None, funcName: Optional[str] = None, noPrintEvent: bool = False,
                        noPrint: bool = False):
        """See if any exceptions occurred in the registered tasks. If they did, then log them using `botState.client.logger`.

        :param logCategory: The category to log into (Default None)
        :type logCategory: Optional[str]
        :param className: Override for the class name to log exceptions as. When excluded, this is inferred (Default None)
        :type className: Optional[str]
        :param funcName: Override for the function name to log exceptions as. When excluded, this is inferred (Default None)
        :type funcName: Optional[str]
        :param noPrintEvent: Give True to skip printing the event string (will still be logged to file) (Default False)
        :type noPrintEvent: Optional[bool]
        :param noPrint: Give True to skip printing the exception entirely (will still be logged to file) (Default False)
        :type noPrint: Optional[bool]
        """
        for t in self.tasks:
            logExceptionsOnTask(t, logCategory=logCategory, className=className, funcName=funcName, noPrintEvent=noPrintEvent,
                                noPrint=noPrint)


    def raiseExceptions(self):
        """Raise any exceptions on the registered tasks.
        Since this operation is a raise, it will halt on the first encountered exception.
        To handle all exceptions, call repeatedly or use getExceptions.

        :raises Exception: When an exception is encountered on any registered task
        """
        for t in self.tasks:
            if e := t.exception():
                raise e


    def getExceptions(self) -> Dict[Coroutine, BaseException]:
        """Get all exceptions set on the registered tasks. This does not raise the exceptions.
        Will also include CancelledError/InvalidStateError if raised on the task.

        :return: A mapping from coroutines to raised exceptions. Will be empty if no exceptions were raised
        :rtype: Dict[Coroutine, BaseException]
        """
        # TODO: Ignoring warning here on incorrect type return from get_coro
        # Theoretically this can return a Generator, but I can't see where in the code that would happen!
        # Also, Task.__init__ will validate that the task's coro is a Coroutine
        exceptions: Dict[Coroutine, BaseException] = {}
        for t in self.tasks:
            try:
                e = t.exception()
            except BaseException as ex:
                exceptions[t.get_coro()] = ex # type: ignore[reportGeneralTypeIssues]
            else:
                if e is not None:
                    exceptions[t.get_coro()] = e # type: ignore[reportGeneralTypeIssues]

        return exceptions


    def getResults(self) -> Dict[Coroutine, Tuple[Optional[BaseException], Any]]:
        """Get all results returned by the registered tasks.
        Results are returned as a mapping:
        {
            coro: (ex, result)
        }
        coro is the coroutine that was executed.
        ex is the exception that was set on the task if any, including CancelledError/InvalidStateError.
        result is the return value of the task.

        :return: A mapping from coroutines to their exceptions and returned values
        :rtype: Dict[Coroutine, Tuple[Optional[BaseException], Any]]
        """
        # TODO: Ignoring warning here on incorrect type return from get_coro
        # Theoretically this can return a Generator, but I can't see where in the code that would happen!
        # Also, Task.__init__ will validate that the task's coro is a Coroutine
        results: Dict[Coroutine, Tuple[Optional[BaseException], Any]] = {}
        for t in self.tasks:
            c = t.get_coro()
            try:
                results[c] = (None, t.result()) # type: ignore[reportGeneralTypeIssues]
            except BaseException as e:
                results[c] = (e, None) # type: ignore[reportGeneralTypeIssues]
        
        return results


    def clear(self):
        """Delete all recorded tasks
        """
        self.tasks.clear()

    
    def __bool__(self) -> bool:
        """Decide if the scheduler has any tasks registered

        :return: True if at least one task is scheduled, False otherwise
        :rtype: bool
        """
        return bool(self.tasks)


    def __len__(self) -> int:
        """Get the number of registered tasks

        :return: The number of tasks
        :rtype: int
        """
        return len(self.tasks)


async def awaitCoroAndLogExceptions(coro: Coroutine, logCategory: Optional[LogCategory] = None, className: Optional[str] = None, funcName: Optional[str] = None,
                        noPrintEvent: bool = False, noPrint: bool = False) -> Any:
    """Await `coro`, and then log any exceptions that occurred using `botState.client.logger`.
    All parameters other than `coro` are optional. If not given, they will be inferred from `coro`.

    :param coro: The coroutine whose exceptions to log
    :type coro: Awaitable
    :param logCategory: The category to log into (Default None)
    :type logCategory: Optional[str]
    :param className: Override for the class name to log exceptions as. When excluded, this is inferred (Default None)
    :type className: Optional[str]
    :param funcName: Override for the function name to log exceptions as. When excluded, this is inferred (Default None)
    :type funcName: Optional[str]
    :param noPrintEvent: Give True to skip printing the event string (will still be logged to file) (Default False)
    :type noPrintEvent: Optional[bool]
    :param noPrint: Give True to skip printing the exception entirely (will still be logged to file) (Default False)
    :type noPrint: Optional[bool]
    :return: A task wrapping the execution
    :rtype: asyncio.Task
    """
    inner = asyncio.create_task(coro)
    await inner
    logExceptionsOnTask(inner, logCategory=logCategory, className=className, funcName=funcName,
                        noPrintEvent=noPrintEvent, noPrint=noPrint)
    return inner.result


def scheduleCoroWithLogging(coro: Coroutine, logCategory: Optional[LogCategory] = None, className: Optional[str] = None, funcName: Optional[str] = None,
                        noPrintEvent: bool = False, noPrint: bool = False) -> asyncio.Task:
    """Schedule a coroutine execution onto the event loop, and log any exceptions that occur during
    execution with `botState.client.logger`.
    Very useful for synchronously scheduling a coroutine for execution without *completely* missing any exceptions.
    Pass a normal parenthesized call to a coroutine, but without awaiting it.
    The task that is contructed is returned, but you don't need to do anything with this for execution to complete.
    If your coroutine returned a value, this will be the result of the task once it completes.
    All parameters other than `coro` are optional. If not given, they will be inferred from `coro`.

    :param coro: The coroutine execution to parallelize
    :type coro: Awaitable
    :param logCategory: The category to log into (Default None)
    :type logCategory: Optional[str]
    :param className: Override for the class name to log exceptions as. When excluded, this is inferred (Default None)
    :type className: Optional[str]
    :param funcName: Override for the function name to log exceptions as. When excluded, this is inferred (Default None)
    :type funcName: Optional[str]
    :param noPrintEvent: Give True to skip printing the event string (will still be logged to file) (Default False)
    :type noPrintEvent: Optional[bool]
    :param noPrint: Give True to skip printing the exception entirely (will still be logged to file) (Default False)
    :type noPrint: Optional[bool]
    :return: A task wrapping the execution
    :rtype: asyncio.Task
    """
    return asyncio.create_task(awaitCoroAndLogExceptions(coro, logCategory=logCategory, className=className, funcName=funcName,
                        noPrintEvent=noPrintEvent, noPrint=noPrint))


def truncateWithEllipse(s: str, maxLength: int, truncatedLength: int, ellipse: str = "...") -> str:
    """If `s` is longer than `maxLength`, truncate it to `truncatedLength` and append `ellipse`.
    If `s` is not longer than `maxLength`, do nothing.

    :param s: The string to potentially truncate
    :type s: str
    :param maxLength: The cutoff before truncation is triggered
    :type maxLength: int
    :param truncatedLength: The number of characters that should remain after truncation is triggered (ignoring `ellipse`)
    :type truncatedLength: int
    :param ellipse: The string to append onto truncated strings (Default "...")
    :type ellipse: str, optional
    :return: `s` truncated to `truncatedLength` and with `ellipse` appended if `s` is longer than `maxLength`, `s` otherwise
    :rtype: str
    """
    return s if len(s) <= maxLength else s[:truncatedLength] + ellipse


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


async def dummyCoroutine(value: Optional[Any]):
    """Dummy coroutine function to return the given value. Acts as an analogue for C#'s Task.CompletedTask or Task.FromResult

    :param value: The value to immediately return
    :type value: Optional[Any]
    :return: `value`
    :rtype: Optional[Any]
    """
    return value


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
        # No isOpen check available for PIL.Image.Image
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
