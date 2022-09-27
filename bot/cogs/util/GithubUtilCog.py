from typing import Optional, Union, cast, List

from discord.abc import Snowflake
from github import Github, UnknownObjectException
from github.Repository import Repository
from github.Issue import Issue

from ...interactions.basedApp import BasedCog
from ... import client, lib
from ...lib.discordUtil import asyncWrap
from ...cfg import cfg
import re

ISSUE_TEMPLATE_NAME_SEARCH = re.compile("name: ")
ISSUE_TEMPLATE_ABOUT_SEARCH = re.compile("about: ")

class GithubUtilCog(BasedCog):
    def __init__(self, bot: "client.BasedClient", *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self._githubClient: Optional[Github] = None
        self._githubRepo: Optional[Repository] = None
        self._githubLoaded = False


    async def cog_load(self):
        """initialized the github client
        """
        if cfg.githubAccessToken and cfg.githubIssuesRepo:
            try:
                self._githubClient = Github(cfg.githubAccessToken)
            except Exception as e:
                self.bot.logger.log(GithubUtilCog.__name__, "cog_load", "", exception=e)
            else:
                try:
                    self._githubRepo = self.githubClient.get_repo(cfg.githubIssuesRepo)
                except Exception as e:
                    self.bot.logger.log(GithubUtilCog.__name__, "cog_load", "", exception=e)
                else:
                    self._githubLoaded = True
                    
        return await super().cog_load()

#region properties

    @property
    def githubRepo(self):
        """The repository in which to create issues.
        Only available after on_ready.

        :raises lib.exceptions.NotReady: Repo not loaded yet
        :return: The repository in which to create issues.
        :rtype: GitHub
        """
        if not self._githubLoaded:
            raise lib.exceptions.NotReady("Not yet loaded. githubRepo is only available after cog_load.")
        return cast(Repository, self._githubRepo)


    @property
    def githubClient(self):
        """The client for accessing the GitHub API.
        Only available after on_ready.

        :raises lib.exceptions.NotReady: Client not loaded yet
        :return: The client for accessing the GitHub API.
        :rtype: GitHub
        """
        if not self._githubLoaded:
            raise lib.exceptions.NotReady("Not yet loaded. githubClient is only available after cog_load.")
        return cast(Github, self._githubClient)

#endregion
#region util

    
    @asyncWrap
    def searchIssues(self, searchTerm: str, maxIssues: int = cfg.githubIssueSearchNumResults) -> List[Issue]:
        """Search through all pages of the github repository's issues for the top `maxIssues` matches for the given search term.
        Searches are performed over issue titles and no other content.

        :param str searchTerm: The issue name to search for
        :param int maxIssues: The maximum number of issues to receive (Default cfg.githubIssueSearchNumResults)
        :return: A list of 0-`maxIssues` Issues that most closely match search Term
        :rtype: List[Issue]
        """
        allIssues = self.githubClient.search_issues(f"is:issue repo:{cfg.githubIssuesRepo} {searchTerm}")
        results: List[Issue] = []
        currentPage = -1

        while len(results) < maxIssues:
            currentPage += 1
            currentIssues = allIssues.get_page(currentPage)
            results += currentIssues[:min(maxIssues, len(currentIssues))]
            if not currentIssues: break

        return results


    @asyncWrap
    def getIssueByNumber(self, issueNumber: int) -> Union[Issue, None]:
        """Get an issue by its number.

        :param int issueNumber: The number of the issue
        :return: The issue with the given number, or None if none exists
        :rtype: Union[Issue, None]
        """
        try:
            return self.githubRepo.get_issue(issueNumber)
        except UnknownObjectException:
            return None

#endregion

async def setup(bot: client.BasedClient):
    # Casting here because for some reason pyright doesn't think SerializableDiscordObject is a Snowflake,
    # even though it extends discord.Object
    await bot.add_cog(GithubUtilCog(bot), guilds=cast(List[Snowflake], cfg.developmentGuilds))
    