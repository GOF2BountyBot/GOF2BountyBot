from typing import List, Tuple, Union, cast
import aiohttp

from github import Github, UnknownObjectException
from github.Issue import Issue
from github.Repository import Repository

from .asyncUtil import asyncWrap

class BasedGithub(Github):
    @asyncWrap
    def searchIssues(self, repo: Union[str, Repository], searchTerm: str, maxResults: int) -> Tuple[int, List[Issue]]:
        """Search through all pages of the github repository's issues for the top `maxResults` matches for the given search term.
        Searches are performed over issue titles and no other content.

        :param str repo: The repository in which to search for issues
        :param str searchTerm: The issue name to search for
        :param int maxResults: The maximum number of results to return
        :return: The total number of matches, followed by A list of 0-`maxResults` Issues that most closely match search Term
        :rtype: Tuple[int, List[Issue]]
        """
        results: List[Issue] = []
        currentPage = 0

        repoStr = repo if isinstance(repo, str) else repo.full_name

        allIssues = self.search_issues(f"is:issue repo:{repoStr} {searchTerm}")
        # Placing a dummy value in here to ensure the loop executes at least once. Python doesn't have while... do :(
        currentIssues: List[Issue] = [cast(Issue, None)]

        while currentIssues and len(results) < maxResults:
            currentIssues = allIssues.get_page(currentPage)
            currentPage += 1
            results += currentIssues[:min(maxResults, len(currentIssues) - 1)]

        return allIssues.totalCount, results


    @classmethod
    @asyncWrap
    def getIssueByNumber(cls, repo: Repository, issueNumber: int) -> Union[Issue, None]:
        """Get an issue by its number.

        :param str repo: The repository in which the issue was created
        :param int issueNumber: The number of the issue
        :return: The issue with the given number, or None if none exists
        :rtype: Union[Issue, None]
        """
        try:
            return repo.get_issue(issueNumber)
        except UnknownObjectException:
            return None


class GithubError(Exception):
    """Thrown when a Github API operation fails.
    """
    pass


async def getNewestTagOnRemote(httpClient: aiohttp.ClientSession, url: str) -> str:
    """Fetch the name of the latest tag on the given git remote.
    If the remote has no tags, empty string is returned.

    :param aiohttp.ClientSession httpClient: The ClientSession to request git info with
    :param str url: URL to the git remote to check
    :return: String name of the the latest tag on the remote at URL, if the remote at URL has any tags. Empty string otherwise
    :rtype: str 
    """
    async with httpClient.get(url) as resp:
        try:
            resp.raise_for_status()
            respJSON = await resp.json()
            return respJSON[0]["tag_name"]
        except (IndexError, KeyError, aiohttp.ContentTypeError, aiohttp.ClientResponseError):
            raise GithubError("Could not fetch latest release info from GitHub. Is the GitHub API down?")
            