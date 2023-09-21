from __future__ import annotations

from typing import List, TypeVar, Generic, TypedDict
from typing_extensions import NotRequired

from ..items.base.itemBase_json import SerializedItemBaseUnion
from .inventoryListingValueAugment_json import SerializedValueAugment

TItemSerialized = TypeVar("TItemSerialized", bound=SerializedItemBaseUnion)


class SerializedInventoryListing(TypedDict, Generic[TItemSerialized]):
    item: TItemSerialized
    count: int
    valueAugments: NotRequired[List[SerializedValueAugment]]
