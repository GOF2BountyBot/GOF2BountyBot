from discord.ui import TextInput
from discord import TextStyle

from bot.views.issues.issueReportModalBase import IssueReportModalBase

class FeatureRequestModal(IssueReportModalBase):
    FriendlyReportIssueAction = "Request a new feature"

    _title = TextInput(
        label="Title",
        style=TextStyle.short,
        required=True,
        placeholder="A very brief description of the feature."
    )
    _problemStatement = TextInput(
        label="Is your feature request related to a problem?",
        style=TextStyle.paragraph,
        required=False,
        placeholder="If your idea solves a problem with the bot, tell us about it here. E.g: It's not fair when..."
    )
    _solutionSuggestion = TextInput(
        label="Describe the solution you'd like",
        style=TextStyle.paragraph,
        required=True,
        placeholder="What would your ideal solution look like? E.g: I'd like to be able to..."
    )
