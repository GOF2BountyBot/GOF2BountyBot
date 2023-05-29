from typing import Optional, Union, cast
from discord import Guild, HTTPException, Interaction, app_commands
from ..cfg import cfg
from . import accessLevels
from .. import client
from ..lib.discordUtil import textChannel, scheduleCoroWithLogging


async def _checkLevel(level: "accessLevels.AccessLevelType", interaction: Interaction) -> bool:
    return await level.userHasAccess(interaction) \
            if issubclass(level, accessLevels.AccessLevelAsync) \
            else level.userHasAccess(interaction)


async def inferUserPermissions(interaction: Interaction) -> "accessLevels.AccessLevelType":
    """Get the commands access level of the user that triggered an interaction.
    
    :return: message.author's access level
    :rtype: basedCommand.AccessLevelType
    """
    for levelName in cfg.userAccessLevels[::-1]:
        level = accessLevels._accessLevels[levelName]
        if await _checkLevel(level, interaction):
            return level
    return accessLevels.defaultAccessLevel()


def accessLevelSufficient(current: "accessLevels.AccessLevelType", required: "accessLevels.AccessLevelType") -> bool:
    """Decide whether an access level is at least as high in the heirarchy as another

    :param current: The 'owned' access level
    :type current: accessLevels.AccessLevelType
    :param required: The access level acting as a comparison point
    :type required: accessLevels.AccessLevelType
    :return: `True` if `current` is at least as high in the access level heirarchy as `required`, `False` otherwise
    :rtype: bool
    """
    return current._intLevel() >= required._intLevel()


async def userHasAccess(interaction: Interaction, level: "accessLevels.AccessLevelType") -> bool:
    return accessLevelSufficient(await inferUserPermissions(interaction), level)


def create_requireAccess(level: Union["accessLevels.AccessLevelType", str]):
    """A command check that requires at least an access level of `level` to use the command.

    :param level: The access level to required
    :type level: Union[basedCommand.AccessLevelType, str]
    :return: The command check callback
    :rtype: Callable[[Interaction], bool]
    """
    if isinstance(level, str):
        level = accessLevels.accessLevelNamed(level)
    async def inner(interaction: Interaction):
        return await userHasAccess(interaction, level)

    return inner


async def _notifyHomeGuildTransfer(interaction: Interaction):
    # Doing some casts in here because this is a private method that requires interaction.guild to be present
    try:
        await interaction.user.send(f":airplane_arriving: Your home server has been set to **{cast(Guild, interaction.guild).name}**.\n"
                                    + "See `/help transfer` for more information.")
    except HTTPException:
        await textChannel(interaction).send(f":airplane_arriving: {interaction.user.mention}, Your home server has been set to **{cast(Guild, interaction.guild).name}**.\n"
                                        + "See `/help transfer` for more information.")


def create_requireHomeGuild(onboardNewUsers: bool = True):
    """A command check that requires the command to be called from within the user's home guild.

    :param onboardNewUsers: When True, the check will create the user's record in the client's usersDB, and set their homeGuild (Default True)
    :return: The command check callback
    :rtype: Callable[[Interaction], bool]
    """
    async def inner(interaction: Interaction) -> bool:
        if interaction.guild is None: return False

        if not isinstance(interaction.client, client.BasedClient):
            raise TypeError(f"{create_requireHomeGuild.__name__} can only be applied to commands which are handled by a {client.BasedClient.__name__}")
        
        if not interaction.client.guildsDB.idExists(interaction.guild.id): return False

        if not interaction.client.usersDB.idExists(interaction.user.id):
            if onboardNewUsers:
                basedUser = interaction.client.usersDB.addID(interaction.user.id)
            else:
                return False
        else:
            basedUser = interaction.client.usersDB.getUser(interaction.user.id)

        if not basedUser.hasHomeGuild():
            if not onboardNewUsers: return False

            await basedUser.transferGuild(interaction.guild)
            scheduleCoroWithLogging(_notifyHomeGuildTransfer(interaction))

        elif basedUser.homeGuildID != interaction.guild.id:
            return False

        return True

    return inner


def requireBasedGuildFeatures(bountiesEnabled: Optional[bool] = None, shopsEnabled: Optional[bool] = None):
    """A command check that requires the command to be called from within a guild with certain BasedGuild features.

    :param bountiesEnabled: Require the server to have bounties enabled/disabled (Default None)
    :type bountiesEnabled: Optional[bool]
    :param shopsEnabled: Require the server to have division shops enabled/disabled (Default None)
    :type shopsEnabled: Optional[bool]
    :return: The command check callback
    :rtype: Callable[[Interaction], bool]
    """
    async def inner(interaction: Interaction):
        if interaction.guild is None: return False

        if not isinstance(interaction.client, client.BasedClient):
            raise TypeError(f"{requireBasedGuildFeatures.__name__} can only be applied to commands which are handled by a {client.BasedClient.__name__}")
        
        if not interaction.client.guildsDB.idExists(interaction.guild.id): return False
        
        basedGuild = interaction.client.guildsDB.getGuild(interaction.guild.id)
        if bountiesEnabled is not None and basedGuild.bountiesDisabled != (not bountiesEnabled): return False
        if shopsEnabled is not None and basedGuild.shopsDisabled != (not shopsEnabled): return False

        return True

    return inner


def guildOnly(
    *,
    bountiesEnabled: Optional[bool] = None,
    shopsEnabled: Optional[bool] = None
):
    """Wrapper around `discord.app_commands.guild_only` that is also able to require the guild to have certain BountyBot features.

    :param bountiesEnabled: Require the server to have bounties enabled/disabled (Default None)
    :type bountiesEnabled: Optional[bool]
    :param shopsEnabled: Require the server to have division shops enabled/disabled (Default None)
    :type shopsEnabled: Optional[bool]
    """
    def decorator(func):
        if not isinstance(func, app_commands.Command):
            raise TypeError("decorator can only be applied to app commands")

        if bountiesEnabled is None and shopsEnabled is None:
            return app_commands.guild_only(func)

        func.add_check(requireBasedGuildFeatures(bountiesEnabled=bountiesEnabled, shopsEnabled=shopsEnabled))

        return app_commands.guild_only(func)

    return decorator


def homeGuildOnly(
    *,
    onboardNewUsers: bool = True
):
    """A decorator that requires the command to be called from within the user's home guild.

    :param onboardNewUsers: When True, the check will create the user's record in the client's usersDB, and set their homeGuild (Default True)
    """
    def decorator(func):
        if not isinstance(func, app_commands.Command):
            raise TypeError("decorator can only be applied to app commands")

        func.add_check(create_requireHomeGuild(onboardNewUsers=onboardNewUsers))

        return app_commands.guild_only(func)

    return decorator
