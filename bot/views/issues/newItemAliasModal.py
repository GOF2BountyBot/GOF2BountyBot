from typing import Union
from discord.ui import TextInput
from discord import Member, TextStyle, User

from bot.views.issues.issueReportModalBase import IssueReportModalBase

TITLE_TEMPLATE = "[Item Alias] <item name>: <your alias>"

class NewItemAliasModal(IssueReportModalBase):
    FriendlyReportIssueAction = "Request a new alias for an item"

    _itemName = TextInput(
        label="The item",
        style=TextStyle.short,
        required=True,
        placeholder="Which item would you like the alias to be added for? E.g Ship: Betty."
    )
    _newAlias = TextInput(
        label="New alias",
        style=TextStyle.short,
        required=True,
        placeholder="How would you like to be able to refer to the item?"
    )

    def _title(self, author: Union[User, Member]) -> str:
        return f"[Item Alias] {self._itemName.value or '<item name>'}: {self._newAlias.value or '<your alias>'}"
