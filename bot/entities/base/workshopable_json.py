from typing import Literal, TypedDict, Union


class SerializedBuiltInWorkshopable(TypedDict):
    fromWorkshop: Literal[False]
    name: str


class SerializedUserSubmittedWorkshopable(TypedDict):
    fromWorkshop: Literal[True]
    workshopListingId: int
    name: str


SerializedWorkshopableUnion = Union[SerializedBuiltInWorkshopable, SerializedUserSubmittedWorkshopable]
