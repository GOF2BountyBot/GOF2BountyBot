from typing import List, Optional, Protocol, Type, TypeVar, Union, runtime_checkable
from discord.ui import TextInput
from discord import Colour, Embed, Member, User
from discord.utils import MISSING
from ...lib.discordUtil import ZWSP

from ..viewBase import ModalBase

@runtime_checkable
class TitleFactory(Protocol):
    # Ignoring here because I would like the callback to take the view instance as a parameter
    def __call__(ProtocolSelf, self: "IssueReportModalBase", author: Union[User, Member]) -> str: ... # type: ignore[reportGeneralTypeIssues]


TModal = TypeVar("TModal", bound="IssueReportModalBase")

class IssueReportModalBase(ModalBase):
    FriendlyReportIssueAction = "Create an issue"
    _title: Union[TextInput, TitleFactory] = MISSING

    def __init__(self, *,
        timeout: Optional[float] = None,
        custom_id: str = MISSING
    ) -> None:
        if not isinstance(self._title, (TextInput, TitleFactory)):
            raise TypeError(f"{IssueReportModalBase.__name__} subclasses must include a _title, as either TextInput field or a callable.")
        self._attachments: List[str] =[]

        super().__init__(title=self.FriendlyReportIssueAction, timeout=timeout, custom_id=custom_id)

    
    def getTitle(self, author: Union[User, Member]) -> str:
        if isinstance(self._title, TextInput):
            return self._title.value
        else:
            return self._title(author) # type: ignore[reportGeneralTypeIssues]
        

    def toEmbed(self, author: Union[User, Member]) -> Embed:
        embed = Embed(colour=Colour.blue(), title=self.getTitle(author))
        embed.set_author(name=self.FriendlyReportIssueAction, icon_url=author.display_avatar.url)

        for field in self.children:
            if field is not self._title and isinstance(field, TextInput):
                embed.add_field(name=field.label, value=field.value or ZWSP, inline=False)

        embed.add_field(name="Attachments", value="\n".join(self._attachments), inline=False)
        
        return embed

    
    # @abstractmethod
    @classmethod
    def fromEmbed(cls: Type[TModal], embed: Embed) -> TModal:
        fieldValues = {
            field.name: field.value \
            for field in embed.fields \
            if field.name is not None \
                and field.value is not None \
                and field.value != ZWSP
        }

        o = cls()

        titleFound = False
        for child in o.children:
            if isinstance(child, TextInput):
                if child.label in fieldValues:
                    child.default = fieldValues[child.label]
                elif child.label == "Title":
                    titleFound = True

        if titleFound and embed.title is not None:
            try:
                titleField = next(f for f in o.children if isinstance(f, TextInput) and f.label == "Title")
            except StopIteration:
                pass
            else:
                titleField.default = embed.title

        return o
