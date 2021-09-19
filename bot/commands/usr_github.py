from typing import Dict, List, Union, cast
import discord

from . import commandsDB as botCommands
from .. import botState, lib
from ..lib.discordUtil import asyncWrap
from ..cfg import cfg
from ..users import basedGuild, basedUser
from datetime import datetime

from github import Github
from github.Issue import Issue
from github.Issue import Issue
from github import UnknownObjectException
import re


botCommands.addHelpSection(0, "github")


ISSUE_TEMPLATE_NAME_SEARCH = re.compile("name: ")
ISSUE_TEMPLATE_ABOUT_SEARCH = re.compile("about: ")


@asyncWrap
def searchIssues(searchTerm: str) -> List[Issue]:
    """Search through all pages of the github repository's issues for the top 3 matches for the given search term.
    Searches are performed over issue titles and no other content.

    :param str searchTerm: The issue name to search for
    :return: A list of 0-3 Issues that most closely match search Term
    :rtype: List[Issue]
    """
    results: List[Issue] = []
    currentPage = 0

    allIssues = botState.githubClient.search_issues(f"is:issue repo:{cfg.githubIssuesRepo} {searchTerm}")
    currentIssues: List[Issue] = allIssues.get_page(currentPage)

    while currentIssues:
        results += currentIssues
        currentPage += 1
        currentIssues = allIssues.get_page(currentPage)

    return results


@asyncWrap
def getIssueByNumber(issueNumber: int) -> Union[Issue, None]:
    """Get an issue by its number.

    :param int issueNumber: The number of the issue
    :return: The issue with the given number, or None if none exists
    :rtype: Union[Issue, None]
    """
    try:
        return botState.githubRepo.get_issue(issueNumber)
    except UnknownObjectException:
        return None


# @asyncWrap
# def getIssueTemplates() -> Dict[str, str]:
#     """Get a dictionary mapping issue template names to their about sections.
#     """
#     issueData: Dict[str, str] = {}
#     for templateName in cfg.githubIssueTemplates:
#         try:
#             content = botState.githubRepo.get_contents(f".github/ISSUE_TEMPLATE/{templateName}.md").decoded_content.decode()
#         except Exception as e:
#             botState.logger.log("usr_github", "getIssueTemplates", "", exception=e)
#         else:
#             formattedName = next(ISSUE_TEMPLATE_NAME_SEARCH.finditer(content))

#             issueData[templateName]


async def cmd_issue_search(message : discord.Message, args : str, isDM : bool):
    """Search for github issues with the given title.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing an issue title to search for
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if not args:
        await message.reply(":x: Please give an issue name to search for!")
        return
    
    await lib.discordUtil.startLongProcess(message)
    issues: List[Issue] = await searchIssues(args)

    resultsEmbed = discord.Embed(title="GitHub Issues Search", description=f"Search term: `{args}`\n** **",
                                    colour=discord.colour.Colour.random())
    prefix = cfg.defaultCommandPrefix if isDM else botState.guildsDB.getGuild(message.guild.id).commandPrefix
    resultsEmbed.set_footer(text=f"GitHub repository linked in `{prefix}source`")
    resultsEmbed.set_thumbnail(url=botState.client.user.avatar_url_as(size=64))
    if issues:
        for issue in issues:
            labelsStr = ', '.join(cfg.githubLabelNames.get(x.name, x.name) for x in issue.labels)
            resultsEmbed.add_field(name=("🟢" if issue.state == "open" else "🔴") + " " + issue.title,
                                    value=f"[#{issue.number}]({issue.url}) *({labelsStr})*")
    else:
        resultsEmbed.add_field(name="No results found", value="​")

    await message.reply(embed=resultsEmbed)
    await lib.discordUtil.endLongProcess(message)

botCommands.register("issue search", cmd_issue_search, 0, forceKeepArgsCasing=True, allowDM=True,
                        aliases=["bug search", "issues search", "git search", "github search", "feature search"],
                        helpSection="github", signatureStr="**issue search <issue-name>**",
                        shortHelp="Search for GitHub issues with the given name, getting the 3 most similar issues.")


async def cmd_issue_get(message : discord.Message, args : str, isDM : bool):
    """Get the GitHub issue with the given number.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing an issue number to fetch
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if not args:
        await message.reply(":x: Please give an issue number to look up!")
        return
    
    if not lib.stringTyping.isInt(args):
        await message.reply(":x: That's not a number!")
        return

    issueNum = int(args)
    if issueNum < 1:
        await message.reply(":x: Your issue number must be at least 1!")
        return
    
    await lib.discordUtil.startLongProcess(message)
    issue: Issue = await getIssueByNumber(issueNum)

    if issue is None:
        await message.reply(":x: Unknown issue number!")
        await lib.discordUtil.endLongProcess(message)
        return

    labelsStr = ', '.join(cfg.githubLabelNames.get(x.name, x.name) for x in issue.labels)
    resultsEmbed = discord.Embed(title="GitHub Issue Lookup",
                                description="__" + ('🟢' if issue.state == 'open' else '🔴') \
                                            + f" [#{issue.number} {issue.title}]({issue.url})__\n" \
                                            + (f"> `{labelsStr}`\n" if labelsStr else "")
                                            + f"\n{issue.body}",
                                colour=discord.colour.Colour.random())
    prefix = cfg.defaultCommandPrefix if isDM else botState.guildsDB.getGuild(message.guild.id).commandPrefix
    resultsEmbed.set_footer(text=f"GitHub repository linked in `{prefix}source`")
    resultsEmbed.set_thumbnail(url=botState.client.user.avatar_url_as(size=64))

    await message.reply(embed=resultsEmbed)
    await lib.discordUtil.endLongProcess(message)

botCommands.register("issue get", cmd_issue_get, 0, forceKeepArgsCasing=True, allowDM=True,
                        aliases=["bug get", "issues get", "git get", "github get", "feature get"],
                        helpSection="github", signatureStr="**issue get <issue-number>**",
                        shortHelp="Get the GitHub issue with the given number.")


# async def cmd_issue_submit(message : discord.Message, args : str, isDM : bool):
#     """Submit a new GitHub issue.

#     :param discord.Message message: the discord message calling the command
#     :param str args: ignored
#     :param bool isDM: Whether or not the command is being called from a DM channel
#     """
#     if botState.usersDB.idExists(message.author.id):
#         bUser: basedUser.BasedUser = botState.usersDB.getUser(message.author.id)
#         now = datetime.utcnow()
#         if bUser.githubIssueSubmitDelayEnd is not None and bUser.githubIssueSubmitDelayEnd > now:
#             await message.reply(f"⏱ Please wait {lib.timeUtil.td_format_noYM(bUser.githubIssueSubmitDelayEnd - now)}" \
#                                 + " before submitting another issue.")
#             return
#     else:
#         bUser: basedUser.BasedUser = botState.usersDB.addID(message.author.id)

#     await lib.discordUtil.startLongProcess(message)
#     # templates = botState.githubRepo.

#     if issue is None:
#         await message.reply(":x: Unknown issue number!")
#         await lib.discordUtil.endLongProcess(message)
#         return

#     labelsStr = ', '.join(cfg.githubLabelNames.get(x.name, x.name) for x in issue.labels)
#     resultsEmbed = discord.Embed(title="GitHub Issue Lookup",
#                                 description="__" + ('🟢' if issue.state == 'open' else '🔴') \
#                                             + f" [#{issue.number} {issue.title}]({issue.url})__\n" \
#                                             + (f"> `{labelsStr}`\n" if labelsStr else "")
#                                             + f"\n{issue.body}",
#                                 colour=discord.colour.Colour.random())
#     prefix = cfg.defaultCommandPrefix if isDM else botState.guildsDB.getGuild(message.guild.id).commandPrefix
#     resultsEmbed.set_footer(text=f"GitHub repository linked in `{prefix}source`")
#     resultsEmbed.set_thumbnail(url=botState.client.user.avatar_url_as(size=64))

#     await message.reply(embed=resultsEmbed)
#     await lib.discordUtil.endLongProcess(message)

# botCommands.register("issue submit", cmd_issue_submit, 0, forceKeepArgsCasing=True, allowDM=True,
#                         aliases=["bug submit", "issues submit", "git submit", "github submit", "feature submit"],
#                         helpSection="github", signatureStr="**issue submit <issue-number>**",
#                         shortHelp="Submit a new issue to GitHub. For more options, " \
#                                     + "submit your issue directly through GitHub, with the URL found in `source`.")


async def cmd_issue(message : discord.Message, args : str, isDM : bool):
    """Various github issues actions

    :param discord.Message message: the discord message calling the command
    :param str args: string containing subcommand name followed by arguments
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    prefix = cfg.defaultCommandPrefix if isDM else botState.guildsDB.getGuild(message.guild.id).commandPrefix
    if args == "":
        await message.reply(mention_author=False,
                            content=f":x: Please give a subcommand! See `{prefix}help issue` for possible commands.")
        return

    if botState.githubRepo is None or botState.githubClient is None:
        await message.reply("GitHub commands are currently disabled. " \
                            + "Please manage issues through the GitHub website directly.")

    argsSplit = args.split(" ")

    issueCmds = {"search": cmd_issue_search,
                "get": cmd_issue_get}
    
    if argsSplit[0] in issueCmds:
        await issueCmds[argsSplit[0]](message, args[len(argsSplit[0])+1:], isDM)
    else:
        await message.reply(mention_author=False,
                            content=f":x: Unknown subcommand! See `{prefix}help issue` for possible commands.")

botCommands.register("issue", cmd_issue, 0, allowDM=True, helpSection="github", signatureStr="**issue <subcommand> <args>**",
                        aliases=["git", "github", "bug", "feature", "issues"], forceKeepArgsCasing=True,
                        shortHelp="Look up and submit new bug reports and feature requests.",
                        longHelp="Look up bugs and feature requests, and submit new ones!\n" \
                            + "To do more with the project's issues, please see the project GitHub repository, " \
                            + "linked in the `source` command.\n\n" \
                            + "subcommands:\n- `search`, to find issues by name\n" \
                            + "- `get`, to find issues by number")
