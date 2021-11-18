from typing import cast
import discord
from github.Label import Label

from . import commandsDB as botCommands
from .. import botState, lib
from ..cfg import cfg
from .usr_github import getIssueByNumber
from github.Issue import Issue


botCommands.addHelpSection(3, "github")


async def dev_cmd_issue_open(message: discord.Message, args: str, isDM: bool):
    """Send a pretty looking message saying that a new issue has been opened, and delete the calling message.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing an issue number
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if not args:
        await message.reply(":x: Please give an issue number to search for!")
        return
    elif not lib.stringTyping.isInt(args):
        await message.reply(":x: That's not a number!")
        return
        
    issueNum = int(args)
    if issueNum < 1:
        await message.reply(":x: Your issue number must be at least 1!")
        return

    issue: Issue = await getIssueByNumber(issueNum)

    if issue is None:
        await message.reply(":x: Unknown issue number!")
        return

    issueEmbed = discord.Embed()
    issueEmbed.colour = discord.Colour.green()
    issueEmbed.description = f"[#{args}]({issue.html_url}): {issue.title}"

    if any(cast(Label, i).name == "bug" for i in issue.labels):
        emoji = cfg.defaultEmojis.bug
    elif any(cast(Label, i).name == "enhancement" for i in issue.labels):
        emoji = cfg.defaultEmojis.feature
    elif any(cast(Label, i).name == "game balance" for i in issue.labels):
        emoji = cfg.defaultEmojis.gameBalance
    elif any(cast(Label, i).name == "optimization" for i in issue.labels):
        emoji = cfg.defaultEmojis.optimisation
    else:
        emoji = cfg.defaultEmojis.newIssue

    issueEmbed.set_author(name=f"{emoji.sendable} New Issue Created", url=issue.html_url,
                            icon_url=str(issue.user.avatar_url))

    if issue.labels:
        labelsStr = ', '.join(cfg.githubLabelNames.get(x.name, x.name) for x in issue.labels)
        issueEmbed.add_field(name="Labels", value=f"*{labelsStr}*")

    await message.channel.send(embed=issueEmbed)
    await message.delete()

botCommands.register("gitopen", dev_cmd_issue_open, 3, forceKeepArgsCasing=True, allowDM=True,
                        aliases=["gitnew"], helpSection="github", signatureStr="**gitopen <issue-number>**",
                        shortHelp="Send a short message with details of a new github issue.")


async def dev_cmd_issue_close(message: discord.Message, args: str, isDM: bool):
    """Send a pretty looking message saying that a new issue has been closed, and delete the calling message.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing an issue number
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if not args:
        await message.reply(":x: Please give an issue number to search for!")
        return
    elif not lib.stringTyping.isInt(args):
        await message.reply(":x: That's not a number!")
        return
        
    issueNum = int(args)
    if issueNum < 1:
        await message.reply(":x: Your issue number must be at least 1!")
        return

    issue: Issue = await getIssueByNumber(issueNum)

    if issue is None:
        await message.reply(":x: Unknown issue number!")
        return

    issueEmbed = discord.Embed()
    issueEmbed.colour = discord.Colour.red()
    issueEmbed.description = f"[#{args}]({issue.html_url}): {issue.title}"

    if any(cast(Label, i).name == "bug" for i in issue.labels):
        emoji = cfg.defaultEmojis.bug
    elif any(cast(Label, i).name == "enhancement" for i in issue.labels):
        emoji = cfg.defaultEmojis.feature
    elif any(cast(Label, i).name == "game balance" for i in issue.labels):
        emoji = cfg.defaultEmojis.gameBalance
    elif any(cast(Label, i).name == "optimization" for i in issue.labels):
        emoji = cfg.defaultEmojis.optimisation
    else:
        emoji = cfg.defaultEmojis.issueClosed

    issueEmbed.set_author(name=f"{emoji.sendable} Issue Closed", url=issue.html_url,
                            icon_url=str(issue.user.avatar_url))

    if issue.labels:
        labelsStr = ', '.join(cfg.githubLabelNames.get(x.name, x.name) for x in issue.labels)
        issueEmbed.add_field(name="Labels", value=f"*{labelsStr}*")

    await message.channel.send(embed=issueEmbed)
    await message.delete()

botCommands.register("gitclose", dev_cmd_issue_close, 3, forceKeepArgsCasing=True, allowDM=True,
                        aliases=["gitold"], helpSection="github", signatureStr="**gitclose <issue-number>**",
                        shortHelp="Send a short message with details of a closed github issue.")
