from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta

from crew_compliance.domain.enums import DutyKind, FindingKind, Position
from crew_compliance.domain.models import CrewMember, DutyPeriod, Finding, Roster
from crew_compliance.engine.runner import run_analysis

_KIND_RANK = {
    FindingKind.INFORMATIONAL: 0,
    FindingKind.INSUFFICIENT_DATA: 1,
    FindingKind.POTENTIAL_ISSUE: 2,
}


@dataclass(frozen=True)
class AssignmentCheckResult:
    proposed: DutyPeriod
    new_or_worsened: tuple[Finding, ...]


def build_proposed_duty(
    *,
    crew_id: str,
    crew_name: str,
    duty_date: date,
    start: str,
    end: str,
    flight_hours: float | None = None,
    sector_count: int | None = None,
    home_base: str | None = None,
    start_location: str | None = None,
    position: Position = Position.UNKNOWN,
    flight_id: str = "PROPOSED",
) -> DutyPeriod:
    start_clock = _parse_hhmm(start)
    end_clock = _parse_hhmm(end)
    duty_start = datetime.combine(duty_date, start_clock)
    duty_end = datetime.combine(duty_date, end_clock)
    if duty_end <= duty_start:
        duty_end += timedelta(days=1)
    hours = (duty_end - duty_start).total_seconds() / 3600.0
    return DutyPeriod(
        duty_id=f"{crew_id}-proposed-{flight_id}",
        crew_id=crew_id,
        crew_name=crew_name,
        position=position,
        home_base=home_base,
        duty_date=duty_date,
        duty_start=duty_start,
        duty_end=duty_end,
        duty_hours=hours,
        is_positioning=False,
        duty_kind=DutyKind.OPERATING_FLIGHT,
        start_location=start_location,
        end_location=None,
        flight_id=flight_id,
        flight_start=duty_start,
        flight_end=duty_end,
        flight_hours=flight_hours,
        source_row=0,
        sector_count=sector_count,
    )


def check_duty_assignment(
    roster: Roster,
    proposed: DutyPeriod,
    framework_id: str,
    **run_kwargs,
) -> AssignmentCheckResult:
    combined = replace(
        roster,
        crew=_crew_with_proposed(roster, proposed),
        duties=roster.duties + (proposed,),
    )
    before = run_analysis(roster, framework_id, **run_kwargs)
    after = run_analysis(combined, framework_id, **run_kwargs)
    prior = {finding.finding_id: finding for finding in before.findings}
    delta: list[Finding] = []
    for finding in after.findings:
        if finding.crew_id != proposed.crew_id:
            continue
        previous = prior.get(finding.finding_id)
        if previous is None or _worsened(previous, finding):
            delta.append(finding)
    delta.sort(
        key=lambda item: (
            item.rule_id,
            item.event_time.isoformat() if item.event_time else "",
            item.finding_id,
        )
    )
    return AssignmentCheckResult(proposed=proposed, new_or_worsened=tuple(delta))


def _parse_hhmm(value: str) -> time:
    hours, minutes = (int(part) for part in value.strip().split(":", 1))
    return time(hours, minutes)


def _crew_with_proposed(roster: Roster, proposed: DutyPeriod) -> tuple[CrewMember, ...]:
    if any(member.crew_id == proposed.crew_id for member in roster.crew):
        return roster.crew
    return roster.crew + (
        CrewMember(proposed.crew_id, proposed.crew_name, proposed.position, proposed.home_base),
    )


def _worsened(previous: Finding, current: Finding) -> bool:
    if _KIND_RANK[current.kind] > _KIND_RANK[previous.kind]:
        return True
    if (
        current.kind == FindingKind.POTENTIAL_ISSUE
        and previous.actual is not None
        and current.actual is not None
        and current.actual > previous.actual + 1e-9
    ):
        return True
    return False
