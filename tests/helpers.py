from __future__ import annotations

from datetime import date, datetime, time, timedelta

from crew_compliance.domain.enums import DutyKind, Position
from crew_compliance.domain.models import CrewMember, DutyPeriod, Roster


def make_duty(
    crew_id: str = "C1",
    name: str = "Crew One",
    day: date = date(2026, 6, 1),
    start: str = "06:00",
    end: str = "16:00",
    flight_hours: float | None = 8.0,
    flight_id: str = "XX1",
    source_row: int = 2,
    home_base: str | None = "LHR",
    start_location: str | None = "LHR",
    positioning: bool = False,
) -> DutyPeriod:
    sh, sm = map(int, start.split(":"))
    eh, em = map(int, end.split(":"))
    duty_start = datetime.combine(day, time(sh, sm))
    duty_end = datetime.combine(day, time(eh, em))
    if duty_end <= duty_start:
        duty_end += timedelta(days=1)
    hours = (duty_end - duty_start).total_seconds() / 3600.0
    return DutyPeriod(
        duty_id=f"{crew_id}-{source_row}-{flight_id}",
        crew_id=crew_id,
        crew_name=name,
        position=Position.CAPTAIN,
        home_base=home_base,
        duty_date=day,
        duty_start=duty_start,
        duty_end=duty_end,
        duty_hours=hours,
        is_positioning=positioning,
        duty_kind=DutyKind.POSITIONING if positioning else DutyKind.OPERATING_FLIGHT,
        start_location=start_location,
        end_location=None,
        flight_id=flight_id,
        flight_start=duty_start,
        flight_end=duty_end,
        flight_hours=flight_hours,
        source_row=source_row,
    )


def make_roster(duties: list[DutyPeriod], source_name: str = "test.csv") -> Roster:
    crew = {}
    for duty in duties:
        crew[duty.crew_id] = CrewMember(duty.crew_id, duty.crew_name, duty.position, duty.home_base)
    return Roster(
        source_name=source_name,
        crew=tuple(crew.values()),
        duties=tuple(duties),
        flights=(),
    )