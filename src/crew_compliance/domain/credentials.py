from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from crew_compliance.domain.models import ValidationIssue

CREDENTIAL_TYPE_ALIASES: dict[str, str] = {
    "license": "license",
    "licence": "license",
    "pilot license": "license",
    "atpl": "license",
    "cpl": "license",
    "medical": "medical",
    "medical certificate": "medical",
    "class 1": "medical",
    "class 2": "medical",
    "type_rating": "type_rating",
    "type rating": "type_rating",
    "rating": "type_rating",
    "sim_check": "sim_check",
    "sim check": "sim_check",
    "simulator": "sim_check",
    "opc": "sim_check",
    "lpc": "sim_check",
    "recurrent": "sim_check",
    "line_check": "line_check",
    "line check": "line_check",
    "line": "line_check",
    "visa": "visa",
    "other": "other",
}


def normalize_credential_type(value: str | None) -> str | None:
    if not value:
        return None
    key = " ".join(str(value).strip().lower().replace("-", " ").replace("_", " ").split())
    compact = key.replace(" ", "_")
    return CREDENTIAL_TYPE_ALIASES.get(key) or CREDENTIAL_TYPE_ALIASES.get(compact) or compact or None


@dataclass(frozen=True)
class Credential:
    crew_id: str
    crew_name: str | None
    role: str | None
    credential_type: str
    credential_detail: str | None
    expiry_date: date | None
    source_row: int


@dataclass(frozen=True)
class CredentialBook:
    """Presence of a book means the credentials file was uploaded."""

    source_name: str
    records: tuple[Credential, ...]
    validation_issues: tuple[ValidationIssue, ...] = ()
    dropped_row_count: int = 0

    def __post_init__(self) -> None:
        by_crew: dict[str, list[Credential]] = {}
        for row in self.records:
            by_crew.setdefault(row.crew_id, []).append(row)
        object.__setattr__(self, "_by_crew", {key: tuple(val) for key, val in by_crew.items()})

    def for_crew(self, crew_id: str) -> tuple[Credential, ...]:
        return self._by_crew.get(crew_id, ())
