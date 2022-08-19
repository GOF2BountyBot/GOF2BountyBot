from typing import List, cast, TYPE_CHECKING
from .. import client
from discord import Colour, app_commands, Interaction, Embed
from discord.abc import Snowflake
from discord.app_commands import Range
from ..cfg import cfg
from ..cfg.cfg import basicAccessLevels
from ..interactions import basedCommand
from ..interactions.basedApp import BasedCog
from typing import List, cast
from enum import Enum


class OpenClose(Enum):
    open = "Opened"
    close = "Closed"


class DevGithubCog(BasedCog):
    def __init__(self, bot: client.BasedClient, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)

#region commands

    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer)
    @app_commands.command(name="announce-issue",
                            description="Send a pretty message saying that a Github issue has been opened/closed.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_announce_issue(self, interaction: Interaction, issue_number: Range[int, 1, ...], action: OpenClose):
        """Send a pretty looking message saying that an issue has been opened/closed.
        """
        issue = await self.GithubUtilCog.getIssueByNumber(issue_number)

        if issue is None:
            await interaction.response.send_message(":x: Unknown issue number!", ephemeral=True)
            return

        issueEmbed = Embed()
        issueEmbed.colour = Colour.green() if action == OpenClose.open else Colour.red()
        issueEmbed.description = f"[#{issue_number}]({issue.html_url}): {issue.title}"

        if any(i.name == "bug" for i in issue.labels):
            emoji = cfg.defaultEmojis.bug
        elif any(i.name == "enhancement" for i in issue.labels):
            emoji = cfg.defaultEmojis.feature
        elif any(i.name == "game balance" for i in issue.labels):
            emoji = cfg.defaultEmojis.gameBalance
        elif any(i.name == "optimization" for i in issue.labels):
            emoji = cfg.defaultEmojis.optimisation
        else:
            emoji = cfg.defaultEmojis.newIssue

        issueEmbed.set_author(name=f"{emoji.sendable} Issue {action.value}", url=issue.html_url,
                                icon_url=str(issue.user.avatar_url))

        if issue.labels:
            labelsStr = ', '.join(cfg.githubLabelNames.get(x.name, x.name) for x in issue.labels)
            issueEmbed.add_field(name="Labels", value=f"*{labelsStr}*")

        await interaction.response.send_message(embed=issueEmbed)

#endregion

async def setup(bot: client.BasedClient):
    # Casting here because for some reason pyright doesn't think SerializableDiscordObject is a Snowflake,
    # even though it extends discord.Object
    await bot.add_cog(DevGithubCog(bot), guilds=cast(List[Snowflake], cfg.developmentGuilds))
