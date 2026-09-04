from __future__ import annotations

from crew_compliance.domain.models import ValidationIssue
from crew_compliance.domain.opening import OpeningBalance, OpeningBalanceBook
from crew_compliance.ingestion.common import _str, mapped_value
from crew_compliance.ingestion.parse import parse_date, parse_hours
from crew_compliance.ingestion.windows_types import normalize_metric, normalize_window_type


def normalize_opening_balances(
    rows: list[dict],
    mapping: dict[str, str | None],
    source_name: str,
    dayfirst: bool = False,
) -> OpeningBalanceBook:
    records: list[OpeningBalance] = []
    issues: list[ValidationIssue] = []
    dropped = 0
    seen: set[tuple[str, str, str | None]] = set()

    for index, row in enumerate(rows, start=2):
        crew_id = _str(mapped_value(row, mapping, "crew_id")) or _str(mapped_value(row, mapping, "crew_name"))
        if not crew_id:
            issues.append(ValidationIssue("This row is missing a crew identifier.", source_row=index, field="crew_id"))
            dropped += 1
            continue
        window = normalize_window_type(_str(mapped_value(row, mapping, "window_type")))
        if not window:
            issues.append(
                ValidationIssue(
                    "This row is missing a window type (for example 7day, 28day, or annual).",
                    source_row=index,
                    field="window_type",
                )
            )
            dropped += 1
            continue
        hours = parse_hours(mapped_value(row, mapping, "hours_already_accrued"))
        if hours is None or hours < 0:
            issues.append(
                ValidationIssue(
                    "Hours already accrued must be a non-negative number.",
                    source_row=index,
                    field="hours_already_accrued",
                )
            )
            dropped += 1
            continue
        as_of = parse_date(mapped_value(row, mapping, "as_of_date"), dayfirst=dayfirst)
        if as_of is None:
            issues.append(
                ValidationIssue(
                    "This row has a missing or invalid as-of date. Use YYYY-MM-DD unless you selected day-first dates.",
                    source_row=index,
                    field="as_of_date",
                )
            )
            dropped += 1
            continue
        metric = normalize_metric(_str(mapped_value(row, mapping, "metric")))
        key = (crew_id, window, metric)
        if key in seen:
            issues.append(
                ValidationIssue(
                    f"Duplicate opening balance for {crew_id} / {window} was skipped.",
                    source_row=index,
                )
            )
            dropped += 1
            continue
        seen.add(key)
        records.append(
            OpeningBalance(
                crew_id=crew_id,
                crew_name=_str(mapped_value(row, mapping, "crew_name")),
                role=_str(mapped_value(row, mapping, "role")),
                window_type=window,
                metric=metric,
                hours=float(hours),
                as_of_date=as_of,
                source_row=index,
            )
        )

    return OpeningBalanceBook(
        source_name=source_name,
        records=tuple(records),
        validation_issues=tuple(issues),
        dropped_row_count=dropped,
    )
