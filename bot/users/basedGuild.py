from __future__ import annotations
from enum import Enum
from discord import Embed, Forbidden, Guild, Member, Message, HTTPException, NotFound, Colour, Role, User
from discord import TextChannel
from discord.utils import MISSING, utcnow
from typing import Any, List, Dict, Optional, Union, cast
from typing_extensions import NotRequired, TypedDict
from aiohttp import client_exceptions
import random

from ..baseClasses.serializable import SerializesToSchema, SerializesToType

from .. import botState, lib
from ..lib import gameMaths
from bot.lib.stringTyping import commaSplitNum
from ..lib.timeUtil import utcfromtimestamp
from ..logging import LogCategory
from ..gameObjects import guildShop
from ..databases.bountyDB import BountyDB, nameForDivision, divisionNameForLevel, SerializedBountyDB
from ..userAlerts import userAlerts
from bot.cfg import cfg, bbData
from ..gameObjects.bounties import bounty, bountyConfig
from ..databases import bountyDivision
from ..gameObjects.bounties.bountyBoards import bountyBoardChannel
from ..gameObjects.items.gameItem import GameItem
from . import basedUser


def formatRewardByMeta(reward: str, units: str, flags: bounty.RewardsMeta) -> str:
    """Format the value of a checking reward according to meta flags, if any

    :param reward: The reward to format (e.g an amount of credits)
    :type reward: str
    :param str units: The units of the reward, e.g xp/credits/etc
    :param flags: bounty.RewardMeta flags
    :type flags: int
    :return: reward, with any extra formatting added to represent flags
    :rtype: str
    """
    out = f"{reward} {units}"
    if bounty.RewardsMeta.USER_PRESTIGED & flags:
        out = f"~~{out}~~"
    return out


def bountyResultsFieldKwargs(place: int, userID: int, userRewards: Dict[str, Union[int, bool]], userMeta: bounty.RewardsMeta) \
        -> Dict[str, Any]:
    """Build kwargs to create a new field, representing a user's contributions to solving a bounty
    """
    creditsGained = commaSplitNum(userRewards["reward"])
    systemsChecked = userRewards["checked"]
    xpGained = "+" + commaSplitNum(userRewards["xp"])
    winner = userRewards["won"]

    kwargs: Dict[str, Union[str, Any]] = dict(
        name=f"{place}. {'🏆' if winner else ''} {formatRewardByMeta(creditsGained, 'credits', userMeta)}:",
        value=f"<@{userID}> checked {systemsChecked}" \
            + f" system{'s' if int(systemsChecked) != 1 else ''}",
        inline=False
    )

    if bounty.RewardsMeta.USER_PRESTIGED & userMeta:
        kwargs["value"] += "\n(user prestiged - credits shared out)"
    else:
        kwargs["value"] += f"\n*{formatRewardByMeta(xpGained, 'xp', userMeta)}*"

    return kwargs


def makeBountyExpiredEmbed(b: bounty.Bounty) -> Embed:
    """Build an embed representing the expiry of a bounty.
    The bounty's expiry time is assumed to be now.

    :param b: The bounty that has expired
    :type b: bounty.Bounty
    :return: An embed detailing the expiry of the bounty
    :rtype: Embed
    """
    e = Embed()
    e.set_author(name="Bounty Expired", icon_url=b.criminal.icon)
    e.description = f"**{b.criminal.name}**\nOut of time! The bounty has expired."
    e.colour = bbData.factionColours[b.faction]
    activeTime = utcnow() - utcfromtimestamp(b.issueTime)
    e.set_footer(text=f"Active time: {lib.timeUtil.td_format_noYM(activeTime)}")
    return e


class GuildChannelType(Enum):
    BountyPlay = "0"
    Announcements = "1"
    Renders = "2"


class GuildChannels(SerializesToType[Dict[str, int]]):
    def __init__(self, bountyPlay: Optional[TextChannel] = None, announcements: Optional[TextChannel] = None, renders: Optional[TextChannel] = None) -> None:
        self.bountyPlay = bountyPlay
        self.announcements = announcements
        self.renders = renders


    def getForType(self, channelType: GuildChannelType) -> Optional[TextChannel]:
        return {GuildChannelType.BountyPlay: self.bountyPlay,
                GuildChannelType.Announcements: self.announcements,
                GuildChannelType.Renders: self.renders}[channelType]


    def setForType(self, channelType: GuildChannelType, channel: Optional[TextChannel]):
        if channelType is GuildChannelType.BountyPlay:
            self.bountyPlay = channel
        elif channelType is GuildChannelType.Announcements:
            self.announcements = channel
        elif channelType is GuildChannelType.Renders:
            self.renders = channel

    
    def keys(self):
        return [
            GuildChannelType.BountyPlay,
            GuildChannelType.Announcements,
            GuildChannelType.Renders
        ]


    def hasChannel(self, channelType: GuildChannelType) -> bool:
        return self.getForType(channelType) is not None


    def serialize(self, **kwargs) -> Dict[str, int]:
        return {k.value: cast(TextChannel, self.getForType(k)).id for k in self.keys() if self.hasChannel(k)}

    
    @classmethod
    def deserialize(cls, data: Dict[str, int], /, dcGuild: Guild, **kwargs):
        new = cls()
        for k in new.keys():
            if k.value in data:
                c = dcGuild.get_channel(cast(int, data[k.value]))
                if isinstance(c, TextChannel):
                    new.setForType(k, c)
        return new


class SerializedBasedGuild(TypedDict):
    alertRoles: NotRequired[Dict[str, int]]
    bountiesDisabled: NotRequired[bool]
    shopsDisabled: NotRequired[bool]
    guildChannels: NotRequired[Dict[str, int]]
    ownedRoleMenus: NotRequired[int]
    commandPrefix: NotRequired[str]


class SerializedBasedGuildWIthBounties(SerializedBasedGuild):
    bountiesDB: NotRequired[SerializedBountyDB]


class SerializedBasedGuildWIthShops(SerializedBasedGuild):
    divisionShops: NotRequired[Dict[str, guildShop.SerializedTechLeveledShop]]


class SerializedBasedGuildWIthBountiesAndShops(SerializedBasedGuildWIthShops, SerializedBasedGuildWIthBounties): pass


SerializedBasedGuildUnion = Union[SerializedBasedGuild, SerializedBasedGuildWIthBounties, SerializedBasedGuildWIthShops, SerializedBasedGuildWIthBountiesAndShops]


class BasedGuild(SerializesToSchema[SerializedBasedGuildUnion]):
    """A class representing a guild in discord, and storing extra bot-specific information about it.

    :var id: The ID of the guild, directly corresponding to a discord guild's ID.
    :vartype id: int
    :var dcGuild: This guild's corresponding discord.Guild object
    :vartype dcGuild: discord.Guild
    :var announceChannel: The discord.channel object for this guild's announcements chanel.
                            None when no announce channel is set for this guild.
    :vartype announceChannel: TextChannel
    :var playChannel: The discord.channel object for this guild's bounty playing chanel.
                        None when no bounty playing channel is set for this guild.
    :vartype playChannel: TextChannel
    :var rendersChannel: The discord.channel which showme ship renders should be limited to. None when no channel is set.
    :vartype rendersChannel: Union[TextChannel, None]
    :var shop: This guild's guildShop object
    :vartype shop: guildShop
    :var alertRoles: A dictionary of user alert IDs to guild role IDs.
    :vartype alertRoles: dict[str, int]
    :var hasBountyBoardChannels: Whether this guild has bounty board channels for each of its divisions or not
    :vartype hasBountyBoardChannel: bool
    :var ownedRoleMenus: The number of ReactionRolePickers present in this guild
    :vartype ownedRoleMenus: int
    :var bounties: This guild's active bounties
    :vartype bounties: BountyDB
    :var bountiesDisabled: Whether or not to disable this guild's bountyDB and bounty spawning
    :vartype bountiesDisabled: bool
    :var shopsDisabled: Whether or not to disable this guild's guildShop and shop refreshing
    :vartype shopsDisabled: bool
    :var hasBountyAlertRoles: True if the guild has alert roles for each of its divisions, False otherwise
    :vartype hasBountyAlertRoles: bool
    """

    def __init__(self, id: int, dcGuild: Guild, bounties: BountyDB, commandPrefix: str = cfg.defaultCommandPrefix,
            guildChannels: Optional[GuildChannels] = None,
            divisionShops: Union[None, Dict[str, guildShop.TechLeveledShop]] = None,
            alertRoles: Dict[str, int] = {}, ownedRoleMenus: int = 0, bountiesDisabled: bool = False,
            shopsDisabled: bool = False):
        """
        :param int id: The ID of the guild, directly corresponding to a discord guild's ID.
        :param discord.Guild dcGuild: This guild's corresponding discord.Guild object
        :param BountyDB bounties: This guild's active bounties
        :param announceChannel: The discord.channel object for this guild's announcements chanel.
                                                None when no announce channel is set for this guild.
        :type announceChannel: Union[TextChannel, None]
        :param playChannel: The discord.channel object for this guild's bounty playing chanel.
                                            None when no bounty playing channel is set for this guild.
        :type playChannel: Union[TextChannel, None]
        :param rendersChannel: The discord.channel which showme ship renders should be limited to. None when no channel is set.
        :type rendersChannel: Union[TextChannel, None]
        :param divisionShops: A dictionary mapping division names to shops. Ignored if shopsDisabled is True
        :type divisionShops: Union[None, Dict[str, guildShop.TechLeveledShop]]
        :param dict[str, int] alertRoles: A dictionary of user alert IDs to guild role IDs.
        :param int ownedRoleMenus: The number of ReactionRolePickers present in this guild
        :param bool bountiesDisabled: Whether or not to disable this guild's bountyDB and bounty spawning
        :param bool shopsDisabled: Whether or not to disable this guild's guildShop and shop refreshing
        :raise TypeError: When given an incompatible argument type
        """

        if dcGuild is None:
            raise lib.exceptions.NoneDCGuildObj("Given dcGuild of type '" + type(dcGuild).__name__ \
                                                + "', expecting discord.Guild")

        self.id = id
        self.dcGuild = dcGuild
        if not commandPrefix:
            raise ValueError("Empty command prefix provided")
        self.commandPrefix = commandPrefix

        if type(id) == float:
            id = int(id)
        elif type(id) != int:
            raise TypeError("id must be int, given " + str(type(id)))

        self.guildChannels = GuildChannels() if guildChannels is None else guildChannels

        self.shopsDisabled = shopsDisabled
        if shopsDisabled:
            self.divisionShops: Union[None, Dict[str, guildShop.TechLeveledShop]] = None
        else:
            if divisionShops is None:
                self.divisionShops = {divName: guildShop.TechLeveledShop(max(cfg.minTechLevel, levels[0]), levels[1]) \
                                        for divName, levels in bountyDivision.divisionNameLevels().items()}
            else:
                self.divisionShops = divisionShops

        self.alertRoles = {}
        for alertID in userAlerts.userAlertsIDsTypes.keys():
            if issubclass(userAlerts.userAlertsIDsTypes[alertID], userAlerts.GuildRoleUserAlert):
                self.alertRoles[alertID] = alertRoles[alertID] if alertID in alertRoles else -1

        self.ownedRoleMenus = ownedRoleMenus
        self.bountiesDB = bounties
        self.bountiesDisabled = bountiesDisabled

        if bountiesDisabled:
            self.hasBountyBoardChannels = False
            self.hasBountyAlertRoles = False
        else:
            try:
                self.hasBountyBoardChannels = self.bountiesDB.divisionForLevel(cfg.minTechLevel).bountyBoardChannel is not None
            except AttributeError:
                self.hasBountyBoardChannels = False

            try:
                self.hasBountyAlertRoles = self.bountiesDB.divisionForLevel(cfg.minTechLevel).alertRoleID != -1
            except AttributeError:
                self.hasBountyAlertRoles = False


    async def makeBountyAlertRoles(self):
        """Create a set of new roles to ping when bounties are created.

        :raise ValueError: If the guild already has new bounty alert roles set, or has bounties disabled
        :raise Forbidden: If the bot does not have role creation permissions
        :raise HTTPException: If creation of any role failed
        :raise RuntimeError: If any roles failed to create for some unexpected reason
        """
        if self.hasBountyAlertRoles:
            raise ValueError("This guild already has bounty alert roles")
        if self.bountiesDisabled:
            raise ValueError("This guild has bounties disabled")
        roleMakers = lib.discordUtil.BasicScheduler()
        divsDone = set()
        async def makeDivRole(div: bountyDivision.BountyDivision):
            divsDone.add(div)
            divName = nameForDivision(div)
            divID = cfg.bountyDivisionNames.index(divName)
            newRole = await self.dcGuild.create_role(name=f"{divName.title()} Bounty Hunter",
                                                    colour=Colour.from_rgb(*cfg.bountyAlertRoleColoursByDivision[divID]),
                                                    reason="Creating new bounty alert roles requested by BB command")
            div.alertRoleID = newRole.id
        
        # Casting here because bountiesDB cannot be None if bountiesDisabled is False
        bountiesDB = cast(BountyDB, self.bountiesDB)
        for div in bountiesDB.divisions.values():
            roleMakers.add(makeDivRole(div))

        await roleMakers.wait()
        exceptions = roleMakers.getExceptions()
        if exceptions:
            for doneDiv in divsDone:
                doneDiv.alertRoleID = -1
            raise list(exceptions.values())[0]
        # Casting here because bountiesDB cannot be None if bountiesDisabled is False
        for div in bountiesDB.divisions.values():
            if div.alertRoleID == -1:
                # Casting here because bountiesDB cannot be None if bountiesDisabled is False
                for doneDiv in bountiesDB.divisions.values():
                    doneDiv.alertRoleID = -1
                raise RuntimeError("An unknown error occurred when creating roles")
        
        self.hasBountyAlertRoles = True


    async def deleteBountyAlertRoles(self):
        """Delete the bounty alert roles from the server.

        :raise ValueError: If the guild does not have new bounty alert roles set
        :raise Forbidden: If the bot does not have role deletion permissions
        :raise HTTPException: If deletion of any role failed
        """
        if not self.hasBountyAlertRoles:
            raise ValueError("This guild does not have bounty alert roles")
        roleRemovers = lib.discordUtil.BasicScheduler()
        async def removeDivRole(div: bountyDivision.BountyDivision):
            if div.alertRoleID != -1:
                tlRole = self.dcGuild.get_role(div.alertRoleID)
                if tlRole is None:
                    await self.dcGuild.fetch_roles()
                tlRole = self.dcGuild.get_role(div.alertRoleID)
                if tlRole is not None:
                    await tlRole.delete(reason="Removing new bounty alert roles requested by BB command")
                div.alertRoleID = -1
        
        # Casting here because bountiesDB cannot be None if bountiesDisabled is False
        for div in cast(BountyDB, self.bountiesDB).divisions.values():
            roleRemovers.add(removeDivRole(div))
        await roleRemovers.wait()
        roleRemovers.raiseExceptions()

        self.hasBountyAlertRoles = False


    async def levelUpSwapRoles(self, dcUser: Member, oldRole: Optional[Role], newRole: Optional[Role],
                                    actionOverride="leveled up") -> List[str]:
        """Remove oldRole from dcUser, and grant newRole.
        If errors occur, they will be printed in the context of dcUser leveling up their bounty Hunting level,
        and sent in channel. If oldRole or newRole are given as None, they will be ignored and no exception raised.

        :param Member dcUser: The user to toggle roles for
        :param Role oldRole: The role to remove, corresponding to dcUser's previous tech level
        :param Role newRole: The role to grant, corresponding to dcUser's new tech level
        :param str actionOverride: The reason for the role change, inserted partially into each message.
                                    (Default "leveled up")
        :returns: A list of errors that occurred
        :rtype: List[str]
        """
        errors = []
        if oldRole is not None:
            try:
                await dcUser.remove_roles(oldRole, reason=f"User {actionOverride} into a new division")
            except Forbidden:
                errors.append("I don't have permission to remove your old division role! Please ensure " \
                                    + "it is beneath the BountyBot role.")
            except HTTPException as e:
                errors.append("Something went wrong when removing your old division role!\n" \
                                    + "The error has been logged.")
                botState.client.logger.log("main", "cmd_notify",
                                    f"{type(e).__name__} occurred when attempting to remove new bounty role " \
                                        + f"{oldRole.name}#{oldRole.id}  from user {dcUser.name}#{dcUser.id}" \
                                        + f" in guild {self.dcGuild.name}#{self.id}.",
                                    category=LogCategory.userAlerts, exception=e)
            except client_exceptions.ClientOSError as e:
                errors.append("A connection error occurred when removing your old division role, " \
                                    + "the error has been logged.")
                botState.client.logger.log("main", "cmd_notify",
                                    f"{type(e).__name__} occurred when attempting to remove new bounty role " \
                                        + f"{oldRole.name}#{oldRole.id}  from user {dcUser.name}#{dcUser.id}" \
                                        + f" in guild {self.dcGuild.name}#{self.id}.",
                                    category=LogCategory.userAlerts, exception=e)
        if newRole is not None:
            try:
                await dcUser.add_roles(newRole, reason=f"User {actionOverride} into a new division")
            except Forbidden:
                errors.append("I don't have permission to grant your new division role! Please ensure " \
                                    + "it is beneath the BountyBot role.")
            except HTTPException as e:
                errors.append("Something went wrong when granting your new division role!\n" \
                                    + "The error has been logged.")
                botState.client.logger.log("main", "cmd_notify",
                                    f"{type(e).__name__} occurred when attempting to grant new bounty role " \
                                        + f"{newRole.name}#{newRole.id}  from user {dcUser.name}#{dcUser.id}" \
                                        + f" in guild {self.dcGuild.name}#{self.id}.",
                                    category=LogCategory.userAlerts, exception=e)
            except client_exceptions.ClientOSError as e:
                errors.append("A connection error occurred when granting your new division role, " \
                                    + "the error has been logged.")
                botState.client.logger.log("main", "cmd_notify",
                                    f"{type(e).__name__} occurred when attempting to grant new bounty role " \
                                        + f"{newRole.name}#{newRole.id}  from user {dcUser.name}#{dcUser.id}" \
                                        + f" in guild {self.dcGuild.name}#{self.id}.",
                                    category=LogCategory.userAlerts, exception=e)
        return errors


    def getChannel(self, channelType: GuildChannelType) -> TextChannel:
        c = self.guildChannels.getForType(channelType)
        if c is None:
            raise ValueError("This guild has no announce channel set")
        return c


    def hasChannel(self, channelType: GuildChannelType) -> bool:
        return self.guildChannels.getForType(channelType) is not None


    def setChannel(self, channelType: GuildChannelType, channel: Optional[TextChannel]):
        self.guildChannels.setForType(channelType, channel)


    def removeChannel(self, channelType: GuildChannelType):
        self.guildChannels.setForType(channelType, None)


    def getAnnounceChannel(self) -> TextChannel:
        """Get the discord channel object of the guild's announcements channel.

        :return: the discord.channel of the guild's announcements channel
        :rtype: TextChannel
        :raise ValueError: If this guild does not have an announcements channel
        """
        if not self.hasAnnounceChannel():
            raise ValueError("This guild has no announce channel set")
        return cast(TextChannel, self.guildChannels.announcements)


    def getPlayChannel(self) -> TextChannel:
        """Get the discord channel object of the guild's bounty playing channel.

        :return: the discord channel object of the guild's bounty playing channel
        :raise ValueError: If this guild does not have a play channel
        :rtype: TextChannel
        """
        if not self.hasPlayChannel():
            raise ValueError("This guild has no play channel set")
        return cast(TextChannel, self.guildChannels.bountyPlay)


    def setAnnounceChannel(self, announceChannel: TextChannel):
        """Set the discord channel object of the guild's announcements channel.

        :param TextChannel announceChannel: The discord channel object of the guild's new announcements channel
        """
        self.guildChannels.announcements = announceChannel


    def setPlayChannel(self, playChannel: TextChannel):
        """Set the discord channel of the guild's bounty playing channel.

        :param TextChannel playChannel: The discord channel object of the guild's new bounty playing channel
        """
        self.guildChannels.bountyPlay = playChannel


    def hasAnnounceChannel(self) -> bool:
        """Whether or not this guild has an announcements channel

        :return: True if this guild has a announcements channel, False otherwise
        :rtype bool:
        """
        return self.guildChannels.hasChannel(GuildChannelType.Announcements)


    def hasPlayChannel(self) -> bool:
        """Whether or not this guild has a play channel

        :return: True if this guild has a play channel, False otherwise
        :rtype bool:
        """
        return self.guildChannels.bountyPlay is not None


    def removePlayChannel(self):
        """Remove and deactivate this guild's announcements channel.

        :raise ValueError: If this guild does not have a play channel
        """
        if not self.hasPlayChannel():
            raise ValueError("Attempted to remove play channel on a BasedGuild that has no playChannel")
        self.guildChannels.bountyPlay = None


    def removeAnnounceChannel(self):
        """Remove and deactivate this guild's play channel.

        :raise ValueError: If this guild does not have an announcements channel
        """
        if not self.hasAnnounceChannel():
            raise ValueError("Attempted to remove announce channel on a BasedGuild that has no announceChannel")
        self.guildChannels.announcements = None


    def setRendersChannel(self, rendersChannel: TextChannel):
        """Set the discord channel of the guild's autoskin renders channel.

        :param TextChannel rendersChannel: The discord channel object of the guild's autoskin renders channel
        """
        self.guildChannels.renders = rendersChannel


    def getRendersChannel(self) -> TextChannel:
        """Get the discord channel of the guild's autoskin renders channel.
        """
        if not self.hasRendersChannel():
            raise ValueError("Attempted to get renders channel on a BasedGuild that has no renders channel")
        return cast(TextChannel, self.guildChannels.renders)


    def hasRendersChannel(self) -> bool:
        """Whether or not this guild has a renders channel

        :return: True if this guild has a renders channel, False otherwise
        :rtype bool:
        """
        return self.guildChannels.renders is not None


    def removeRendersChannel(self):
        """Remove and deactivate this guild's announcements channel.

        :raise ValueError: If this guild does not have a renders channel
        """
        if not self.hasRendersChannel():
            raise ValueError("Attempted to remove renders channel on a BasedGuild that has no rendersChannel")
        self.guildChannels.renders = None


    def getUserAlertRoleID(self, alertID: str) -> int:
        """Get the ID of this guild's alerts role for the given alert ID.

        :param str alertID: The alert ID for which the role ID should be fetched
        :return: The ID of the discord role that this guild mentions for the given alert ID.
        :rtype: int
        """
        return self.alertRoles[alertID]


    def setUserAlertRoleID(self, alertID: str, roleID: int):
        """Set the ID of this guild's alerts role for the given alert ID.

        :param str alertID: The alert ID for which the role ID should be set
        :param int roleID: The ID of the role which this guild should mention when alerting alertID
        """
        self.alertRoles[alertID] = roleID


    def removeUserAlertRoleID(self, alertID: str):
        """Remove the stored role and deactivate alerts for the given alertID

        :param str alertID: The alert ID for which the role ID should be removed
        """
        self.alertRoles[alertID] = -1


    def hasUserAlertRoleID(self, alertID: str) -> bool:
        """Decide whether or not this guild has a role set for the given alert ID.

        :param str alertID: The alert ID for which the role existence should be tested
        :return: True if this guild has a role set to mention for alertID
        :rtype: bool
        :raise KeyError: If given an unrecognised alertID
        """
        if alertID in self.alertRoles:
            return self.alertRoles[alertID] != -1
        raise KeyError("Unknown GuildRoleUserAlert ID: " + alertID)


    async def makeBountyBoardChannelMessage(self, bounty: bounty.Bounty, msg: str = "", embed: Optional[Embed] = None) -> Message:
        """Create a new bountyBoardChannel listing for the given bounty, in the given guild.
        guild must own a bountyBoardChannel.

        :param bounty.Bounty bounty: The bounty for which to create a listing
        :param str msg: The text to display in the listing message content (Default "")
        :param discord.Embed embed: The embed to display in the listing message - this will be removed immediately in place
                                    of the embed generated during bountyBoardChannel.updateBountyMessage,
                                    so is only really useful in case updateBountyMessage fails. (Default None)
        :return: The new discord message containing the BBC listing
        :rtype: discord.Message
        :raise ValueError: If guild does not own a bountyBoardChannel
        """
        if not self.hasBountyBoardChannels:
            raise ValueError("The requested BasedGuild has no bountyBoardChannel")
        
        # Casting here because division.bountyBoardChannel is guaranteed for every division, if the guild has hasBountyBoardChannels as True
        bbc = cast(bountyBoardChannel.BountyBoardChannel, bounty.division.bountyBoardChannel)
        bountyListing = await bbc.channel.send(msg, embed=embed if embed is not None else MISSING)
        await bbc.addBounty(bounty, bountyListing)
        await bbc.updateBountyMessage(bounty)
        return bountyListing


    async def removeBountyBoardChannelMessage(self, bounty: bounty.Bounty):
        """Remove guild's bountyBoardChannel listing for bounty.

        :param bounty bounty: The bounty whose BBC listing should be removed
        :raise ValueError: If guild does not own a BBC
        :raise KeyError: If the guild's BBC does not have a listing for bounty
        """
        if not self.hasBountyBoardChannels:
            raise ValueError("The requested BasedGuild has no bountyBoardChannel")

        # Casting here because division.bountyBoardChannel is guaranteed for every division, if the guild has hasBountyBoardChannels as True
        bbc = cast(bountyBoardChannel.BountyBoardChannel, bounty.division.bountyBoardChannel)
        if bbc.hasMessageForBounty(bounty):
            try:
                await bbc.getMessageForBounty(bounty).delete()
            except Forbidden:
                botState.client.logger.log("Main", "rmBBCMsg",
                                    "Forbidden exception thrown when removing bounty listing message for criminal: " \
                                    + bounty.criminal.name, category=LogCategory.bountyBoards, eventType="RM_LISTING-FORBIDDENERR")
            except NotFound:
                botState.client.logger.log("Main", "rmBBCMsg",
                                    "Bounty listing message no longer exists, BBC entry removed: " + bounty.criminal.name,
                                    category=LogCategory.bountyBoards, eventType="RM_LISTING-NOT_FOUND")
            except HTTPException:
                botState.client.logger.log("Main", "rmBBCMsg",
                                    "HTTPException thrown when removing bounty listing message for criminal: " \
                                    + bounty.criminal.name, category=LogCategory.bountyBoards, eventType="RM_LISTING-HTTPERR")
            await bbc.removeBounty(bounty)
        else:
            raise KeyError("The requested BasedGuild (" + str(self.id) \
                            + ") does not have a bountyBoardChannel listing for the given bounty: " + bounty.criminal.name)


    async def updateBountyBoardChannel(self, bounty: bounty.Bounty, bountyComplete: bool = False):
        """Update the BBC listing for the given bounty in the given server.

        :param bounty bounty: The bounty whose listings should be updated
        :param bool bountyComplete: Whether or not the bounty has now been completed.
                                    When True, bounty listings will be removed rather than updated. (Default False)
        """
        if self.hasBountyBoardChannels:
            # Casting here because division.bountyBoardChannel is guaranteed for every division, if the guild has hasBountyBoardChannels as True
            bbc = cast(bountyBoardChannel.BountyBoardChannel, bounty.division.bountyBoardChannel)
            if bountyComplete:
                if bbc.hasMessageForBounty(bounty):
                    await self.removeBountyBoardChannelMessage(bounty)
            else:
                if not bbc.hasMessageForBounty(bounty):
                    await self.makeBountyBoardChannelMessage(bounty, "A new bounty is now available from **" \
                                                                    + bounty.faction.title() + "** central command:")
                else:
                    await bbc.updateBountyMessage(bounty)


    async def announceNewBounty(self, newBounty: bounty.Bounty, isRespawn: bool = False):
        """Announce the creation of a new bounty to this guild's announceChannel, if it has one

        :param bounty newBounty: the bounty to announce
        """
        if newBounty.activeShip is None:
            raise ValueError(f"Bounty does not have a ship: {newBounty.criminal.name}")
        print("Difficulty", newBounty.techLevel, "New bounty with value:", newBounty.activeShip.getValue())
        # Create the announcement embed
        bountyEmbed = lib.discordUtil.makeEmbed(titleTxt=lib.discordUtil.criminalNameOrDiscrim(newBounty.criminal),
                                                col=bbData.factionColours[newBounty.faction],
                                                thumb=newBounty.criminal.icon, footerTxt=newBounty.faction.title())
        if isRespawn:
            bountyEmbed.description = f"{cfg.defaultEmojis.bountyRespawn.sendable} __Bounty Respawned__"
            msg = f"A bounty has reappeared onto the **{newBounty.faction.title()}** bounty board:"
        else:
            bountyEmbed.description = f"{cfg.defaultEmojis.newBounty.sendable} __New Bounty Available__"
            msg = f"A new bounty is now available from **{newBounty.faction.title()}** central command:"
            
        bountyEmbed.add_field(name="**Reward Pool:**", value=str(newBounty.reward) + " Credits")
        bountyEmbed.add_field(name="**Difficulty:**", value=str(newBounty.techLevel))
        bountyEmbed.add_field(name="**See the culprit's loadout with:**",
                                value="`" + self.commandPrefix + "loadout criminal " + newBounty.criminal.name + "`")
        bountyEmbed.add_field(name="**Route:**", value=", ".join(newBounty.route), inline=False)
        bountyEmbed.add_field(name="Bounty ends:", value=f"<t:{int(newBounty.endTime)}:R>")

        if self.hasBountyBoardChannels:
            # Casting here because division.bountyBoardChannel is guaranteed for every division, if the guild has hasBountyBoardChannels as True
            bbc = cast(bountyBoardChannel.BountyBoardChannel, newBounty.division.bountyBoardChannel)
            try:
                if self.hasBountyAlertRoles:
                    msg = f"<@&{newBounty.division.alertRoleID}> {msg}"
                # announce to the given channel
                bountyListing = await bbc.channel.send(msg, embed=bountyEmbed)
                await bbc.addBounty(newBounty, bountyListing)
                await bbc.updateBountyMessage(newBounty)
                return bountyListing

            except Forbidden:
                dcGuild = botState.client.get_guild(self.id)
                guildName = "<unknown>" if dcGuild is None else dcGuild.name
                botState.client.logger.log("BasedGuild", "anncBnty",
                                    "Failed to post BBCh listing to guild " + guildName + "#" \
                                    + str(self.id) + " in channel " + bbc.channel.name + "#" \
                                    + str(bbc.channel.id), category=LogCategory.bountyBoards,
                                    eventType="BBC_NW_FRBDN")

        # If the guild has an announceChannel
        elif self.hasAnnounceChannel():
            # ensure the announceChannel is valid
            currentChannel = self.getAnnounceChannel()
            if currentChannel is not None:
                try:
                    if self.hasBountyAlertRoles:
                        # announce to the given channel
                        await currentChannel.send(f"<@&{newBounty.division.alertRoleID}> {msg}",
                                                    embed=bountyEmbed)
                    else:
                        await currentChannel.send(msg, embed=bountyEmbed)
                except Forbidden:
                    dcGuild = botState.client.get_guild(self.id)
                    guildName = "<unknown>" if dcGuild is None else dcGuild.name
                    botState.client.logger.log("BasedGuild", "anncBnty",
                                        "Failed to post announce-channel bounty listing to guild " \
                                        + guildName + "#" + str(self.id) + " in channel " \
                                        + currentChannel.name + "#" + str(currentChannel.id), eventType="ANNCCH_SND_FRBDN")

            # TODO: may wish to add handling for invalid announceChannels - e.g remove them from the BasedGuild object


    async def spawnAndAnnounceBounty(self, newBountyData, isRespawn: bool = False):
        """Generate a new bounty, either at random or by the given bbBountyConfig, spawn it,
        and announce it if this guild has an appropriate channel selected.
        """
        if self.bountiesDisabled:
            botState.client.logger.log("basedGuild", "spwnAndAnncBty",
                                "Attempted to spawn a bounty into a guild where bounties are disabled: " \
                                    + (self.dcGuild.name if self.dcGuild is not None else "") + "#" + str(self.id),
                                eventType="BTYS_DISABLED")
            return
        # ensure a new bounty can be created
        # Casting here because bountiesDB cannot be None if bountiesDisabled is False
        bountiesDB = cast(BountyDB, self.bountiesDB)

        if isRespawn or bountiesDB.canMakeBounty():
            newBounty: bounty.Bounty = newBountyData["newBounty"]
            config: bountyConfig.BountyConfig = newBountyData["newConfig"].copy() if "newConfig" in newBountyData else bountyConfig.BountyConfig()

            if newBounty is not None:
                div = newBounty.division
                if config.techLevel == -1:
                    config.techLevel = newBounty.techLevel
            elif config.techLevel != -1:
                div = bountiesDB.divisionForLevel(config.techLevel)
            else:
                div: "bountyDivision.BountyDivision" = random.choice(list(bountiesDB.divisions.values()))
                while div.isFull():
                    div = random.choice(list(bountiesDB.divisions.values()))
                config.techLevel = div.pickNewTL()

            if newBounty is None:
                newBounty = bounty.Bounty(division=div, config=config)
            else:
                # If removed, uncomment this line from bounty._respawn
                if bountiesDB.escapedCriminalExists(newBounty.criminal):
                    bountiesDB.removeEscapedCriminal(newBounty.criminal)

                if config is not None:
                    newConfig = config.copy()
                    if not newConfig.generated:
                        newConfig.generate(div)
                    newBounty.route = newConfig.route
                    newBounty.answer = newConfig.answer
                    newBounty.checked = newConfig.checked
                    newBounty.reward = newConfig.reward
                    newBounty.issueTime = newConfig.issueTime
                    newBounty.endTime = newConfig.endTime

            # activate and announce the bounty
            bountiesDB.addBounty(newBounty, isRespawn=isRespawn)
            await self.announceNewBounty(newBounty, isRespawn=isRespawn)
        
        else:
            raise OverflowError("Attempted to spawnAndAnnounceBounty when no more space is available for bounties " \
                                + "in the bountiesDB")


    async def announceBountyWon(self, bounty: bounty.Bounty, rewards: Dict[int, Dict[str, Union[int, bool]]],
                                winningUser: Union[Member, User], rewardsMeta: Dict[int, bounty.RewardsMeta],
                                leveledUp: Dict["basedUser.BasedUser", List[GameItem]]):
        """Announce the completion of a bounty
        Messages will be sent to the playChannel if one is set

        :param bounty bounty: the bounty to announce
        :param dict rewards: the rewards dictionary as defined by bounty.calculateRewards
        :param discord.Member winningUser: the guild member that won the bounty
        :param rewardsMeta: mapping from user ID to binary flags for special rewards handling (bounty.RewardsMeta)
        :type rewardsMeta: Dict[int, int]
        :param divUpUnlockedUserIDs: IDs for each user that unlocked the next division with this bounty.
        :type divUpUnlockedUserIDs: List[int]
        :param prestigeUnlockedUserIDs: IDs for each user that unlocked prestiging with this bounty.
        :type prestigeUnlockedUserIDs: List[int]
        """
        if self.dcGuild is None:
            dcGuild = botState.client.get_guild(self.id)
            guildName = "<unknown>" if dcGuild is None else dcGuild.name
            botState.client.logger.log("Main", "AnncBtyWn",
                                "None dcGuild received when posting bounty won to guild " \
                                + guildName + "#" + str(self.id) + " in channel ?#" \
                                + str(self.getPlayChannel().id), eventType="DCGUILD_NONE")
            return

        if self.bountiesDB is None or not self.hasPlayChannel(): return
        
        # Create the announcement embed
        rewardsEmbed = lib.discordUtil.makeEmbed(titleTxt="Bounty Complete!",
                                                authorName=lib.discordUtil.criminalNameOrDiscrim(bounty.criminal) \
                                                + " Arrested", icon=bounty.criminal.icon,
                                                col=bbData.factionColours[bounty.faction],
                                                desc="`Suspect located in '" + bounty.answer + "'`")

        # Add the winning user to the embed
        rewardsEmbed.add_field(**bountyResultsFieldKwargs(1, winningUser.id, rewards[winningUser.id],
                                                            rewardsMeta[winningUser.id]))

        # The index of the current user in the embed
        place = 2
        # Loop over all non-winning users in the rewards dictionary
        for userID, userRewards in rewards.items():
            if not userRewards["won"]:
                rewardsEmbed.add_field(**bountyResultsFieldKwargs(place, userID, userRewards, rewardsMeta[userID]))
                place += 1

        levelUpsStr = ""
        division: Optional[bountyDivision.BountyDivision] = None
        divUpUnlocked: List["basedUser.BasedUser"] = []

        for user, userRewards in leveledUp.items():
            level = gameMaths.calculateUserBountyHuntingLevel(user.bountyHuntingXP)
            levelUpsStr += "\n:arrow_up: **Level Up!**\n" \
                        + f"<@{user.id}> reached **Bounty Hunter Level {level}!** :partying_face:"

            if len(userRewards) == 1:
                levelUpsStr += f"\nYou got a **{userRewards[0].name}**."
            elif len(userRewards) != 0:
                levelUpsStr += "\nYou got:\n- " + "\n".join(f"- a **{i.name}**" for i in userRewards)
            
            division = division or self.bountiesDB.divisionForLevel(level)
            if level == division.maxLevel:
                divUpUnlocked.append(user)

        if divUpUnlocked:
            if len(divUpUnlocked) > 1:
                levelUpsStr += ", ".join(f"<@{i.id}>" for i in divUpUnlocked[:-1]) + f" and <@{divUpUnlocked[-1].id}>"
            else:
                levelUpsStr += f"<@{divUpUnlocked[0].id}>"
                
            if cast(bountyDivision.BountyDivision, division).maxLevel == cfg.maxTechLevel:
                levelUpsStr += f" unlocked prestiging! use the `{self.commandPrefix}prestige` command to " \
                                + "gain special rewards and start a new run!"
            else:
                levelUpsStr += f" unlocked the next division! use the `/div-up` command to " \
                                + "move up, and take on tougher bounties!\n"

        # Send the announcement to the guild's playChannel
        await self.getPlayChannel().send(":trophy: **You win!**\n**" + winningUser.display_name \
                                            + "** located and EMP'd **" + bounty.criminal.name \
                                            + "**, who has been arrested by local security forces. :chains:\n\n" \
                                            + levelUpsStr,
                                            embed=rewardsEmbed)


    async def announceBountyExpired(self, b: bounty.Bounty):
        """Announce the expiry of a bounty. Does not update the bountyboard channel if one exists.

        :param b: The bounty that has expired
        :type b: bounty.Bounty
        """
        if self.dcGuild is not None:
            if self.hasPlayChannel():
                await self.getPlayChannel().send(embed=makeBountyExpiredEmbed(b))
        else:
            dcGuild = botState.client.get_guild(self.id)
            guildName = "<unknown>" if dcGuild is None else dcGuild.name
            botState.client.logger.log("Main", "AnncBtyWn",
                                "None dcGuild received when posting bounty expiry to guild " \
                                + guildName + "#" + str(self.id) + " in channel ?#" \
                                + str(self.getPlayChannel().id), eventType="DCGUILD_NONE")


    def enableBounties(self):
        """Enable bounties for this guild.
        Sets up a new bounties DB and bounty spawning TimedTask.

        :raise ValueError: If bounties are already enabled in this guild
        """
        if not self.bountiesDisabled:
            raise ValueError("Bounties are already enabled in this guild")

        self.bountiesDB = BountyDB(self)
        self.bountiesDisabled = False


    async def disableBounties(self):
        """Disable bounties for this guild.
        Removes any bountyboard if one is present, and removes the guild's bounties DB and bounty spawning TimedTask.

        :raise ValueError: If bounties are already disabled in this guild
        """
        if self.bountiesDisabled:
            raise ValueError("Bounties are already disabled in this guild")

        if self.hasBountyBoardChannels:
            # Casting here because guild.bountiesDB can be None, but this is checked for in the hasBountyBoardChannels check above
            for div in cast(BountyDB, self.bountiesDB).divisions.values():
                div.removeBountyBoardChannel()
            self.hasBountyBoardChannels = False
        self.bountiesDisabled = True
        self.bountiesDB = None

        if self.hasBountyAlertRoles:
            await self.deleteBountyAlertRoles()


    def enableShops(self):
        """Enable shops for this guild.
        Creates a new guildShop object for each division.

        :raise ValueError: If shops are already enabled in this guild
        """
        if not self.shopsDisabled:
            raise ValueError("Shop are already enabled in this guild")

        self.divisionShops = {divName: guildShop.TechLeveledShop(max(cfg.minTechLevel, levels[0]), levels[1], noRefresh=True) \
                                for divName, levels in bountyDivision.divisionNameLevels().items()}
        self.shopsDisabled = False


    def disableShops(self):
        """Disable shops for this guild.
        Removes the guild's guildShop objects.

        :raise ValueError: If shops are already disabled in this guild
        """
        if self.shopsDisabled:
            raise ValueError("Shop are already disabled in this guild")

        self.divisionShops = None
        self.shopsDisabled = True


    async def announceNewShopStock(self, newLevel: Optional[int] = None):
        """Announce to the guild's play channel that this guild's shop stock has been refreshed.
        If no playChannel has been set, does nothing.
        If newLevel is None, announce that all of the guild's shops have been refreshed.
        Otherwise, just announce that the shop owning that level has refreshed.

        :raise ValueError: If this guild's shop is disabled
        """
        if self.shopsDisabled:
            raise ValueError("Attempted to announceNewShopStock on a guild where shop is disabled")
        if self.hasPlayChannel():
            playCh = self.getPlayChannel()
            msg = "The shop stock has been refreshed!"
            msgEmbed = Embed()
            if newLevel is None:
                for divName, shop in cast(Dict[str, guildShop.TechLeveledShop], self.divisionShops).items():
                    msgEmbed.add_field(name=divName, value=f"Now at level **{shop.currentTechLevel}**")
            else:
                msgEmbed.add_field(name=divisionNameForLevel(newLevel), value=f"Now at level **{newLevel}**")
            try:
                if self.hasUserAlertRoleID("shop_refresh"):
                    # announce to the given channel
                    await playCh.send(":arrows_counterclockwise: <@&" \
                                            + str(self.getUserAlertRoleID("shop_refresh")) + "> " + msg,
                                        embed=msgEmbed)
                else:
                    await playCh.send(":arrows_counterclockwise: " + msg,
                                        embed=msgEmbed)
            except Forbidden:
                botState.client.logger.log("Main", "anncNwShp",
                                    "Failed to post shop stock announcement to " + self.dcGuild.name + "#" + str(self.id) \
                                    + " in channel " + playCh.name + "#" + str(playCh.id), category=LogCategory.shop,
                                    eventType="PLCH_NONE")


    def serialize(self, **kwargs) -> SerializedBasedGuildUnion:
        """Serialize this BasedGuild into dictionary format to be saved to file.

        :return: A dictionary containing all information needed to reconstruct this BasedGuild
        :rtype: dict
        """
        data: SerializedBasedGuildUnion = {
            "alertRoles":       self.alertRoles,
            "bountiesDisabled": self.bountiesDisabled,
            "shopsDisabled":     self.shopsDisabled
        }

        guildChannels = self.guildChannels.serialize()
        if guildChannels != {}:
            data["guildChannels"] = guildChannels

        if self.ownedRoleMenus:
            data["ownedRoleMenus"] = self.ownedRoleMenus

        if self.commandPrefix != cfg.defaultCommandPrefix:
            data["commandPrefix"] = self.commandPrefix

        if not self.bountiesDisabled:
            # Casting here because we know the guild has bounties enabled
            data = cast(SerializedBasedGuildWIthBounties, data)
            # Casting here because bountiesDB cannot be None if bountiesDisabled is False
            data["bountiesDB"] = cast(BountyDB, self.bountiesDB).serialize(**kwargs)

        if not self.shopsDisabled:
            # Casting here because we know the guild has shops enabled
            data = cast(SerializedBasedGuildWIthShops, data)
            # Casting here because shop existence is checked with the shopsDisabled check
            data["divisionShops"] = {k: v.serialize(**kwargs) for k, v in cast(Dict[str, guildShop.TechLeveledShop], self.divisionShops).items()}

        return data


    @classmethod
    def deserialize(cls, guildDict: SerializedBasedGuildUnion, dbReload=False, *, guildID: int, **kwargs) -> BasedGuild:
        """Factory function constructing a new BasedGuild object from the information
        in the provided guildDict - the opposite of BasedGuild.serialize

        :param int guildID: The discord ID of the guild
        :param dict guildDict: A dictionary containing all information required to build the BasedGuild object
        :param bool dbReload: Whether or not this guild is being created during the initial database loading phase of
                                bountybot. This is used to toggle name checking in bounty contruction.
        :return: A BasedGuild according to the information in guildDict
        :rtype: BasedGuild
        """
        if guildID is None:
            raise NameError("Required kwarg missing: guildID")

        dcGuild = botState.client.get_guild(guildID)
        if dcGuild is None:
            raise lib.exceptions.NoneDCGuildObj("Could not get guild object for id " + str(guildID))

        if "guildChannels" in guildDict:
            guildChannels = GuildChannels.deserialize(cast(dict, guildDict["guildChannels"]), dcGuild=dcGuild)
        else:
            guildChannels = GuildChannels()
            # Ignoring here because I'm porting the legacy serialized guild schema
            if guildDict.get("announceChannel", -1) != -1:
                c = dcGuild.get_channel(cast(int, guildDict["announceChannel"])) # type: ignore[reportGeneralTypeIssues]
                if isinstance(c, TextChannel):
                    guildChannels.announcements = c
            if guildDict.get("playChannel", -1) != -1:
                c = dcGuild.get_channel(cast(int, guildDict["playChannel"])) # type: ignore[reportGeneralTypeIssues]
                if isinstance(c, TextChannel):
                    guildChannels.bountyPlay = c
            if guildDict.get("rendersChannel", -1) != -1:
                c = dcGuild.get_channel(cast(int, guildDict["rendersChannel"])) # type: ignore[reportGeneralTypeIssues]
                if isinstance(c, TextChannel):
                    guildChannels.renders = c

        bountiesDisabled = guildDict.get("bountiesDisabled", False)

        shopsDisabled = guildDict.get("shopsDisabled", guildDict.get("shopDisabled", False))

        if shopsDisabled:
            divisionShops = None
        else:
            # For legacy savedata, just generate new shops
            if "divisionShops" in guildDict:
                # Casting here because we know the guild has shops
                guildDict = cast(SerializedBasedGuildWIthShops, guildDict)
                # Casting here because pyright doesn't know the structure of a serialized BasedGuild
                divisionShops = {k: guildShop.TechLeveledShop.deserialize(v) for k, v in guildDict.get("divisionShops", {}).items()}
            else:
                divisionShops = {divName: guildShop.TechLeveledShop(max(cfg.minTechLevel, levels[0]), levels[1]) \
                                    for divName, levels in bountyDivision.divisionNameLevels().items()}

        newGuild = BasedGuild(**cls._makeDefaults(guildDict, ("bountiesDB","bountyBoardChannel","shop","shopDisabled","announceChannel","playChannel","rendersChannel"),
                                                    id=guildID, dcGuild=dcGuild, bounties=None,
                                                    guildChannels=guildChannels,
                                                    divisionShops=divisionShops, shopsDisabled=shopsDisabled))

        if not bountiesDisabled:
            if "bountiesDB" in guildDict:
                # Casting here because we know the guild has bounties
                guildDict = cast(SerializedBasedGuildWIthBounties, guildDict)
                # Ignoring here because I just checked that the key is present
                bountiesDB = BountyDB.deserialize(guildDict["bountiesDB"], # type: ignore[reportTypedDictNotRequiredAccess]
                                                    dbReload=dbReload, owningBasedGuild=newGuild)
            else:
                bountiesDB = BountyDB(newGuild)
            newGuild.bountiesDB = bountiesDB
            newGuild.hasBountyBoardChannels = next(i for i in newGuild.bountiesDB.divisions.values()).bountyBoardChannel \
                                                is not None
            newGuild.hasBountyAlertRoles = next(i for i in newGuild.bountiesDB.divisions.values()).alertRoleID != -1

        return newGuild
