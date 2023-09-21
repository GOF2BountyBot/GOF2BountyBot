from typing import Literal, TypedDict, Union
from typing_extensions import NotRequired


class SerializedBuiltInWorkshopable(TypedDict):
    fromWorkshop: Literal[False]
    name: str


class SerializedUserSubmittedWorkshopable(TypedDict):
    fromWorkshop: Literal[True]
    workshopListingId: int
    name: str


class AnySerializedWorkshopable(TypedDict):
    fromWorkshop: bool
    workshopListingId: NotRequired[int]
    name: str


SerializedWorkshopableUnion = Union[SerializedBuiltInWorkshopable, SerializedUserSubmittedWorkshopable]