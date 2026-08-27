from __future__ import annotations

from datetime import datetime

from crew_compliance.domain.enums import DutyKind, Position
from crew_compliance.domain.models import CrewMember, DutyPeriod, Flight, Roster, ValidationIssue
from crew_compliance.ingestion.common import build_duty_kwargs, mapped_value
from crew_compliance.ingestion.parse import apply_overnight_wrap, parse_hours
from crew_compliance.ingestion.common import _str


def normalize_roster(
    rows: list[dict],
    mapping: dict[str, str | None],
    source_name: str,
    dayfirst: bool = False,
) -> Roster:
    issues: list[ValidationIssue] = []
    duties: list[DutyPeriod] = []
    crew_map: dict[str, CrewMember] = {}
    flights: list[Flight] = []
    dropped = 0
    seen: set[tuple] = set()

    wide = mapping.get("captain") is not None

    for index, row in enumerate(rows, start=2):
        people: list[tuple[str, str | None, Position]] = []
        if wide:
            captain = _str(mapped_value(row, mapping, "captain"))
            fo = _str(mapped_value(row, mapping, "first_officer"))
            if captain:
                people.append((captain, captain, Position.CAPTAIN))
            if fo:
                people.append((fo, fo, Position.FO))
            if not people:
                issues.append(ValidationIssue("This row has no Captain or First Officer name.", source_row=index))
                dropped += 1
                continue
        else:
            crew_id = _str(mapped_value(row, mapping, "crew_id")) or _str(mapped_value(row, mapping, "crew_name"))
            crew_name = _str(mapped_value(row, mapping, "crew_name")) or crew_id
            if not crew_id:
                issues.append(ValidationIssue("This row is missing a crew identifier.", source_row=index, field="crew_id"))
                dropped += 1
                continue
            people.append((crew_id, crew_name, None))  # type: ignore[arg-type]

        kwargs = build_duty_kwargs(row, mapping, dayfirst)
        if kwargs["duty_date"] is None:
            issues.append(
                ValidationIssue(
                    "This row has a missing or invalid date. Use YYYY-MM-DD unless you selected day-first dates.",
                    source_row=index,
                    field="duty_date",
                )
            )
            dropped += 1
            continue
        if kwargs["duty_start"] and kwargs["duty_end"]:
            kwargs["duty_end"] = apply_overnight_wrap(kwargs["duty_start"], kwargs["duty_end"])
            if kwargs["duty_end"] <= kwargs["duty_start"]:
                issues.append(
                    ValidationIssue(
                        "Duty end is not after duty start, even after allowing for an overnight duty.",
                        source_row=index,
                    )
                )
                dropped += 1
                continue
        if kwargs["flight_hours"] is not None and kwargs["flight_hours"] < 0:
            issues.append(ValidationIssue("Flight hours cannot be negative.", source_row=index, field="flight_hours"))
            dropped += 1
            continue
        if kwargs["duty_start"] and kwargs["duty_end"]:
            kwargs["duty_hours"] = (kwargs["duty_end"] - kwargs["duty_start"]).total_seconds() / 3600.0
        else:
            kwargs["duty_hours"] = None
            hours_only = parse_hours(mapped_value(row, mapping, "flight_hours"))
            if hours_only is None and kwargs["flight_hours"] is None:
                issues.append(
                    ValidationIssue(
                        "This row has no duty times and no flight hours, so it cannot be used in the analysis.",
                        source_row=index,
                    )
                )
                dropped += 1
                continue

        for crew_id, crew_name, implied_position in people:
            position = implied_position or kwargs["position"] or Position.UNKNOWN
            key = (crew_id, kwargs["duty_start"] or kwargs["duty_date"], kwargs["flight_id"])
            if key in seen:
                issues.append(
                    ValidationIssue(
                        f"Duplicate record for {crew_id} on the same duty/flight was skipped.",
                        source_row=index,
                    )
                )
                dropped += 1
                continue
            seen.add(key)
            duty_id = f"{crew_id}-{index}-{kwargs['flight_id'] or 'duty'}"
            duty = DutyPeriod(
                duty_id=duty_id,
                crew_id=crew_id,
                crew_name=crew_name or crew_id,
                position=position,
                home_base=kwargs["home_base"],
                duty_date=kwargs["duty_date"],
                duty_start=kwargs["duty_start"],
                duty_end=kwargs["duty_end"],
                duty_hours=kwargs["duty_hours"],
                is_positioning=kwargs["is_positioning"],
                duty_kind=kwargs["duty_kind"] if kwargs["duty_kind"] != DutyKind.UNKNOWN else (
                    DutyKind.POSITIONING if kwargs["is_positioning"] else DutyKind.OPERATING_FLIGHT
                ),
                start_location=kwargs["start_location"],
                end_location=kwargs["end_location"],
                flight_id=kwargs["flight_id"],
                flight_start=kwargs["flight_start"],
                flight_end=kwargs["flight_end"],
                flight_hours=kwargs["flight_hours"],
                source_row=index,
            )
            duties.append(duty)
            crew_map[crew_id] = CrewMember(
                crew_id=crew_id,
                name=crew_name or crew_id,
                position=position,
                home_base=kwargs["home_base"],
            )
            flights.append(
                Flight(
                    flight_id=kwargs["flight_id"],
                    flight_start=kwargs["flight_start"],
                    flight_end=kwargs["flight_end"],
                    flight_hours=kwargs["flight_hours"],
                    is_operating=not kwargs["is_positioning"],
                )
            )

    _flag_overlaps(duties, issues)
    return Roster(
        source_name=source_name,
        crew=tuple(crew_map.values()),
        duties=tuple(duties),
        flights=tuple(flights),
        validation_issues=tuple(issues),
        dropped_row_count=dropped,
        date_order="dayfirst" if dayfirst else "iso",
    )


def _flag_overlaps(duties: list[DutyPeriod], issues: list[ValidationIssue]) -> None:
    by_crew: dict[str, list[DutyPeriod]] = {}
    for duty in duties:
        by_crew.setdefault(duty.crew_id, []).append(duty)
    for crew_id, items in by_crew.items():
        timed = [d for d in items if d.duty_start and d.duty_end]
        timed.sort(key=lambda d: d.duty_start or datetime.min)
        for prev, curr in zip(timed, timed[1:]):
            if prev.duty_end and curr.duty_start and curr.duty_start < prev.duty_end:
                issues.append(
                    ValidationIssue(
                        f"{crew_id} has overlapping duties (rows {prev.source_row} and {curr.source_row}). "
                        "Both were kept for analysis; overlapping times may distort rest and duty totals.",
                        source_row=curr.source_row,
                        severity="warning",
                    )
                )