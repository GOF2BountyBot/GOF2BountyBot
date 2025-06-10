from __future__ import annotations
from . import reactionMenu
from bot.cfg import cfg
from .. import botState, lib
from discord import Colour, Emoji, PartialEmoji, Message, Embed, User, Member, Role
from ..scheduling import timedTask
from typing import Dict, Optional, Union, cast
from typing_extensions import NotRequired
from ..users import basedUser
from ..logging import LogCategory
from bot.baseClasses.serializable import SerializesToSchema
from bot.lib.timeUtil import utcfromtimestamp


checkMarkIcon = \
    "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/twitter/259/ballot-box-with-ballot_1f5f3.png"


async def printAndExpirePollResults(msgID: int):
    """Menu expiring method specific to ReactionPollMenus. Count the reactions on the menu, selecting only one per user
    in the case of single-choice mode polls, and replace the menu embed content with a bar chart summarising
    the results of the poll.

    :param int msgID: The id of the discord message containing the menu to expire
    """
    menu = botState.client.reactionMenusDB[msgID]
    if not isinstance(menu, ReactionPollMenu): return
    menuMsg: Message = await menu.msg.channel.fetch_message(menu.msg.id)
    results = {}

    if menu.owningBBUser is not None:
        try:
            menu.owningBBUser.removeOwnedMenu(basedUser.OwnedMenuType.poll, menu)
        except KeyError:
            pass

    maxOptionLen = 0

    for option in menu.options.values():
        results[option] = []
        if len(option.name) > maxOptionLen:
            maxOptionLen = len(option.name)

    for reaction in menuMsg.reactions:
        if isinstance(reaction.emoji, (Emoji, PartialEmoji)):
            # Casting here because custom emojis are guaranteed to have an ID
            currentEmoji = lib.emojis.BasedEmoji(id=cast(int, reaction.emoji.id))
        else:
            currentEmoji = lib.emojis.BasedEmoji(unicode=reaction.emoji)

        if currentEmoji is None:
            botState.client.logger.log("ReactPollMenu", "prtAndExpirePollResults", "Failed to fetch BasedEmoji for reaction: " \
                                + str(reaction), category=LogCategory.reactionMenus, eventType="INV_REACT")
            pollEmbed = menuMsg.embeds[0]
            pollEmbed.set_footer(text="This poll has ended.")
            await menu.msg.edit(content="An error occured when calculating the results of this poll. " \
                                        + "The error has been logged.", embed=pollEmbed)
            return

        menuOption = None
        for currentOption in results:
            if currentOption.emoji == currentEmoji:
                menuOption = currentOption
                break

        if menuOption is None:
            # botState.client.logger.log("ReactPollMenu", "prtAndExpirePollResults", "Failed to find menuOption for emoji: " \
            #                                                                 + str(currentEmoji),
            #                     category=LogCategory.reactionMenus, eventType="UNKN_OPTN")
            # pollEmbed = menuMsg.embeds[0]
            # pollEmbed.set_footer(text="This poll has ended.")
            # await menu.msg.edit(content="An error occured when calculating the results of this poll. " \
            #                     + "The error has been logged.", embed=pollEmbed)
            # return
            continue
        
        user: Union[User, Member]
        async for user in reaction.users():
            if user != botState.client.user:
                if menu.targetRole is not None and (isinstance(user, User) or menu.targetRole not in user.roles):
                    continue
                validVote = True
                if not menu.multipleChoice:
                    for currentOption in results:
                        if currentOption.emoji != currentEmoji and user in results[currentOption]:
                            validVote = False
                            break
                if validVote and user not in results[menuOption]:
                    results[menuOption].append(user)
                    # print(str(user),"voted for", menuOption.emoji.sendable)

    pollEmbed = menuMsg.embeds[0]
    pollEmbed.set_footer(text="This poll has ended.")

    maxCount = 0
    for currentResult in results.values():
        if len(currentResult) > maxCount:
            maxCount = len(currentResult)

    if maxCount > 0:
        resultsStr = "```\n"
        for currentOption in results:
            resultsStr += ("🏆" if len(results[currentOption]) == maxCount else "  ") + currentOption.name \
                            + (" " * (maxOptionLen - len(currentOption.name))) + " | " \
                            + ("=" * int((len(results[currentOption]) / maxCount) * cfg.pollMenuResultsBarLength)) \
                            + (" " if len(results[currentOption]) == 0 else "") + " +" + str(len(results[currentOption])) \
                            + " Vote" + ("s" if len(results[currentOption]) != 1 else "") + "\n"
        resultsStr += "```"

        pollEmbed.add_field(name="Results", value=resultsStr, inline=False)

    else:
        pollEmbed.add_field(name="Results", value="No votes received!", inline=False)

    await menuMsg.edit(embed=pollEmbed, view=None)
    if msgID in botState.client.reactionMenusDB:
        del botState.client.reactionMenusDB[msgID]

    if menuMsg.guild is not None:
        for reaction in menuMsg.reactions:
            await reaction.remove(menuMsg.guild.me)


class SerializedReactionPollMenu(reactionMenu.SerializedReactionMenu):
    multipleChoice: bool
    owningBBUser: NotRequired[int]


@reactionMenu.saveableMenu
class ReactionPollMenu(reactionMenu.ReactionMenu[reactionMenu.DummyReactionMenuOption, reactionMenu.SerializedReactionMenuOption], SerializesToSchema[SerializedReactionPollMenu]):
    """A saveable reaction menu taking a vote from its participants on a selection of option strings.
    On menu expiry, the menu's TimedTask should call printAndExpirePollResults. This edits to menu embed to provide a summary
    and bar chart of the votes submitted to the poll. The poll options have no functionality, all vote counting takes place
    after menu expiry.
    TODO: change pollOptions from dict[BasedEmoji, ReactionMenuOption] to dict[BasedEmoji, str] which is used
            to spawn DummyReactionMenuOptions

    :var multipleChoice: Whether to accept votes for multiple options from the same user, or to restrict users to one option
                            vote per poll.
    :vartype multipleChoice: bool
    :var owningBBUser: The bbUser who started the poll
    :vartype owningBBUser: bbUser
    """
    def __init__(self, msg: Message, pollOptions: Dict[lib.emojis.BasedEmoji, reactionMenu.DummyReactionMenuOption], timeout: timedTask.TimedTask,
            pollStarter: Optional[Union[User, Member]] = None, multipleChoice: bool = False, titleTxt: str = "", desc: str = "",
            col: Colour = Colour.blue(), img: str = "", thumb: str = "", icon: str = "",
            authorName: str = "", targetRole: Optional[Role] = None,
            owningBBUser: Optional[basedUser.BasedUser] = None):
        """
        :param discord.Message msg: the message where this menu is embedded
        :param options: A dictionary storing all of the poll options. Poll option behaviour functions are not called.
                        TODO: Add reactionAdded/Removed overloads that just return and dont check anything
        :type options: dict[lib.emojis.BasedEmoji, ReactionMenuOption]
        :param TimedTask timeout: The TimedTask responsible for expiring this menu
        :param discord.Member pollStarter: The user who started the poll, for printing in the menu embed. Optional.
                                            (Default None)
        :param bool multipleChoice: Whether to accept votes for multiple options from the same user, or to restrict users
                                    to one option vote per poll.
        :param str titleTxt: The content of the embed title (Default "")
        :param str desc: he content of the embed description; appears at the top below the title (Default "")
        :param discord.Colour col: The colour of the embed's side strip (Default None)
        :param str img: URL to a large icon appearing as the content of the embed, left aligned like a field (Default "")
        :param str thumb: URL to a larger image appearing to the right of the title (Default "")
        :param str icon: URL to a smaller image to the left of authorName. AuthorName is required for this to be displayed.
                        (Default "")
        :param str authorName: Secondary, smaller title for the embed (Default "Poll")
        :param discord.Role targetRole: In order to interact with this menu, users must possess this role.
                                        All other reactions are ignored (Default None)
        :param bbUser owningBBUser: The bbUser who started the poll. Used for resetting whether or not a user can make
                                    a new poll (Default None)
        """
        self.multipleChoice = multipleChoice
        self.owningBBUser = owningBBUser

        if pollStarter is not None and authorName == "":
            authorName = str(pollStarter) + " started a poll!"
        else:
            authorName = authorName if authorName else "Poll"

        if icon == "":
            if pollStarter is not None:
                icon = pollStarter.display_avatar.with_size(64).url
        else:
            icon = icon if icon else checkMarkIcon

        if desc == "":
            desc = "React to this message to vote!"
        else:
            desc = "*" + desc + "*"

        super(ReactionPollMenu, self).__init__(msg, options=pollOptions, titleTxt=titleTxt, desc=desc, col=col,
                                                img=img, thumb=thumb, icon=icon, authorName=authorName,
                                                timeout=timeout, targetRole=targetRole)


    def getMenuEmbed(self) -> Embed:
        """Generate the discord.Embed representing the reaction menu, and that
        should be embedded into the menu's message.
        Contains a short description of the menu, its options, the poll starter (if given), whether it accepts multiple choice
        votes, and its expiry time.

        :return: A discord.Embed representing the menu and its options
        :rtype: discord.Embed
        """
        baseEmbed: Embed = super(ReactionPollMenu, self).getMenuEmbed()
        if self.targetRole is not None:
            desc = baseEmbed.description
            baseEmbed.description = ""
            baseEmbed.insert_field_at(0, name=desc, value=f"You must have the {self.targetRole.mention} role to vote.")

        if self.multipleChoice:
            baseEmbed.add_field(name="This is a multiple choice poll!", value="Voting for more than one option is allowed.",
                                inline=False)
        else:
            baseEmbed.add_field(name="This is a single choice poll!",
                                value="If you vote for more than one option, only one will be counted.", inline=False)

        return baseEmbed


    def serialize(self, **kwargs) -> SerializedReactionPollMenu:
        """Serialize this menu to dictionary format for saving.

        :return: A dictionary containing all information needed to recreate this menu
        :rtype: dict
        """
        # Casting here to add the new fields
        baseDict = cast(SerializedReactionPollMenu, super().serialize(**kwargs))
        baseDict["multipleChoice"] = self.multipleChoice
        if self.owningBBUser is not None:
            baseDict["owningBBUser"] = self.owningBBUser.id
        return baseDict


    @classmethod
    def deserialize(cls, rmDict: SerializedReactionPollMenu, **kwargs) -> ReactionPollMenu:
        """Reconstruct a ReactionPollMenu object from its dictionary-serialized representation -
        the opposite of ReactionPollMenu.serialize

        :param dict rmDict: A dictionary containing all information needed to recreate the desired ReactionPollMenu
        :return: A new ReactionPollMenu object as described in rmDict
        :rtype: ReactionPollMenu
        """
        if "msg" not in kwargs:
            raise NameError("Required kwarg not given: msg")
        msg = kwargs["msg"]

        options = {}
        for emojiName in rmDict["options"]:
            emoji = lib.emojis.BasedEmoji.fromStr(emojiName)
            options[emoji] = reactionMenu.DummyReactionMenuOption(rmDict["options"][emojiName]["name"], emoji)

        timeoutTT = None
        if "timeout" in rmDict:
            expiryTime = utcfromtimestamp(rmDict["timeout"])
            botState.client.taskScheduler.scheduleTask(timedTask.TimedTask(expiryTime=expiryTime,
                                                    expiryFunction=printAndExpirePollResults, expiryFunctionArgs=msg.id))

        if "owningBBUser" in rmDict and botState.client.usersDB.idExists(rmDict["owningBBUser"]):
            owner = botState.client.usersDB.getUser(rmDict["owningBBUser"])
        else:
            owner = None
        
        menuColour = Colour.from_rgb(rmDict["col"][0], rmDict["col"][1], rmDict["col"][2]) \
                        if "col" in rmDict else Colour.blue()

        return ReactionPollMenu(**cls._makeDefaults(args=rmDict, ignores=("type", "guild", "channel", "options", "timeout", "owningBBUser", "footerTxt"),
                                                    msg=msg, pollOptions=options, timeout=timeoutTT,
                                                    col=menuColour, owningBBUser=owner,
                                                    targetRole=msg.guild.get_role(rmDict["targetRole"]) \
                                                                    if "targetRole" in rmDict else None))
