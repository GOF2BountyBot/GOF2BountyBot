from dataclasses import dataclass
import operator
import random
from typing import List, Optional, Union, cast
import discord
from discord import ButtonStyle, Embed, Guild, Member, Reaction, User, app_commands, Interaction, Colour
from discord.utils import utcnow
from discord.ui import View, Button
from aiohttp import client_exceptions
import traceback

from .. import client, lib, botState
from ..lib.BASED_version import getBASEDVersion, BASED_REPO_URL
from ..lib.discordUtil import ZWSP
from ..lib.stringTyping import isInt, commaSplitNum
from ..lib.gameMaths import calculateUserBountyHuntingLevel
from ..interactions import basedCommand, basedApp
from ..interactions.basedComponent import StaticComponents
from ..interactions.commandChecks import guildOnly
from ..cfg import cfg, bbData
from .util.transformers import BoolYesNo
from ..users import basedUser
from ..userAlerts import userAlerts
from ..databases import bountyDB
from ..logging import LogCategory
from .util.EmbedEditorUtil import EMBED_EDIT_TEXT_ARGS_SEPARATOR, AnyEmbedField, interactionErrorString
from ..reactionMenus import reactionPollMenu

#region how to play util

FIELD_SPACER = f"\n{ZWSP}"
HOWTOPLAY_MAX_PAGE = "6"
HOWTOPLAY_PAGES = (
    "intro",
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "outro"
)

# endregion
#region leaderboard util

@dataclass
class LeaderboardSettings:
    boardTitle: str
    boardUnit: str
    boardUnitPlural: str
    boardDesc: str


LEADERBOARDS = {
    basedUser.LeaderBoardStat.credits:
        LeaderboardSettings("Current Balance", "Credit", "Credits", "Current player credits balance"),
    
    basedUser.LeaderBoardStat.systemsChecked:
        LeaderboardSettings("Systems Checked", "System", "Systems", "Total number of systems checked"),
    
    basedUser.LeaderBoardStat.bountyWins:
        LeaderboardSettings("Bounties Won", "Bounty", "Bounties", "Total number of bounties won"),
    
    basedUser.LeaderBoardStat.lifetimeBountyHuntingXP:
        LeaderboardSettings("Lifetime Bounty Hunter XP", "xp", "xp", "Total amount of bounty hunting xp earned"),
    
    basedUser.LeaderBoardStat.lifetimeBountyCreditsWon:
        LeaderboardSettings("Lifetime Bounty Rewards", "Credit", "Credits", "Total amount of credits earned from bounty hunting"),
    
    basedUser.LeaderBoardStat.prestiges:
        LeaderboardSettings("Prestiges", "Prestige", "Prestiges", "Number of prestiged achieved"),
    
    basedUser.LeaderBoardStat.totalValue:
        LeaderboardSettings("Current Total Value", "Credit", "Credits", "Total value of balance and all items owned"),
}

#endregion
#region views

"""
# pollCreatorView: "EmbedEditorCog.ViewFactoryType"
def pollCreatorView(interaction: Interaction, userId: Optional[Union[int, str]], embed: Optional[Embed] = None, disableAll: bool = False) -> Optional[View]:
    if interaction.guild is None: return None
    view = View()
    _userId = "" if userId is None else str(userId)

    confirmButton = Button(style=ButtonStyle.green, label="done", disabled=disableAll)
    confirmButton = StaticComponents.User_PollCreator_Submit_New(confirmButton, args=_userId)
    view.add_item(confirmButton)

    cancelButton = Button(style=ButtonStyle.red, label="cancel", disabled=disableAll)
    cancelButton = StaticComponents.User_PollCreator_Cancel_New(cancelButton, args=_userId)
    view.add_item(cancelButton)

    setQuestionButton = Button(style=ButtonStyle.blurple, label="set poll topic", disabled=disableAll)
    setQuestionButton = StaticComponents.User_PollCreator_SetTopic(setQuestionButton, args=f"1{EMBED_EDIT_TEXT_ARGS_SEPARATOR}{_userId}")
    view.add_item(setQuestionButton)

    changeEmojiButton = Button(style=ButtonStyle.blurple, label="change emoji", disabled=disableAll)
    changeEmojiButton = StaticComponents.User_PollCreator_Change_Emoji_Select(changeEmojiButton, args=_userId)
    view.add_item(changeEmojiButton)

    addOptionButton = Button(style=ButtonStyle.blurple, label="add option", disabled=disableAll)
    addOptionButton = StaticComponents.User_PollCreator_Add_Option(addOptionButton, args=_userId)
    view.add_item(addOptionButton)

    removeOptionButton = Button(style=ButtonStyle.blurple, label="remove option", disabled=disableAll)
    removeOptionButton = StaticComponents.User_PollCreator_Remove_Option_Select(removeOptionButton, args=_userId)
    view.add_item(removeOptionButton)

    setDurationButton = Button(style=ButtonStyle.blurple, label="+minutes", disabled=disableAll)
    setDurationButton = StaticComponents.User_PollCreator_SetDuration(setDurationButton, args=_userId)
    view.add_item(setDurationButton)
    
    return view
"""

# endregion

class UserMiscCog(basedApp.BasedCog):
#region util
    def getHowToPlayEmbed(self, page: str):
        e = lib.discordUtil.makeEmbed(
            titleTxt='**BountyBot: How To Play**',
            thumb=self.bot.user.display_avatar.with_size(64).url if self.bot.user else ""
        )

        if isInt(page):
            e.set_footer(text=f"Page {page}/{HOWTOPLAY_MAX_PAGE}")

        return e


    def getHowToPlayPage(self, interaction: Interaction, page: str):
        howToPlayEmbed = self.getHowToPlayEmbed(page)

        if page == "intro":
            howToPlayEmbed.add_field(
                name="Introduction",
                value="This game is based on the *'Most Wanted'* system from Galaxy on Fire 2. If you have played the Supernova addon, " \
                    + "this should be familiar!\n\nIf at any time you would like information about a command, use the `/help [command]` " \
                    + f"command. To see all commands, just use `/help`.\n\nHave fun! 🚀",
                inline=False
            )
            
        elif page == "1":
            newBountiesChannelStr = ""
            if interaction.guild is not None:
                requestedBBGuild = self.bot.guildsDB.getGuild(interaction.guild.id)
                if requestedBBGuild.bountiesDB is not None and requestedBBGuild.hasBountyBoardChannels:
                    bbc = requestedBBGuild.bountiesDB.divisionForLevel(0).bountyBoardChannel
                    if bbc is not None:
                        newBountiesChannelStr = f" in {bbc.channel.mention}"
                if newBountiesChannelStr == "" and requestedBBGuild.hasAnnounceChannel():
                    newBountiesChannelStr = " in <#" + str(requestedBBGuild.getAnnounceChannel().id) + ">"
                    
            howToPlayEmbed.add_field(
                name="1. New Bounties",
                value=f"At random times, new bounties are announced{newBountiesChannelStr}.\n• Use `/bounties` to see the currently active bounties.\n" \
                    + "• Criminals spawn in a system somewhere on the `/map`.\n" \
                    + "• To view a criminal's current route *(possible systems)*, use `/route [criminal]`.",
                inline=False)

        elif page == "2":
            howToPlayEmbed.add_field(
                name="2. System Checking",
                value="Now that we know where our criminal could be, we can check a system with `/check [system]`.\n" \
                    + "This system will now be crossed out in the criminal's `/route`, so we know not to check there again.\n" \
                    + "If a criminal has visited the system recently, then the station's security force will let you know. " \
                    + "They can't have gotten much further along their route!",
                inline=False)

        elif page == "3":
            howToPlayEmbed.add_field(
                name="3. Dueling",
                value="Locating the bounty will immediately engage them in a **duel**. Duels are won by having more powerful gear " \
                    + "than your opponent, by a direct comparison of stats. Finding and defeating a bounty will win you credits and XP.\n\n"
                    + "> Didn't win the bounty? No worries!\nYou will get a share of the rewards for helping narrow down the search.\n\n"

                    + "Many items do not currently have any effect on dueling, such as repair bots, EMPs, or triggerable modules.\n" \
                    + "To get a quick idea of whether you might be able to defeat a bounty, compare their **difficulty level** " \
                    + "to your **bounty hunter level**. For a better comparison, compare your `/loadout` with the criminal's loadout, " \
                    + "which you can find with `/criminal-loadout`.",
                inline=False)

        elif page == "4":
            howToPlayEmbed.add_field(
                name="4. Items",
                value="Now that you've got some credits, try customising your `/loadout`!" \
                    + "\n• You can see your inventory of inactive items in the `/hangar`." \
                    + "\n• You can `/buy` more items from the `/shop`, as well as `/sell` your old ones." ,
                inline=False)


        elif page == "5":
            howToPlayEmbed.add_field(
                name="5. Divisions",
                value="A division is a group of relatively similar bounty difficulties. Every player begins in the easiest division.\n" \
                    + "Once you have completed the final level in your division, you will be able to ascend to the next division and " \
                    + "gain rewards with `/div-up`.\n" \
                    + "Reaching higher divisions will unlock tougher bounties, and much, much more money! And with more money comes much fancier loadouts.\n" \
                    + "Each division also has its own shop, stocking items with the higher tech levels that you will need.",
                inline=False)

        elif page == "6":
            howToPlayEmbed.add_field(
                name="6. Prestiging",
                value="If you are able to defeat the final division, you will unlock `/prestige`.\n"
                    + "Prestiging will reset your playthrough in exchange for some special rewards, and a bump to the **prestiges** stat on your " \
                    + "profile for bragging rights.\n\n" \
                    + "Prestiging resets your bounty hunter level, loadout, balance, hangar and loma. However, you can save your items " \
                    + "from being erased by storing them in your personal **Kaamo Club** storage, with `/kaamo-store`. You will be able to " \
                    + "retrieve these items again once you return to the maximum bounty hunter level, with `/kaamo-get`.",
                inline=False)

        elif page == "outro":
            howToPlayEmbed.add_field(
                name="Extra Notes/Tips",
                value="• 🌍 **Home Servers**: To keep BountyBot balanced, you can only use certain commands (e.g `/check`, `/buy`...) in one server of your choice, " \
                    + "your home server. You can change your home server with `/set-home-server`, but be aware that this command has a very long cooldown.\n\n" \
                    + "• Having trouble getting to new bounties in time? Use `/notify bounties` to be pinged every time a new bounty spawns.\n\n" \
                    + "• Make sure you are ready to fight the next division's bounties before you `/div-up`! You may wish to check out the " \
                    + "loadouts of the division's easier bounties before you decide.\n\n" \
                    + "• If you `/div-up` too soon and are unable to defeat any bounties, you can `/div-down` to descend to the previous " \
                    + "division, but you will have to complete the division's highest level again before you can return.",
                inline=False)

        return howToPlayEmbed


    def makeHowToPlayView(self, interaction: Interaction, page: str):
        v = View(timeout=None)
        pageIndex = HOWTOPLAY_PAGES.index(page)
        
        nextPage = Button(disabled=page == HOWTOPLAY_PAGES[-1], emoji=cfg.defaultEmojis.next.sendable)
        nextPage = StaticComponents.User_HowToPlay_ShowPage(nextPage, HOWTOPLAY_PAGES[min(len(HOWTOPLAY_PAGES) - 1, pageIndex + 1)])

        previousPage = Button(disabled=page == HOWTOPLAY_PAGES[0], emoji=cfg.defaultEmojis.previous.sendable)
        previousPage = StaticComponents.User_HowToPlay_ShowPage(previousPage, HOWTOPLAY_PAGES[pageIndex - 1])

        deleteMessage = Button(emoji=cfg.defaultEmojis.delete.sendable, style=ButtonStyle.red)
        deleteMessage = StaticComponents.Delete_Message(deleteMessage, str(interaction.user.id))

        v.add_item(previousPage).add_item(nextPage).add_item(deleteMessage)
        return v

#endregion
#region static components
#region how to play

    @basedApp.BasedCog.staticComponentCallback(StaticComponents.User_HowToPlay_ShowPage)
    async def howToPlay(self, interaction: Interaction, page: str):
        e = self.getHowToPlayPage(interaction, page)
        v = self.makeHowToPlayView(interaction, page)
        await interaction.response.edit_message(embed=e, view=v)

#endregion how to play
#region poll creator
    """
    @basedApp.BasedCog.staticComponentCallback(StaticComponents.User_PollCreator_Add_Option)
    async def poll_addOption(self, interaction: Interaction, userId: str):
        if userId and interaction.user.id != int(userId):
            return

        if interaction.message is None or interaction.guild is None: return
        menu = self.bot.reactionMenusDB.get(interaction.message.id, None)
        if not isinstance(menu, reactionPollMenu.ReactionPollMenu):
            await interaction.response.send_message(f"{cfg.defaultEmojis.error} This interaction is not valid here. The message is not a poll.", ephemeral=True)
            return
        
        embed = interaction.message.embeds[0]
        disabledView = pollCreatorView(interaction, userId=userId, embed=embed, disableAll=True)

        await interaction.response.edit_message(view=disabledView)
        reactMsg = await interaction.followup.send(f"React with your new emoji, within {lib.timeUtil.td_format_noYM(cfg.timeouts.menuInteractionDefault)}", wait=True)

        def check(reaction: Reaction, user: Union[Member, User]) -> bool:
            return reaction.message.id == reactMsg.id and user.id == int(userId)
        
        try:
            reaction, _ = await self.bot.wait_for("reaction_add", check=check, timeout=int(cfg.timeouts.menuInteractionDefault.total_seconds()))
        except TimeoutError:
            await interaction.edit_original_response(content=f"~~React with your new emoji, within {lib.timeUtil.td_format_noYM(cfg.timeouts.menuInteractionDefault)}~~\nOut of time!")
        else:
            try:
                newEmoji = lib.emojis.BasedEmoji.fromReaction(reaction.emoji, rejectInvalid=True)
            except lib.exceptions.UnrecognisedCustomEmoji:
                await interaction.edit_original_response(content=":x: I can't access that emoji! Please use either a stock emoji, or one from a server that I am a member of.")
            else:
                if newEmoji in menu.options:
                    await interaction.edit_original_response(content=":x: That emoji is already in use for another role.")
                else:
                    menu.options[newEmoji] = option
                    del menu.options[option.emoji]
                    option.emoji = newEmoji
                    await menu.updateMessage(view=view)
                    await reactMsg.delete()
                    return

        await menu.msg.edit(view=view)
        return

        embed = interaction.message.embeds[0]

        selectedRaw: Optional[List[str]] = None if interaction.data is None else interaction.data.get("values", None)

        selectedRoles: List[Role] = []
        failed: List[str] = []
        addedEmojis: List[lib.emojis.BasedEmoji] = []
        removedEmojis: List[lib.emojis.BasedEmoji] = []
        
        if selectedRaw is None:
            await interaction.response.send_message(cfg.defaultEmojis.cancel + " This type of interaction is not valid here.", ephemeral=True)
            self.bot.logger.log(type(self).__name__, self.poll_addOption.__name__,
                                "select-based static component triggered for non-select interaction: " \
                                    + interactionErrorString(interaction, StaticComponents.Admin_MakeRoleMenu_Manage_Roles),
                                category=LogCategory.staticComponents, eventType="COMPONENT_NOT_SELECT")
            return
        else:
            for rawId in selectedRaw:
                if not lib.stringTyping.isInt(rawId):
                    self.bot.logger.log(type(self).__name__, self.poll_addOption.__name__,
                                f"Non-int role ID received '{rawId}': " \
                                    + interactionErrorString(interaction, StaticComponents.Admin_MakeRoleMenu_Manage_Roles),
                                category=LogCategory.staticComponents, eventType="ID_NOT_INT")
                    failed.append(rawId)
                    continue

                role = interaction.guild.get_role(int(rawId))
                if role is None or not role.is_assignable():
                    failed.append(rawId)
                    continue
                
                selectedRoles.append(role)
                
                if not any(o.role == role for o in menu.options.values()):
                    while (optionEmoji := randomEmoji()) in menu.options: pass
                    menu.options[optionEmoji] = ReactionRolePickerOption(emoji=optionEmoji, role=role, menu=menu)
                    addedEmojis.append(optionEmoji)
            
            removedEmojis = [e for e, o in menu.options.items() if o.role not in selectedRoles]
            for option in removedEmojis:
                del menu.options[option]


        if lib.discordUtil.embedEmpty(embed):
            embed.description = lib.discordUtil.ZWSP
        
        view = roleMenuCreatorView(interaction, userId, embed=embed, disableAll=True)
        # TODO: Why does this think the interaction has already been acknowledged?
        try:
            await interaction.response.edit_message(content=f"{cfg.defaultEmojis.longProcess} Role menu loading..", view=view, embed=None)
        except HTTPException:
            pass

        async def addEmoji(e: lib.emojis.BasedEmoji):
            ""This function guarantees that only discord-compatible emojis will be added to the menu, by randomly adding reactions until an emoji is accepted.
            ""
            try:
                await cast(Message, interaction.message).add_reaction(e.sendable)
            except HTTPException as ex:
                if ex.code != lib.discordUtil.ApiError.unknown_emoji.value:
                    raise ex
            else:
                return
            
            original = e

            while True:
                while (e := randomEmoji()) in menu.options: pass
                try:
                    await cast(Message, interaction.message).add_reaction(e.sendable)
                except HTTPException as ex:
                    if ex.code != lib.discordUtil.ApiError.unknown_emoji.value:
                        raise ex
                else:
                    break

            menu.options[e] = menu.options[original]
            menu.options[e].emoji = e
            del menu.options[original]

        async def removeEmoji(e: lib.emojis.BasedEmoji):
            try:
                await cast(Message, interaction.message).remove_reaction(e.sendable, cast(ClientUser, self.bot.user))
            except HTTPException:
                pass

        tasks = lib.discordUtil.BasicScheduler()
        for e in addedEmojis:
            tasks.add(addEmoji(e))
        for e in removedEmojis:
            tasks.add(removeEmoji(e))

        await tasks.wait()
        tasks.raiseExceptions()
        
        if view:
            for c in view.children:
                if isinstance(c, (Button, Select)):
                    c.disabled = False

        await interaction.edit_original_response(content=None, view=view, embed=menu.getMenuEmbed())

        if failed:
            await interaction.message.reply("The following roles could not be added. Please try again:",
                                            embed=Embed(description="\n".join(f"<@&{i}>" for i in failed)), ephemeral=True)

    
    @BasedCog.staticComponentCallback(StaticComponents.Admin_MakeRoleMenu_Change_Emoji_Select)
    async def startChangeEmoji(self, interaction: Interaction, userId: str):
        if userId and interaction.user.id != int(userId):
            return

        if interaction.message is None or interaction.guild is None: return
        menu = roleMenuForInteraction(interaction)
        if menu is None:
            await interaction.response.send_message(f"{cfg.defaultEmojis.error} This interaction is not valid here. The message is not a role menu.", ephemeral=True)
            return

        view = roleMenuCreatorView(interaction, userId, embed=interaction.message.embeds[0])
        if view:
            for c in view.children:
                if isinstance(c, Button):
                    c.disabled = True
                elif isinstance(c, Select):
                    view.remove_item(c)

            emojiSelector = Select(options=[SelectOption(label=option.role.name, value=str(option.role.id)) for option in menu.options.values()])
            emojiSelector = StaticComponents.Admin_MakeRoleMenu_Change_Emoji(emojiSelector, args=userId)
            view.add_item(emojiSelector)

        await interaction.response.edit_message(view=view)

    
    @BasedCog.staticComponentCallback(StaticComponents.Admin_MakeRoleMenu_Change_Emoji)
    async def endChangeEmoji(self, interaction: Interaction, userId: str):
        if userId and interaction.user.id != int(userId):
            return

        if interaction.message is None or interaction.guild is None: return
        menu = roleMenuForInteraction(interaction)
        if menu is None:
            await interaction.response.send_message(f"{cfg.defaultEmojis.error} This interaction is not valid here. The message is not a role menu.", ephemeral=True)
            return

        selected: Optional[List[str]] = None if interaction.data is None else interaction.data.get("values", None)
        view = roleMenuCreatorView(interaction, userId, embed=interaction.message.embeds[0])

        if not selected:
            errorMsg = cfg.defaultEmojis.cancel + " This type of interaction is not valid here."
            self.bot.logger.log(type(self).__name__, self.endChangeEmoji.__name__,
                                "select-based static component triggered for non-select interaction: " \
                                    + interactionErrorString(interaction, StaticComponents.Admin_MakeRoleMenu_Change_Emoji),
                                category=LogCategory.staticComponents, eventType="COMPONENT_NOT_SELECT")
        else:
            rawId = selected[0]
            if not lib.stringTyping.isInt(rawId):
                self.bot.logger.log(type(self).__name__, self.endChangeEmoji.__name__,
                            f"Non-int role ID received '{rawId}': " \
                                + interactionErrorString(interaction, StaticComponents.Admin_MakeRoleMenu_Change_Emoji),
                            category=LogCategory.staticComponents, eventType="ID_NOT_INT")
                errorMsg = "That menu option doesn't represent a role!"
            else:
                roleId = int(rawId)
                try:
                    option = next(o for o in menu.options.values() if o.role.id == roleId)
                except StopIteration:
                    errorMsg = "I can't find that role in the menu!"
                else:
                    disabledNoSelects = roleMenuCreatorView(interaction, userId, embed=interaction.message.embeds[0])
                    if disabledNoSelects:
                        for c in disabledNoSelects.children:
                            if isinstance(c, Button):
                                c.disabled = True
                            elif isinstance(c, Select):
                                disabledNoSelects.remove_item(c)

                    await interaction.response.edit_message(view=disabledNoSelects)
                    reactMsg = await interaction.followup.send(f"React with your new emoji, within {lib.timeUtil.td_format_noYM(cfg.timeouts.menuInteractionDefault)}", wait=True)

                    def check(reaction: Reaction, user: Union[Member, User]) -> bool:
                        return reaction.message.id == reactMsg.id and user.id == int(userId)
                    
                    try:
                        reaction, _ = await self.bot.wait_for("reaction_add", check=check, timeout=int(cfg.timeouts.menuInteractionDefault.total_seconds()))
                    except TimeoutError:
                        await interaction.edit_original_response(content=f"~~React with your new emoji, within {lib.timeUtil.td_format_noYM(cfg.timeouts.menuInteractionDefault)}~~\nOut of time!")
                    else:
                        try:
                            newEmoji = lib.emojis.BasedEmoji.fromReaction(reaction.emoji, rejectInvalid=True)
                        except lib.exceptions.UnrecognisedCustomEmoji:
                            await interaction.edit_original_response(content=":x: I can't access that emoji! Please use either a stock emoji, or one from a server that I am a member of.")
                        else:
                            if newEmoji in menu.options:
                                await interaction.edit_original_response(content=":x: That emoji is already in use for another role.")
                            else:
                                menu.options[newEmoji] = option
                                del menu.options[option.emoji]
                                option.emoji = newEmoji
                                await menu.updateMessage(view=view)
                                await reactMsg.delete()
                                return

                    await menu.msg.edit(view=view)
                    return

        await interaction.response.edit_message(view=view)
        if errorMsg is not None:
            await interaction.followup.send(errorMsg, ephemeral=True)

    
    @BasedCog.staticComponentCallback(StaticComponents.Admin_MakeRoleMenu_Submit_New_Menu)
    async def endCreateMenu(self, interaction: Interaction, userId: str):
        if interaction.message and (commonStaticComponentsCog := self.getCommonStaticComponentsCog(callingFuncName="endCreatemenu")):
            if await commonStaticComponentsCog.clearViewFromMessage(interaction, userId):
                menu = self.bot.reactionMenusDB[interaction.message.id]
                menuEmbed = interaction.message.embeds[0]
                
                menu.titleTxt = menuEmbed.title or ""
                menu.desc = menuEmbed.description or ""
                menu.col = menuEmbed.color or Colour.blue()
                menu.img = menuEmbed.image.url or ""
                menu.thumb = menuEmbed.thumbnail.url or ""
                menu.icon = menuEmbed.author.icon_url or ""
                menu.authorName = menuEmbed.author.name or ""
                
                await menu.updateMessage()


    @BasedCog.staticComponentCallback(StaticComponents.Admin_MakeRoleMenu_Cancel_New_Menu)
    async def cancelMenu(self, interaction: Interaction, userId: str):
        if interaction.message and interaction.user.id == int(userId):
            await interaction.response.defer()
            menu = self.bot.reactionMenusDB[interaction.message.id]
            await menu.delete()
    """

#endregion poll creator
#endregion
#region commands

    @basedCommand.basedCommand()
    @app_commands.command(name="source",
                            description="Get information about the bot, including a link to source code.")
    async def cmd_source(self, interaction: Interaction):
        """Print a short message with information about the bot's source code.
        """
        srcEmbed = lib.discordUtil.makeEmbed(authorName="Source Code",
                                            col=Colour.purple(),
                                            icon="https://image.flaticon.com/icons/png/512/25/25231.png",
                                            footerTxt="Bot Source",
                                            footerIcon="https://i.imgur.com/7SMgF0t.png")
        srcEmbed.add_field(name="Uptime",
                            value=lib.timeUtil.td_format_noYM(utcnow() - self.bot.launchTime))
        srcEmbed.add_field(name="Author",
                            value="Trimatix#2244")
        srcEmbed.add_field(name="Library",
                            value="[Discord.py " + discord.__version__ + "](https://github.com/Rapptz/discord.py/)")
        srcEmbed.add_field(name="BASED",
                                value=f"[BASED {getBASEDVersion().BASED_version}]({BASED_REPO_URL})")
        srcEmbed.add_field(name="Source Code",
                            value=f"[GitHub]({self.bot.githubRepo.html_url})")
        srcEmbed.add_field(name="Invite",
                            value="Please ask the bot developer to post the bot's invite link here!")
        await interaction.response.send_message(embed=srcEmbed)


    @basedCommand.basedCommand()
    @app_commands.command(name="how-to-play",
                            description="Learn the basics of how to play BountyBot!")
    async def cmd_how_to_play(self, interaction: Interaction):
        """Print a short guide, teaching users how to play bounties.
        """
        if interaction.guild is None:
            sendDM = False
        else:
            if interaction.user.dm_channel is None:
                await interaction.user.create_dm()
            sendDM = interaction.user.dm_channel is not None

        newBountiesChannelStr = ""
        if interaction.guild is not None:
            requestedBBGuild = self.bot.guildsDB.getGuild(interaction.guild.id)
            if requestedBBGuild.bountiesDB is not None and requestedBBGuild.hasBountyBoardChannels:
                bbc = requestedBBGuild.bountiesDB.divisionForLevel(0).bountyBoardChannel
                if bbc is not None:
                    newBountiesChannelStr = f" in {bbc.channel.mention}"
            if newBountiesChannelStr == "" and requestedBBGuild.hasAnnounceChannel():
                newBountiesChannelStr = " in <#" + str(requestedBBGuild.getAnnounceChannel().id) + ">"

        e = self.getHowToPlayPage(interaction, HOWTOPLAY_PAGES[0])
        v = self.makeHowToPlayView(interaction, HOWTOPLAY_PAGES[0])

        if not sendDM:
            await interaction.response.send_message(embed=e, view=v, ephemeral=True)
            return

        try:
            await interaction.user.send(embed=e, view=v)
        except discord.Forbidden:
            await interaction.response.send_message(embed=e, view=v, ephemeral=True)
            return

        await interaction.response.send_message("✅ Info sent to your DMs!", ephemeral=True)


    @basedCommand.basedCommand()
    @app_commands.describe(
        stat="The user statistic to display (Defaults to bounty wins)",
        all_servers=f"Give Yes to view users in all servers, or No to view only users in this server (Defaults to No)"
    )
    @app_commands.choices(
        stat=[
            app_commands.Choice(name=s.value, value=s.value)
            for s in basedUser.LeaderBoardStat
        ]
    )
    @app_commands.command(
        name="leaderboard",
        description="Show the leaderboard for various user statistics, in this server or all servers."
    )
    async def cmd_leaderboard(self, interaction: Interaction, stat: str = basedUser.LeaderBoardStat.bountyWins.value, all_servers: BoolYesNo = BoolYesNo.No):
        """display leaderboards for different statistics
        """
        await interaction.response.defer(thinking=True)

        _stat = basedUser.LeaderBoardStat(stat)
        inGuild = interaction.guild is not None

        globalBoard = not (inGuild and not bool(all_servers))
        boardScope = interaction.guild.name \
                        if interaction.guild is not None and not globalBoard \
                        else "Global Leaderboard"

        settings = LEADERBOARDS[_stat]
        boardDesc = f"*{settings.boardDesc}{' across all servers' if globalBoard else ''}.*"

        def userIsInScope(user: basedUser.BasedUser) -> bool:
            # casting here because guild nullability is checked above
            return globalBoard or cast(discord.Guild, interaction.guild).get_member(user.id) is not None

        # get the requested stats
        userStats = {user.id: user.getStat(_stat) for user in self.bot.usersDB.getUsers() if userIsInScope(user)}

        # build the leaderboard embed
        leaderboardEmbed = lib.discordUtil.makeEmbed(titleTxt=settings.boardTitle, authorName=boardScope,
                                                        icon=bbData.winIcon, col=bbData.factionColours["neutral"], desc=boardDesc)

        if userStats:
            # sort users by the stat
            userStats = sorted(userStats.items(), key=operator.itemgetter(1), reverse=True)[:10]

            # add all users to the leaderboard embed with places and values
            includesExternalUser = False
            first = True

            valueIsInt = isinstance(userStats[0][1], int)

            for place in range(min(len(userStats), 10)):
                memberAttempt: Optional[Union[User, Member]] = None

                if interaction.guild is not None:
                    memberAttempt = interaction.guild.get_member(userStats[place][0])

                # handling for global leaderboards/users not in the local guild
                if memberAttempt is None:
                    memberAttempt = self.bot.get_user(userStats[place][0])
                    if memberAttempt is None:
                        currentUser = f"{'*' if inGuild else ''}<@{userStats[place][0]}>"
                    else:
                        currentUser = f"{'*' if inGuild else ''}{memberAttempt}"
                    includesExternalUser = True
                else:
                    currentUser = memberAttempt.mention
                
                currentValue = commaSplitNum(cast(int, userStats[place][1])) if valueIsInt else str(userStats[place][1])
                currentUnits = settings.boardUnit if userStats[place][1] == 1 else settings.boardUnitPlural
                leaderboardEmbed.add_field(name=f"{'⭐ ' if first else ''}{currentValue} {currentUnits}",
                                            value=f"{place + 1}. {currentUser}",
                                            inline=False)
                if first:
                    first = False
    
            # If at least one external use is on the leaderboard, give a key
            if inGuild and includesExternalUser:
                leaderboardEmbed.set_footer(text="* A user that is from another server")

        # send the embed
        await interaction.followup.send(embed=leaderboardEmbed)


    @guildOnly()
    @basedCommand.basedCommand()
    @app_commands.choices(
        notification=[
            app_commands.Choice(name=alertType.userFriendlyName, value=alertId)
            for alertId, alertType in userAlerts.userAlertsIDsTypes.items()
        ]
    )
    @app_commands.command(name="notify",
                            description="Toggle notifications for various events.")
    async def cmd_notify(self, interaction: Interaction, notification: str):
        """⚠ WARNING: MARKED FOR CHANGE ⚠
        The following function is provisional and marked as planned for overhaul.
        Details: Notifications for shop items have yet to be implemented.

        Allow a user to subscribe and unsubscribe from pings when certain events occur.
        """
        # Casting here because this command is decorated with guildOnly
        guild = cast(Guild, interaction.guild)
        if not guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message(":x: I do not have the 'Manage Roles' permission in this server! Please contact an admin :robot:")
            return

        requestedBBUser = self.bot.usersDB.getOrAddID(interaction.user.id)
        requestedBBGuild = self.bot.guildsDB.getGuild(guild.id)

        alertType = userAlerts.userAlertsIDsTypes[notification]

        guildMember = guild.get_member(interaction.user.id)
        if guildMember is None:
            guildMember = await guild.fetch_member(interaction.user.id)
            if guildMember is None:
                await interaction.response.send_message("🥴 An error occurred when fetching your account from discord. Please try this command again.", ephemeral=True)
                return

        if alertType is userAlerts.UA_New_Bounty:
            if requestedBBGuild.bountiesDisabled:
                await interaction.response.send_message(":x: This server has bounties disabled!", ephemeral=True)
                return
            if not requestedBBGuild.hasBountyAlertRoles:
                await interaction.response.send_message(":x: This server does not have roles for new bounties notifications. :robot:")
                return

            bountiesDB = cast(bountyDB.BountyDB, requestedBBGuild.bountiesDB)

            if requestedBBUser.classicModeEnabled:
                tl = -1
                div = bountiesDB.divisionForName(cfg.classic_divisionName)
                roleId = div.alertRoleID
                classicStr = "classic mode "
            else:
                tl = calculateUserBountyHuntingLevel(requestedBBUser.bountyHuntingXP)
                roleId = bountiesDB.divisionForLevel(tl).alertRoleID
                classicStr = ""

            tlRole = guild.get_role(roleId)
            if tlRole is None:
                allRoles = await guild.fetch_roles()
                try:
                    tlRole = next(r for r in allRoles if r.id == roleId)
                except StopIteration:
                    await interaction.response.send_message(":woozy_face: The role for your division could not be found. Please contact an admin.", ephemeral=True)
                    return

            if tlRole in guildMember.roles:
                try:
                    await guildMember.remove_roles(tlRole, reason="User unsubscribed from new bounties notifications via BB command")
                except discord.Forbidden:
                    await interaction.response.send_message(":woozy_face: I don't have permission to do that! Please ensure the " \
                                                            + f"{tlRole.name} role is beneath the BountyBot role.", ephemeral=True)
                except discord.HTTPException as ex:
                    await interaction.response.send_message(":woozy_face: Something went wrong! Please contact an admin or try again later.\n" \
                                                            + f"`{ex.code} {ex.text}`", ephemeral=True)
                except client_exceptions.ClientOSError:
                    await interaction.response.send_message(":thinking: Whoops! A connection error occurred, and the error has been " \
                                                            + "logged. Could you try that again please?", ephemeral=True)
                    self.bot.logger.log("main", "cmd_notify",
                                        "aiohttp.client_exceptions.ClientOSError occurred when attempting to " \
                                            + f"remove new bounty role {tlRole.name}#{tlRole.id}" \
                                            + f", TL {tl}, from {classicStr}user {interaction.user.name}#{interaction.user.id}" \
                                            + f" in guild {guild.name}#{guild.id}.",
                                        category=LogCategory.userAlerts,
                                        eventType="ClientOSError", trace=traceback.format_exc())
                else:
                    await interaction.response.send_message(":white_check_mark: You have unsubscribed from **new bounties** notifications.", ephemeral=True)
            else:
                if not requestedBBUser.hasHomeGuild or requestedBBUser.homeGuildID != guild.id:
                    await interaction.response.send_message(":x: You can only enable new bounty alerts in your home server!\n" \
                                                + f"For more information, please see `/help` for the `/home-server` command.")
                    return
                try:
                    await guildMember.add_roles(tlRole,
                                                    reason="User subscribed to new bounties notifications via BB command")
                except discord.Forbidden:
                    await interaction.response.send_message(":woozy_face: I don't have permission to do that! Please ensure the " \
                                                + f"{tlRole.name} role is beneath the BountyBot role.")
                except discord.HTTPException:
                    await interaction.response.send_message(":woozy_face: Something went wrong! " \
                                                + "Please contact an admin or try again later.")
                except client_exceptions.ClientOSError:
                    await interaction.response.send_message(":thinking: Whoops! A connection error occurred, and the error has been " \
                                                + "logged. Could you try that again please?")
                    self.bot.logger.log("main", "cmd_notify",
                                        "aiohttp.client_exceptions.ClientOSError occurred when attempting to " \
                                            + "grant new bounty role {tlRole.name}#{tlRole.id}" \
                                            + f", TL {tl}, from {classicStr}user {interaction.user.name}#{interaction.user.id}" \
                                            + f" in guild {guild.name}#{guild.id}.",
                                        category=LogCategory.userAlerts,
                                        eventType="ClientOSError", trace=traceback.format_exc())
                else:
                    await interaction.response.send_message(":white_check_mark: You have subscribed to **new bounties** notifications!")
            
        else:
            try:
                alertNewState = await requestedBBUser.toggleAlertType(alertType, guild, requestedBBGuild, guildMember)

            except discord.Forbidden:
                await interaction.response.send_message(":woozy_face: I don't have permission to do that! Please ensure the requested role " \
                                                        + "is beneath the BountyBot role.", ephemeral=True)
            except discord.HTTPException:
                await interaction.response.send_message(":woozy_face: Something went wrong! Please contact an admin or try again later.", ephemeral=True)
            
            except ValueError:
                await interaction.response.send_message(f":x: This server does not have a role for {alertType.userFriendlyName} notifications. :robot:", ephemeral=True)
            
            except client_exceptions.ClientOSError as e:
                await interaction.response.send_message(":thinking: Whoops! A connection error occurred, and the error has been logged. " \
                                                        + "Could you try that again please?", ephemeral=True)

                self.bot.logger.log("main", "cmd_notify", "ClientOSError occurred when attempting to grant " \
                                                            + f"{interaction.user.name}#{interaction.user.id}" \
                                                            + f" alert {notification} in guild {guild.name}#{guild.id}.",
                                                        category=LogCategory.userAlerts,
                                                        exception=e)
            else:
                await interaction.response.send_message(f":white_check_mark: You have {'subscribed to' if alertNewState else 'unsubscribed from'} **{alertType.userFriendlyName}** notifications.")

    """
    @guildOnly()
    @app_commands.command(name="poll",
                            description="Create a reaction-based poll, with up to 20 options. Each user can only run 1 poll at a time.")
    async def cmd_poll(self, interaction: Interaction):
        ""Run a reaction-based poll, allowing users to choose between several named options.
        Users may not create more than one poll at a time, anywhere.
        Option reactions must be either unicode, or custom to the server where the poll is being created.

        args must contain a poll subject (question) and new line, followed by a newline-separated list of emoji-option pairs,
        where each pair is separated with a space.
        For example: 'Which one?\n0️⃣ option a\n1️⃣ my second option\n2️⃣ three' will produce three options:
        - 'option a'         which participants vote for by adding the 0️⃣ reaction
        - 'my second option' which participants vote for by adding the 1️⃣ reaction
        - 'three'            which participants vote for by adding the 2️⃣ reaction
        and the subject of the poll is 'Which one?'
        The poll subject is optional. To not provide a subject, simply begin args with a new line.

        args may also optionally contain the following keyword arguments, given as argname=value
        - target        : A role to restrict participants by. Must be a role mention, not ID.
        - multiplechoice: Whether or not to allow participants to vote for multiple poll options. Must be true or false.
        - days          : The number of days that the poll should run for. Must be at least one, or unspecified.
        - hours         : The number of hours that the poll should run for. Must be at least one, or unspecified.
        - minutes       : The number of minutes that the poll should run for. Must be at least one, or unspecified.
        - seconds       : The number of seconds that the poll should run for. Must be at least one, or unspecified.

        Polls must have a run length. That is, specifying ALL run time kwargs as 'off' will return an error.

        TODO: Support target IDs

        :param discord.Message message: the discord message calling the command
        :param str args: A newline-separated list of space-separated emoji-option pairs, and optionally any kwargs as specified
                            in this function's docstring
        :param bool isDM: Whether or not the command is being called from a DM channel
        ""
        bUser = self.bot.usersDB.getOrAddID(interaction.user.id)
        if bUser.hasMenuOfTypeID(basedUser.OwnedMenuType.poll):
            await interaction.response.send_message(":x: You can only make one poll at a time!", ephemeral=True)
            return

        await interaction.response.send_message(f"{cfg.defaultEmojis.longProcess} Loading...")
        menuMsg = await interaction.original_response()

        embed = Embed(description="React to this message to choose your role(s):", title="Role Menu")
        embed.set_footer(text=f"Menu ID: {menuMsg.id}")
        view = roleMenuCreatorView(interaction, interaction.user.id, embed=embed)

        await menuMsg.edit(content=None, embed=embed, view=view)
        menu = ReactionRolePicker(menuMsg, {}, dcGuild, timeout=None)
        self.bot.reactionMenusDB[menuMsg.id] = menu
















        pollOptions = {}
        kwArgs = {}
        requestedBBGuild = botState.client.guildsDB.getGuild(message.guild.id)

        argsSplit = args.split("\n")
        if len(argsSplit) < 2:
            await message.reply(mention_author=False,
                                content=":x: Invalid arguments! Please provide your poll subject, followed by a new line, then " \
                                        + "a new line-separated series of poll options.\nFor more info, see `" \
                                        + requestedBBGuild.commandPrefix + "help poll`")
            return
        pollSubject = argsSplit[0]
        argPos = 0
        for arg in argsSplit[1:]:
            if arg == "":
                continue
            argPos += 1
            try:
                argNoSpaces = arg.strip(" ")
                optionName = argNoSpaces[arg.strip(" ").index(" ") + 1:]
                dumbReact = lib.emojis.BasedEmoji.fromStr(argNoSpaces.split(" ")[0])
            except (ValueError, IndexError):
                for kwArg in ["target=", "days=", "hours=", "seconds=", "minutes=", "multiplechoice="]:
                    if arg.lower().startswith(kwArg):
                        kwArgs[kwArg[:-1]] = arg[len(kwArg):]
                        break
            # except lib.exceptions.UnrecognisedCustomEmoji:
            #     await message.reply(mention_author=False, content=":x: I don't know your " + str(argPos) + lib.stringTyping.getNumExtension(argPos) \
            #                                 + " emoji!\n" \
            #                                 + "You can only use built in emojis, or custom emojis that are in this server.")
            #     return
            else:
                if dumbReact.sendable == "None":
                    await message.reply(mention_author=False, content=":x: I don't know your " + str(argPos) + lib.stringTyping.getNumExtension(argPos) \
                                                + " emoji!\nYou can only use built in emojis, " \
                                                + "or custom emojis that are in this server.")
                    return
                if dumbReact is None:
                    await message.reply(mention_author=False, content=":x: Invalid emoji: " + argNoSpaces.split(" ")[1])
                    return
                elif dumbReact.isID:
                    localEmoji = False
                    for localEmoji in message.guild.emojis:
                        if localEmoji.id == dumbReact.id:
                            localEmoji = True
                            print("EMOJI FOUND")
                            break
                    if not localEmoji:
                        await message.reply(mention_author=False, content=":x: I don't know your " + str(argPos) \
                                                    + lib.stringTyping.getNumExtension(argPos) + " emoji!\n" \
                                                    + "You can only use built in emojis, or custom emojis " \
                                                    + "that are in this server.")
                        return

                if dumbReact in pollOptions:
                    await message.reply(mention_author=False, content=":x: Cannot use the same emoji for two options!")
                    return

                pollOptions[dumbReact] = reactionMenu.DummyReactionMenuOption(optionName, dumbReact)

        if len(pollOptions) == 0:
            await message.reply(mention_author=False, content=":x: No options given!")
            return

        targetRole = None
        if "target" in kwArgs:
            if lib.stringTyping.isRoleMention(kwArgs["target"]):
                targetRole = message.guild.get_role(int(kwArgs["target"].lstrip("<@&").rstrip(">")))
                if targetRole is None:
                    await message.reply(mention_author=False, content=":x: Unknown target role!")
                    return

            else:
                await message.reply(mention_author=False, content=":x: Invalid target role!")
                return

        timeoutDict = {}

        for timeName in ["days", "hours", "minutes", "seconds"]:
            if timeName in kwArgs:
                if kwArgs[timeName].lower() == "off":
                    timeoutDict[timeName] = -1
                else:
                    if not lib.stringTyping.isInt(kwArgs[timeName]) or int(kwArgs[timeName]) < 1:
                        await message.reply(mention_author=False, content=":x: Invalid number of " + timeName + " before timeout!")
                        return

                    timeoutDict[timeName] = int(kwArgs[timeName])


        multipleChoice = True

        if "multiplechoice" in kwArgs:
            if kwArgs["multiplechoice"].lower() in ["off", "no", "false", "single", "one"]:
                multipleChoice = False
            elif kwArgs["multiplechoice"].lower() not in ["on", "yes", "true", "multiple", "many"]:
                await message.reply(mention_author=False, content="Invalid `multiplechoice` argument '" + kwArgs["multiplechoice"] \
                                            + "'! Please use either `multiplechoice=yes` or `multiplechoice=no`")
                return


        timeoutExists = False
        for timeName in timeoutDict:
            if timeoutDict[timeName] != -1:
                timeoutExists = True
        timeoutExists = timeoutExists or timeoutDict == {}

        if not timeoutExists:
            await message.reply(mention_author=False, content=":x: Poll timeouts cannot be disabled!")
            return

        menuMsg = await message.reply(mention_author=False, content="‎")

        timeoutDelta = timedelta(**(timeoutDict or cfg.timeouts.pollMenuExpiry))
        timeoutTT = timedTask.TimedTask(expiryDelta=timeoutDelta, expiryFunction=reactionPollMenu.printAndExpirePollResults,
                                        expiryFunctionArgs=menuMsg.id)
        botState.client.taskScheduler.scheduleTask(timeoutTT)

        menu = reactionPollMenu.ReactionPollMenu(menuMsg, pollOptions, timeoutTT, pollStarter=message.author,
                                                    multipleChoice=multipleChoice, targetRole=targetRole,
                                                    owningBBUser=botState.client.usersDB.getUser(message.author.id),
                                                    desc=pollSubject)
        await menu.updateMessage()
        botState.client.reactionMenusDB[menuMsg.id] = menu
        botState.client.usersDB.getUser(message.author.id).addOwnedMenu(basedUser.OwnedMenuType.poll, menu)

    textCommandsDB.register("poll", cmd_poll, 0, forceKeepArgsCasing=True, allowDM=False,
                            signatureStr="**poll** *<subject>*\n**<option1 emoji> <option1 name>**\n...    ...\n*[kwargs]*",
                            shortHelp="Start a reaction-based poll. Each option must be on its own new line, as an emoji, " \
                                + "followed by a space, followed by the option name.",
                            longHelp="Start a reaction-based poll. Each option must be on its own new line, as an emoji, " \
                                + "followed by a space, followed by the option name. The `subject` is the question that users " \
                                + "answer in the poll and is optional, to exclude your subject simply give a new line.\n\n" \
                                + "__Optional Arguments__\nOptional arguments should be given by `name=value`, with each arg " \
                                    + "on a new line.\n" \
                                + "- Give `multiplechoice=no` to only allow one vote per person (default: yes).\n" \
                                + "- Give `target=@role mention` to limit poll participants only to users with the specified " \
                                    + "role.\n" \
                                + "- You may specify the length of the poll, with each time division on a new line. Acceptable " \
                                    + "time divisions are: `seconds`, `minutes`, `hours`, `days`. (default: minutes=5)")
    """


    @guildOnly()
    @basedCommand.basedCommand()
    @app_commands.command(name="drink",
                            description="Order a refreshing drink from the bar.")
    async def cmd_drink(self, interaction: Interaction):
        """Show a random drink message.
        """
        await interaction.response.send_message(random.choice(bbData.drinkMessages))


    @guildOnly()
    @basedCommand.basedCommand()
    @app_commands.command(name="premium",
                            description="Order something extra-special from the bar. Supply is very limited on these goodies!")
    async def cmd_drink_premium(self, interaction: Interaction):
        """Show a random premium drink message, with a global cooldown.
        """
        now = utcnow()
        if botState.premiumCooldownEnd is None or now > botState.premiumCooldownEnd:
            botState.premiumCooldownEnd = now + bbData.premiumDrinkTimeout
            await interaction.response.send_message(random.choice(bbData.premiumDrinkMessages))
        else:
            await interaction.response.send_message(bbData.premiumDrinkTimeoutMessage)

#endregion commands

async def setup(bot: client.BasedClient):
    await bot.add_cog(UserMiscCog(bot))
