"""
Public entry-point for the persistence layer.

Example usage from anywhere in the code base
--------------------------------------------
from persistence import get_storage

storage = get_storage()
player   = storage.get_player("1234567890")
"""
from __future__ import annotations

from .facade import PersistenceFacade

# Lazily-created **singleton** instance of the façade.
# You almost never need more than one instance.
def get_storage() -> PersistenceFacade:
    return PersistenceFacade.get()

__all__: list[str] = ["get_storage", "PersistenceFacade"]