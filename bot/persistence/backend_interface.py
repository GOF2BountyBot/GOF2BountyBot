from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class StorageBackend(ABC):
    """
    Contract that every concrete storage backend (JSON, Postgres, …)
    must fulfil.  The façade only depends on this interface.
    """

    # ---- LOW-LEVEL CRUD PRIMITIVES ---------------------------------
    @abstractmethod
    def read_collection(self, name: str) -> Any:  # noqa: ANN401
        """
        Return the raw Python object (dict, list, …) belonging to *name*,
        or ``None`` if the collection does not yet exist.
        """

    @abstractmethod
    def write_collection(self, name: str, data: Any) -> None:  # noqa: ANN401
        """Persist *data* under *name* (must create/overwrite atomically)."""