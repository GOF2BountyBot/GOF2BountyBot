from __future__ import annotations
from discord.member import Member
from . import reactionMenu, expiryFunctions
from .. import botState
from ..lib.emojis import BasedEmoji
from ..lib.timeUtil import utcfromtimestamp
from ..baseClasses.serializable import SerializesToSchema
from discord import Colour, Guild, Role, Message, User
from ..scheduling import timedTask
from typing import Optional, Tuple, Union, Dict, cast
from typing_extensions import TypedDict


async def giveRole(args: Tuple[Guild, Role, int], reactingUser: Union[User, Member]):
    """Grant the given user the role described in args.
    if reactingUser already has the requested role, do nothing.

    :param dict args: A list containing the guild to grant the role in, the role to grant, and finally the message ID that
                        triggered the role addition.
    :param discord.User reactingUser: The user to grant the role to (Default None)
    """
    dcGuild, role, msgID = args
    dcMember = dcGuild.get_member(reactingUser.id)
    if dcMember is None:
        return

    if role not in dcMember.roles:
        await dcMember.add_roles(role, reason="User requested role toggle via BB reaction menu " + str(msgID))


async def removeRole(args: Tuple[Guild, Role, int], reactingUser: Union[User, Member]):
    """remove the role described in args from the given user.
    if reactingUser already lacks the requested role, do nothing.

    :param dict args: A list containing the guild to remove the role in, the role to grant, and finally the message ID that
                        triggered the role addition.
    :param discord.User reactingUser: The user to remove the role from (Default None)
    """
    dcGuild, role, msgID = args
    dcMember = dcGuild.get_member(reactingUser.id)
    if dcMember is None:
        return

    if role in dcMember.roles:
        await dcMember.remove_roles(role, reason="User requested role toggle via BB reaction menu " + str(msgID))


async def markExpiredRoleMenu(menuID: int):
    """Decrement the owning bbGuild's role menus counter, and call reactionMenu.markExpiredMenu.

    :param int menuID: The message ID of the menu to expire
    """
    menu = botState.client.reactionMenusDB[menuID]
    if menu.msg.guild is not None:
        if botState.client.guildsDB.idExists(menu.msg.guild.id):
            botState.client.guildsDB.getGuild(menu.msg.guild.id).ownedRoleMenus -= 1
    await expiryFunctions.markExpiredMenu(menuID)


class SerializedReactionRolePickerOption(TypedDict):
    role: int


class ReactionRolePickerOption(reactionMenu.ReactionMenuOption, SerializesToSchema[SerializedReactionRolePickerOption]):
    """A reaction menu option that stores a role, granting the reacting user the role when added, and removing the role when
    the reaction is removed.

    :var role: The role to toggle on reactions
    :vartype role: discord.Role
    """

    def __init__(self, emoji: BasedEmoji, role: Role, menu: "ReactionRolePicker"):
        self.role = role
        super(ReactionRolePickerOption, self).__init__(self.role.name, emoji, addFunc=giveRole,
                                                        addArgs=(menu.dcGuild, self.role, menu.msg.id),
                                                        removeFunc=removeRole,
                                                        removeArgs=(menu.dcGuild,
                                                        self.role, menu.msg.id))


    def serialize(self, **kwargs) -> SerializedReactionRolePickerOption:
        """Serialize the option into dictionary format for saving.
        Since reaction menu options are saved alongside their emojis, this dictionary need not contain the option emoji.

        :return: A dictionary containing all information needed to reconstruct this menu option
        :rtype: dict
        """
        # baseDict = super(ReactionRolePickerOption, self).serialize(**kwargs)
        # baseDict["role"] = self.role.id

        # return baseDict

        return {"role": self.role.id}


class SerializedReactionRolePicker(reactionMenu.SerializedReactionMenu):
    guild: int


@reactionMenu.saveableMenu
class ReactionRolePicker(reactionMenu.ReactionMenu[ReactionRolePickerOption, SerializedReactionRolePickerOption], SerializesToSchema[SerializedReactionRolePicker]):
    """A reaction menu that grants and removes roles when interacted with.
    TODO: replace dcGuild param with extracting msg.guild
    """

    def __init__(self, msg: Message, reactionRoles: Dict[BasedEmoji, Role], dcGuild: Guild,
            titleTxt: str = "", desc: str = "", col: Colour = Colour.blue(), timeout: Optional[timedTask.TimedTask] = None,
            img: str = "", thumb: str = "", icon: str = "", authorName: str = "",
            targetMember: Optional[Member] = None, targetRole: Optional[Role] = None):
        # TODO: Stop taking dcGuild, and instead extract dcGuild from msg.guild
        """
        :param discord.Message msg: the message where this menu is embedded
        :param reactionRoles: A dictionary where keys are emojis and values are the roles to grant/remove when adding/removing
                                the emoji
        :type reactionRoles: dict[BasedEmoji, discord.Role]
        :param discord.Guild dcGuild: The guild where this menu is contained TODO: Remove and replace with extracting msg.guild
        :param str titleTxt: The content of the embed title (Default "**Role Menu**")
        :param str desc: he content of the embed description; appears at the top below the title
                            (Default "React for your desired role!")
        :param discord.Colour col: The colour of the embed's side strip (Default None)
        :param str img: URL to a large icon appearing as the content of the embed, left aligned like a field (Default "")
        :param str thumb: URL to a larger image appearing to the right of the title (Default "")
        :param str icon: URL to a smaller image to the left of authorName. AuthorName is required for this to be displayed.
                            (Default "")
        :param str authorName: Secondary, smaller title for the embed (Default "")
        :param TimedTask timeout: The TimedTask responsible for expiring this menu (Default None)
        :param discord.Member targetMember: The only discord.Member that is able to interact with this menu.
                                            All other reactions are ignored (Default None)
        :param discord.Role targetRole: In order to interact with this menu, users must possess this role.
                                        All other reactions are ignored (Default None)
        """
        self.dcGuild = dcGuild
        self.msg = msg
        roleOptions = {}
        for reaction in reactionRoles:
            roleOptions[reaction] = ReactionRolePickerOption(reaction, reactionRoles[reaction], self)

        if titleTxt == "":
            titleTxt = "**Role Menu**"
        if desc == "":
            desc = "React for your desired role!"

        super(ReactionRolePicker, self).__init__(msg, options=roleOptions, titleTxt=titleTxt, desc=desc, col=col,
                                                    img=img, thumb=thumb, icon=icon,
                                                    authorName=authorName, timeout=timeout, targetMember=targetMember,
                                                    targetRole=targetRole)


    def serialize(self, **kwargs) -> SerializedReactionRolePicker:
        """Serialize this menu to dictionary format for saving to file.

        :return: A dictionary containing all information needed to reconstruct this menu object
        :rtype: dict
        """
        # TODO: Remove this method. The guild is already saved in ReactionMenu.serialize
        # Casting here because guild is required
        baseDict = cast(SerializedReactionRolePicker, super().serialize(**kwargs))
        baseDict["guild"] = self.dcGuild.id
        return baseDict


    @classmethod
    def deserialize(cls, rmDict: SerializedReactionRolePicker, **kwargs) -> ReactionRolePicker:
        """Reconstruct a ReactionRolePicker from its dictionary-serialized representation.

        :param dict rmDict: A dictionary containing all information needed to construct the desired ReactionRolePicker
        :return: A new ReactionRolePicker object as described in rmDict
        :rtype: ReactionRolePicker
        """
        if "msg" in kwargs:
            raise NameError("Required kwarg not given: msg")
        msg = kwargs["msg"]
        dcGuild = msg.guild

        reactionRoles = {BasedEmoji.fromStr(k): dcGuild.get_role(v["role"]) \
                        for k, v in rmDict["options"].items()}

        timeoutTT = None
        if "timeout" in rmDict:
            expiryTime = utcfromtimestamp(rmDict["timeout"])
            timeoutTT = timedTask.TimedTask(expiryTime=expiryTime,
                                            expiryFunction=expiryFunctions.markExpiredMenu,
                                            expiryFunctionArgs=msg.id)
            botState.client.taskScheduler.scheduleTask(timeoutTT)

        menuColour = Colour.from_rgb(rmDict["col"][0], rmDict["col"][1], rmDict["col"][2]) \
                        if "col" in rmDict else Colour.blue()

        return ReactionRolePicker(**cls._makeDefaults(rmDict, msg=msg, reactionRoles=reactionRoles, dcGuild=dcGuild,
                                                        col=menuColour, timeout=timeoutTT,
                                                        targetMember=dcGuild.get_member(rmDict["targetMember"]) \
                                                                        if "targetMember" in rmDict else None,
                                                        targetRole=dcGuild.get_role(rmDict["targetRole"]) \
                                                                    if "targetRole" in rmDict else None))
