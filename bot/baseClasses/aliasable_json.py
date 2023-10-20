from typing import TypedDict, List
from typing_extensions import NotRequired

class SerializedAliasable(TypedDict):
    name: str
    aliases: NotRequired[List[str]]
