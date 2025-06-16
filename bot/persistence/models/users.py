from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class User:
    """Lightweight domain object that can be serialised to / from JSON."""
    id: str
    name: str = "Unknown"
    stats: dict[str, Any] = field(default_factory=dict)

    # ------ helpers ------------------------------------------------
    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "User":
        return cls(**raw)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)