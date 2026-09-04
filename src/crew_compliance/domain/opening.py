from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from crew_compliance.domain.models import ValidationIssue


@dataclass(frozen=True)
class OpeningBalance:
    crew_id: str
    crew_name: str | None
    role: str | None
    window_type: str
    metric: str | None
    hours: float
    as_of_date: date
    source_row: int


@dataclass(frozen=True)
class OpeningBalanceBook:
    """Indexed carry-over hours. Presence of a book means the opening file was uploaded."""

    source_name: str
    records: tuple[OpeningBalance, ...]
    validation_issues: tuple[ValidationIssue, ...] = ()
    dropped_row_count: int = 0

    def __post_init__(self) -> None:
        index: dict[tuple[str, str], dict[str | None, OpeningBalance]] = {}
        for row in self.records:
            bucket = index.setdefault((row.crew_id, row.window_type), {})
            bucket[row.metric] = row
        object.__setattr__(self, "_index", index)

    def get(self, crew_id: str, window_type: str, metric: str | None = None) -> OpeningBalance | None:
        bucket = self._index.get((crew_id, window_type))
        if not bucket:
            return None
        if metric in bucket:
            return bucket[metric]
        return bucket.get(None)
