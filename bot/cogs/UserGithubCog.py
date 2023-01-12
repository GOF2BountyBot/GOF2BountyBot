from typing import List, cast
from urllib.parse import quote_plus

from discord import Colour, Embed, app_commands, Interaction
from discord.abc import Snowflake
from discord.app_commands import Range

from .. import client
from ..cfg import cfg
from ..cfg.cfg import basicAccessLevels
from ..interactions import basedCommand
from ..interactions.basedApp import BasedCog
from ..lib.discordUtil import ZWSP
from .util.transformers import BoolYesNo


class UserGithubCog(BasedCog):
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


async def setup(bot: client.BasedClient):
    # Casting here because for some reason pyright doesn't think SerializableDiscordObject is a Snowflake,
    # even though it extends discord.Object
    await bot.add_cog(UserGithubCog(bot), guilds=cast(List[Snowflake], cfg.developmentGuilds))
