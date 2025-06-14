from __future__ import annotations

from typing import Any, Dict, List, Optional
from pathlib import Path
from importlib import import_module

from bot.cfg import cfg
from bot.persistence.backend_interface import StorageBackend
from bot.persistence.json_backend import JSONBackend

class PersistenceFacade:
    """
    Central, *public* API that the rest of the bot should use
    for **all** data access.  Internally it delegates to one concrete
    :class:`~persistence.backend_interface.StorageBackend`.

    Singleton semantics (``.get()``) are used so that you do not
    accidentally create competing façade instances that each keep
    their own backend/connection cache.
    """

    # ------------- Singleton plumbing (simple and thread-safe) --------------
    _instance: Optional["PersistenceFacade"] = None

    @classmethod
    def get(cls) -> "PersistenceFacade":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------------
    def __init__(self, backend: Optional[StorageBackend] = None) -> None:
        # Only allow normal instantiation when no singleton instance exists
        # (otherwise `.get()` must be used).
        if PersistenceFacade._instance is not None and backend is None:
            raise RuntimeError(
                "Use PersistenceFacade.get() instead of direct construction."
            )

        # Default to the current JSON backend until Postgres is ready.
        self._backend: StorageBackend = backend or JSONBackend()

    # =========================================================================
    # LOW-LEVEL helpers
    # =========================================================================
    def _read(self, collection: str) -> Any:  # noqa: ANN401
        return self._backend.read_collection(collection) or {}

    def _write(self, collection: str, data: Any) -> None:  # noqa: ANN401
        self._backend.write_collection(collection, data)

    # ---- Bounties -----------------------------------------------------------
    _BOUNTIES = "bounties"

    def get_bounties(self) -> List[Dict[str, Any]]:
        """
        Return all bounties as a list (empty list when none exist).
        """
        return self._read(self._BOUNTIES) or []

    def add_bounty(self, bounty: Dict[str, Any]) -> None:
        """
        Append a new *bounty* to the collection.
        """
        bounties = self.get_bounties()
        bounties.append(bounty)
        self._write(self._BOUNTIES, bounties)

    # ---- Users DB ----------------------------------------------------------
    # The path to the JSON file lives in cfg.paths.usersDB (loaded from your TOML).

    def _users_path(self) -> str:
        #cfg = import_module("bot.cfg.cfg")
        return str(cfg.paths.usersDB)

    def get_users_db_raw(self) -> dict[str, Any]:
        """Return the raw (dict) representation of the Users DB."""
        return self._read(self._users_path()) or {}

    def save_users_db_raw(self, data: dict[str, Any]) -> None:
        """Persist *data* as the current Users DB."""
        self._write(self._users_path(), data)

    # ---- Generic key/value helpers -----------------------------------------
    def get_raw(self, collection: str) -> Any:  # noqa: ANN401
        """Low-level escape hatch for special cases – use sparingly."""
        return self._backend.read_collection(collection)

    def set_raw(self, collection: str, data: Any) -> None:  # noqa: ANN401
        self._backend.write_collection(collection, data)