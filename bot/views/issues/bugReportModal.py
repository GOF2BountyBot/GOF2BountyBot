from discord.ui import TextInput
from discord import TextStyle

from bot.views.issues.issueReportModalBase import IssueReportModalBase

class BugReportModal(IssueReportModalBase):
    FriendlyReportIssueAction = "Report a bug"

    _title = TextInput(
        label="Title",
        style=TextStyle.short,
        required=True,
        placeholder="A very brief description of the bug."
    )
    _description = TextInput(
        label="Describe the bug",
        style=TextStyle.paragraph,
        required=True,
        placeholder="A full description of the bug, what went wrong, and what you expected to happen if applicable."
    )
    _reproSteps = TextInput(
        label="Steps to reproduce",
        style=TextStyle.paragraph,
        required=True,
        placeholder="Steps to reproduce the bug. E.g:\n" + \
                    "1. In channel `x`\n" + \
                    "2. Have `y` equipped\n" + \
                    "3. Use command `z`\n" + \
                    "4. 🥴"
    )
    _interactionId = TextInput(
        label="Interaction ID",
        style=TextStyle.short,
        required=False,
        placeholder="BountyBot will usually give you an ID when errors occur. This will make debugging much quicker!"
    )
    _messageLink = TextInput(
        label="Message link",
        style=TextStyle.short,
        required=False,
        placeholder="Linking to the message where the bug occurred lets us see what led up to the bug"
    )
