from __future__ import annotations

import json
import pathlib
from typing import Any

from .backend_interface import StorageBackend


class JSONBackend(StorageBackend):
    """
    Thin wrapper around ``json.load`` / ``json.dump`` that satisfies the
    :class:`StorageBackend` contract.
    """

    def __init__(self, base_dir: str | pathlib.Path = "data") -> None:
        self.base_dir = pathlib.Path(base_dir)

    # -----------------------------------------------------------------
    # StorageBackend implementation
    # -----------------------------------------------------------------
    def read_collection(self, name: str) -> Any:  # noqa: ANN401
        path = self._path(name)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def write_collection(self, name: str, data: Any) -> None:  # noqa: ANN401
        path = self._path(name)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Cheap but safe way to avoid partially-written files.
        tmp = path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        tmp.replace(path)

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------
    def _path(self, name: str) -> pathlib.Path:
        """
        If *name* already looks like an absolute/relative filename
        (it contains ``/`` or ends with ``.json``), return it unchanged;
        otherwise treat it as a logical *collection* and append
        ``.json`` inside ``base_dir``.
        """
        p = pathlib.Path(name)
        if p.is_absolute() or p.suffix == ".json" or "/" in name or "\\" in name:
            return p
        return self.base_dir / f"{name}.json"