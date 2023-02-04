from typing import Dict, List, Optional, Tuple, Type, Union, cast
from urllib.parse import quote_plus

from discord import Colour, Embed, InteractionType, Member, Message, User, app_commands, Interaction, ButtonStyle, HTTPException, ClientException
from discord.abc import Snowflake
from discord.app_commands import Range
from discord.ui import View, Button

from github import GithubException

from .. import client
from ..cfg import cfg
from ..cfg.cfg import basicAccessLevels
from ..cfg.schema import GitHubIssueType, gitHubIssueTypeIds, gitHubIssueIdTypes
from ..interactions import basedCommand
from ..interactions.basedApp import BasedCog
from ..lib.discordUtil import ZWSP, messageDescriptor
from ..lib import ids
from ..lib.timeUtil import td_format_noYM
from .util.transformers import BoolYesNo
from ..views.issues.bugReportModal import BugReportModal
from ..views.issues.issueReportModalBase import IssueReportModalBase
from ..views.issues.featureRequestModal import FeatureRequestModal
from ..views.issues.newItemAliasModal import NewItemAliasModal
from ..views.confirmView import ConfirmView
from ..views.cancelView import CancelView
from ..interactions.basedComponent import StaticComponents
from .util.EmbedEditorUtil import interactionErrorString
from ..logging import LogCategory

IssueTypeModal: Dict[GitHubIssueType, Type[IssueReportModalBase]] = {
    "Bug report": BugReportModal,
    "Feature request": FeatureRequestModal,
    "New item alias": NewItemAliasModal
}

MAX_ISSUE_ATTACHMENTS = 20

def makeIssueSubmitComponentArgs(issueTypeId: str, userId: str) -> str:
    return f"{issueTypeId}{userId}"


def deconstructIssueSubmitComponentArgs(args: str) -> Tuple[GitHubIssueType, int]:
    return gitHubIssueIdTypes[ids.idToIndex(args[0])], int(args[1:])


def makeIssueSubmitView(issueType: GitHubIssueType, userId: Union[int, str], disableAll: bool = False) -> View:
    view = View()
    _userId = userId if isinstance(userId, str) else str(userId)

    issueTypeId = ids.indexToID(gitHubIssueTypeIds[issueType])
    if len(issueTypeId) > 1:
        raise ValueError(f"Too many github issue types exist to construct issue submit view component args. The maximum issue type id is {ids.maxIndex(1)}.")

    args = makeIssueSubmitComponentArgs(issueTypeId, _userId)

    cancelButton = Button(style=ButtonStyle.red, label="cancel", disabled=disableAll)
    cancelButton = StaticComponents.Clear_View(cancelButton, args=_userId)
    view.add_item(cancelButton)

    submitButton = Button(style=ButtonStyle.green, label="submit", disabled=disableAll)
    submitButton = StaticComponents.User_IssueCreator_Submit(submitButton, args=args)
    view.add_item(submitButton)

    editButton = Button(style=ButtonStyle.blurple, label="edit", disabled=disableAll)
    editButton = StaticComponents.User_IssueCreator_Edit(editButton, args=args)
    view.add_item(editButton)

    addAttachmentsButton = Button(style=ButtonStyle.blurple, label="add attachments", disabled=disableAll)
    addAttachmentsButton = StaticComponents.User_IssueCreator_Add_Attachments(addAttachmentsButton, args=args)
    view.add_item(addAttachmentsButton)

    removeAttachmentsButton = Button(style=ButtonStyle.blurple, label="remove attachments", disabled=disableAll)
    removeAttachmentsButton = StaticComponents.User_IssueCreator_Remove_Attachments_Select(removeAttachmentsButton, args=args)
    view.add_item(removeAttachmentsButton)
    
    return view


def gitHubIssueHeader(user: Union[User, Member], issueType: GitHubIssueType) -> str:
    return f"<img src=\"{user.display_avatar.url}\" align=\"left\" width=\"96\" height=\"96\" hspace=\"10\"></img> **Issue by [{user.name}#{user.discriminator}]**\n" \
        + f"<!-- User ID: {user.id} -->\n\n" \
        + "_Originally opened via discord command_\n" \
        + f"_Issue type: {issueType}_\n\n" \
        + "----\n\n"


class UserGithubCog(BasedCog):
#region util

    async def messageForInteraction(self, interaction: Interaction, funcName: str, staticComponentId: StaticComponents) -> Optional[Message]:
        """TODO: This appears to acknowledge the interaction"""
        if interaction.message is not None: return interaction.message
        # await interaction.response.defer(thinking=False)
        try:
            message = await interaction.original_response()
        except (ClientException, HTTPException) as e:
            self.bot.logger.log(type(self).__name__, funcName,
                                "on-message static component triggered for non-message-based interaction: " \
                                    + interactionErrorString(interaction, staticComponentId),
                                category=LogCategory.staticComponents, eventType="MESSAGE_FETCH_FAIL", exception=e, interaction=interaction)
            await interaction.response.send_message(cfg.defaultEmojis.cancel + " This type of interaction is not valid here.", ephemeral=True)
            return None

        if not message.embeds:
            self.bot.logger.log(type(self).__name__, funcName,
                                "static component that requires an embed triggered for a message without an embed: " \
                                    + interactionErrorString(interaction, staticComponentId) + " message: " + messageDescriptor(message),
                                category=LogCategory.staticComponents, eventType="NO_EMBED", interaction=interaction)
            await interaction.response.send_message(cfg.defaultEmojis.cancel + " This type of interaction is not valid here.", ephemeral=True)
            return None
        
        return message

#endregion
#region components

    @BasedCog.staticComponentCallback(StaticComponents.User_IssueCreator_Submit)
    async def issueCreator_submit(self, interaction: Interaction, args: str):
        issueType, userId = deconstructIssueSubmitComponentArgs(args)
        if not self.CommonStaticComponentsCog.ensureOwnership(interaction, userId): return

        message = await self.messageForInteraction(interaction, UserGithubCog.issueCreator_submit.__name__, StaticComponents.User_IssueCreator_Submit)
        if message is None: return
        embed = message.embeds[0]

        if embed.title is None:
            await interaction.response.send_message(f"{cfg.defaultEmojis.cancel} This type of interaction is not valid here.", ephemeral=True)
            raise ValueError("Embed has no title")

        disabledView = makeIssueSubmitView(issueType, userId, disableAll=True)
        await interaction.response.edit_message(view=disabledView)
        resultsMessage = await message.channel.send(f"{cfg.defaultEmojis.longProcess} {interaction.user.mention} Sending issue...")

        header = gitHubIssueHeader(interaction.user, issueType)
        body = "\n\n".join(f"**{f.name}**\n{f.value}" for f in embed.fields if f.value and f.value != ZWSP)

        deleteMeView = View()
        deleteMeButton = Button(emoji=cfg.defaultEmojis.delete.sendable)
        deleteMeButton = StaticComponents.Delete_Message(deleteMeButton, str(userId))
        deleteMeView.add_item(deleteMeButton)

        try:
            issue = await self.GithubUtilCog.createIssue(embed.title, body=header + body, labels=cfg.githubIssueTypeLabels.get(issueType, []))
        except GithubException as e:
            await resultsMessage.edit(content=f"{cfg.defaultEmojis.cancel} {interaction.user.mention} The new issue was rejected by GitHub: {e.status} {e.data}\n\n" \
                                            + f"Please check your issue content and try again later, or report this as a bug on the project's github page, quoting interaction ID: `{interaction.id}`",
                                            view=deleteMeView)
            view = makeIssueSubmitView(issueType, userId)
            await interaction.response.edit_message(view=view)
            return
        
        embed = Embed(colour=Colour.green())
        embed.set_author(name=f"#{issue.number}: {issue.title}", icon_url=interaction.user.display_avatar.url, url=issue.html_url)
        
        if issue.labels:
            labelsStr = ', '.join(cfg.githubLabelNames.get(x.name, x.name) for x in issue.labels)
            embed.add_field(name="Labels", value=f"*{labelsStr}*")

        await resultsMessage.edit(content=f"{cfg.defaultEmojis.submit} Your new issue has been created! If more information is required before the issue can be worked on, comments will be posted on GitHub.\n\nTrack development progress here:",
                                    embed=embed,
                                    view=deleteMeView)
        await interaction.edit_original_response(content=f"Issue created here: {issue.html_url}")
        
    
    @BasedCog.staticComponentCallback(StaticComponents.User_IssueCreator_Edit)
    async def issueCreator_edit(self, interaction: Interaction, args: str):
        issueType, userId = deconstructIssueSubmitComponentArgs(args)
        if not self.CommonStaticComponentsCog.ensureOwnership(interaction, userId): return

        message = await self.messageForInteraction(interaction, UserGithubCog.issueCreator_submit.__name__, StaticComponents.User_IssueCreator_Submit)
        if message is None: return

        modal = IssueTypeModal[issueType].fromEmbed(message.embeds[0])
        await interaction.response.send_modal(modal)

        if await modal.wait():
            await interaction.edit_original_response(content="🛑 Out of time, Please try this button again.")
            return

        embed = modal.toEmbed(interaction.user)
        await modal.interaction.response.edit_message(embed=embed)


    @BasedCog.staticComponentCallback(StaticComponents.User_IssueCreator_Add_Attachments)
    async def issueCreator_add_attachments(self, interaction: Interaction, args: str):
        issueType, userId = deconstructIssueSubmitComponentArgs(args)
        if not self.CommonStaticComponentsCog.ensureOwnership(interaction, userId): return

        message = await self.messageForInteraction(interaction, UserGithubCog.issueCreator_add_attachments.__name__, StaticComponents.User_IssueCreator_Add_Attachments)
        if message is None: return
        embed = message.embeds[0]
        
        try:
            attachmentsFieldIndex, attachmentsField = next((i, f) for i, f in enumerate(embed.fields) if f.name == "Attachments")
        except StopIteration:
            await interaction.response.send_message(f"{cfg.defaultEmojis.cancel} This type of interaction is not valid here.", ephemeral=True)
            raise ValueError("Embed has no attachments field")

        numExistingAttachments = 0 if attachmentsField.value is None or attachmentsField.value == "" else len(attachmentsField.value.split("\n"))
        if numExistingAttachments >= MAX_ISSUE_ATTACHMENTS:
            await interaction.response.send_message(f"This issue already has the maximum number of attachments ({MAX_ISSUE_ATTACHMENTS}).", ephemeral=True)
            return

        view = makeIssueSubmitView(issueType, userId)
        disableView = makeIssueSubmitView(issueType, userId, disableAll=True)
        await interaction.response.edit_message(view=disableView)

        uploadView = CancelView()
        attachmentsRequestMessage = await message.channel.send(
            f"{interaction.user.mention} Send one message in this channel with your attachments, within {td_format_noYM(cfg.timeouts.menuInteractionDefault)}.\n" 
            + "If you need to add more attachments, you can simply press this button again.\n" \
            + "Your attachments will be used in your GitHub issue, so please do not delete your message later!",
            view=uploadView)

        def check(response: Union[Message, Interaction]) -> bool:
            if isinstance(response, Message):
                return response.author.id == userId and len(response.attachments) > 0
            response = cast(Interaction, response)
            # TODO: I don't check that the interaction was on the message created above! It could be any button with this CustomID.
            return response.user.id == userId and response.type == InteractionType.component \
                and response.data is not None and response.data.get("custom_id", None) == uploadView.cancel.custom_id
        
        try:
            attachmentsMessage: Union[Message, Interaction] = \
                await self.bot.multiWaitFor(["message", "interaction"], check=check,
                                            timeout=cfg.timeouts.menuInteractionDefault.total_seconds())
        except TimeoutError:
            await attachmentsRequestMessage.edit(content=f"~~Send one message in this channel with your attachments, within {td_format_noYM(cfg.timeouts.menuInteractionDefault)}.~~\nOut of time! Please try this button again.")
            await interaction.edit_original_response(view=view)
            return

        if isinstance(attachmentsMessage, Interaction):
            uploadView.disableAll()
            await attachmentsMessage.response.edit_message(content="🛑 Attachment upload cancelled.", view=uploadView)
            await interaction.edit_original_response(view=view)
            return
        
        remainingAttachmentSlots = MAX_ISSUE_ATTACHMENTS - numExistingAttachments - len(attachmentsMessage.attachments)
        if remainingAttachmentSlots < 0:
            truncatedAttachmentsTxt = f"\nThe maximum number of attachments has been reached, the last {abs(remainingAttachmentSlots)} of your attachments were ignored."
            end = remainingAttachmentSlots
        else:
            truncatedAttachmentsTxt = ""
            end = len(attachmentsMessage.attachments)

        attachmentsTxt = "\n".join(f"[{a.filename}]({a.url})" for a in attachmentsMessage.attachments[:end])

        if attachmentsField.value is None:
            attachmentsField.value = attachmentsTxt
        else:
            attachmentsField.value += "\n" + attachmentsTxt

        embed.set_field_at(attachmentsFieldIndex, name=attachmentsField.name, value=attachmentsField.value, inline=attachmentsField.inline)
        
        uploadView.disableAll()
        deleteMeView = View()
        deleteMeButton = Button(emoji=cfg.defaultEmojis.delete.sendable)
        deleteMeButton = StaticComponents.Delete_Message(deleteMeButton, str(userId))
        deleteMeView.add_item(deleteMeButton)

        await attachmentsMessage.reply(f"{cfg.defaultEmojis.submit} Attachments added successfully.{truncatedAttachmentsTxt}", view=deleteMeView)
        await attachmentsMessage.add_reaction("👍")
        await attachmentsRequestMessage.delete()
        await interaction.edit_original_response(view=view, embed=embed)


    @BasedCog.staticComponentCallback(StaticComponents.User_IssueCreator_Remove_Attachments_Select)
    async def issueCreator_remove_attachments_select(self, interaction: Interaction, args: str):
        ...


    @BasedCog.staticComponentCallback(StaticComponents.User_IssueCreator_Remove_Attachments)
    async def issueCreator_remove_attachments_end(self, interaction: Interaction, args: str):
        ...

#endregion components
#region commands

    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="Github")
    @app_commands.describe(
        send_private="If Yes, the results will be sent in a message that only you can see. (Defaults to Yes)"
    )
    @app_commands.command(name="github-search",
                            description="Search for GitHub issues with the given name, getting the " \
                                        + f"{cfg.githubIssueSearchNumResults} most similar issues.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_issue_search(self, interaction: Interaction, search: str, send_private: BoolYesNo = BoolYesNo.Yes):
        """Search for github issues with the given title.
        """
        await interaction.response.defer(thinking=True, ephemeral=bool(send_private))
        
        totalResults, issues = await self.bot.githubClient.searchIssues(self.bot.githubRepo, search, cfg.githubIssueSearchNumResults)
        numIssues = len(issues)

        if numIssues > 0 and numIssues != totalResults:
            desc = f"Search term: `{search}`\nShowing the first {cfg.githubIssueSearchNumResults} of {totalResults} matches. See all results [here](" \
                    + f"https://github.com/{self.bot.githubRepo.full_name}/issues?q=is%3Aissue+{quote_plus(search)}+in%3Atitle)."
        else:
            desc = f"Search term: `{search}`"

        resultsEmbed = Embed(title="GitHub Issues Search", description=desc, colour=Colour.random())
        resultsEmbed.set_footer(text="GitHub repository linked in /source")
        resultsEmbed.set_thumbnail(url=self.bot.user.display_avatar.with_size(64).url if self.bot.user is not None else None)

        if issues:
            for issue in issues:
                labelsStr = ', '.join(cfg.githubLabelNames.get(x.name, x.name) for x in issue.labels)
                resultsEmbed.add_field(name=("🟢" if issue.state == "open" else "🔴") + " " + issue.title,
                                        value=f"[#{issue.number}]({issue.html_url}) *({labelsStr})*")
        else:
            resultsEmbed.add_field(name="No results found", value=ZWSP)

        await interaction.followup.send(embed=resultsEmbed)

    
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="Github")
    @app_commands.describe(
        send_private="If Yes, the results will be sent in a message that only you can see. (Defaults to Yes)"
    )
    @app_commands.command(name="github-get",
                            description="Get the GitHub issue with the given number.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_issue_get(self, interaction: Interaction, issue_number: Range[int, 1], send_private: BoolYesNo = BoolYesNo.Yes):
        """Get the GitHub issue with the given number.
        """
        await interaction.response.defer(ephemeral=bool(send_private), thinking=True)
        issue = await self.bot.githubClient.getIssueByNumber(self.bot.githubRepo, issue_number)

        if issue is None:
            await interaction.followup.send(":x: Unknown issue number!", ephemeral=True)
            return

        labelsStr = ', '.join(cfg.githubLabelNames.get(x.name, x.name) for x in issue.labels)
        resultsEmbed = Embed(title="GitHub Issue Lookup",
                            description="__" + ('🟢' if issue.state == 'open' else '🔴') \
                                        + f" [#{issue.number} {issue.title}]({issue.html_url})__\n" \
                                        + (f"> `{labelsStr}`\n" if labelsStr else "")
                                        + f"\n{issue.body}",
                            colour=Colour.random())

        resultsEmbed.set_footer(text="GitHub repository linked in /source")
        resultsEmbed.set_thumbnail(url=self.bot.user.display_avatar.with_size(64).url if self.bot.user is not None else None)

        await interaction.followup.send(embed=resultsEmbed)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="Github")
    @app_commands.command(name="submit-bug-report",
                            description="Submit a new bug report to the project's GitHub repository (see /source)")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_issue_submit_bug(self, interaction: Interaction):
        await self.shared_issue_submit(interaction, "Bug report")


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="Github")
    @app_commands.command(name="submit-feature-request",
                            description="Submit a new feature request to the project's GitHub repository (see /source)")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_issue_submit_feature(self, interaction: Interaction):
        await self.shared_issue_submit(interaction, "Feature request")
        

    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="Github")
    @app_commands.command(name="submit-issue",
                            description="Submit a new issue to the project's GitHub repository (see /source)")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_issue_submit(self, interaction: Interaction, issue_type: GitHubIssueType):
        await self.shared_issue_submit(interaction, issue_type)


    async def shared_issue_submit(self, interaction: Interaction, issueType: GitHubIssueType):
        confirm = ConfirmView(confirmLabel="Yes", cancelLabel="No")
        await interaction.response.send_message("Have you checked that a similar issue does not already exist with `/github-search`?",
                                                ephemeral=True, view=confirm)

        confirm.disableAll()

        if await confirm.wait():
            await interaction.edit_original_response(content="🛑 Out of time, issue submission cancelled.", view=confirm)
            return
        elif confirm.cancelled:
            await confirm.interaction.response.edit_message(content="🛑 Issue submission cancelled.", view=confirm)
            return

        modal = IssueTypeModal[issueType]()
        await confirm.interaction.response.send_modal(modal)
        await interaction.edit_original_response(view=confirm)

        if await modal.wait():
            await interaction.edit_original_response(content="🛑 Out of time, issue submission cancelled.", view=confirm)
            return

        embed = modal.toEmbed(interaction.user)
        view = makeIssueSubmitView(issueType, interaction.user.id)
        await modal.interaction.response.edit_message(content=None, embed=embed, view=view)

#endregion commands

async def setup(bot: client.BasedClient):
    # Casting here because for some reason pyright doesn't think SerializableDiscordObject is a Snowflake,
    # even though it extends discord.Object
    await bot.add_cog(UserGithubCog(bot), guilds=cast(List[Snowflake], cfg.developmentGuilds))
