from typing import Literal, TypedDict, Union
from typing_extensions import NotRequired


class SerializedBuiltInWorkshopable(TypedDict):
    fromWorkshop: Literal[False]
    name: str


class SerializedUserSubmittedWorkshopable(TypedDict):
    fromWorkshop: Literal[True]
    workshopListingId: int
    name: str


class AnySerializedWorkshopable(SerializedBuiltInWorkshopable):
    workshopListingId: NotRequired[int]


SerializedWorkshopableUnion = Union[SerializedBuiltInWorkshopable, SerializedUserSubmittedWorkshopable]
