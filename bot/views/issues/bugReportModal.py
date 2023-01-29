from discord.ui import TextInput
from discord import TextStyle

from .issueReportModalBase import IssueReportModalBase

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
        placeholder="If an unexpected error occurs, BountyBot will usually provide you with an interaction ID. " \
                    + "This will make resolving your issue much quicker!"
    )
    _messageLink = TextInput(
        label="Message link",
        style=TextStyle.short,
        required=False,
        placeholder="If you can (i.e the channel is accessible to at least one developer), providing a link " \
                    + "to the message where you saw the bug is one of the most helpful things you can do, " \
                    + "so we can see what led up to the bug.\n" \
                    + "On discord mobile, tap and hold on the message, tap share, and copy the link.\n" \
                    + "On discord desktop/web, right click on the message, and click copy message link."
    )
