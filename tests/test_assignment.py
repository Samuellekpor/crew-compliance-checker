from __future__ import annotations

from datetime import date, timedelta

from crew_compliance.domain.enums import FindingKind
from crew_compliance.engine.assignment import build_proposed_duty, check_duty_assignment
from tests.helpers import make_duty, make_roster


def test_assignment_flags_new_fdp_exceedance():
    roster = make_roster([make_duty(start="06:00", end="16:00")])
    proposed = build_proposed_duty(
        crew_id="C1",
        crew_name="Crew One",
        duty_date=date(2026, 6, 2),
        start="06:00",
        end="19:06",
        flight_hours=8.0,
        home_base="LHR",
        start_location="LHR",
    )
    result = check_duty_assignment(roster, proposed, "easa")
    fdp = [
        f
        for f in result.new_or_worsened
        if f.rule_id == "EASA-FTL-205-TABLE" and f.kind == FindingKind.POTENTIAL_ISSUE
    ]
    assert len(fdp) == 1
    assert fdp[0].required == 13.0
    assert fdp[0].duty_id == proposed.duty_id


def test_assignment_equal_to_fdp_limit_is_not_a_potential_issue():
    roster = make_roster([make_duty(start="06:00", end="16:00")])
    proposed = build_proposed_duty(
        crew_id="C1",
        crew_name="Crew One",
        duty_date=date(2026, 6, 2),
        start="06:00",
        end="19:00",
        flight_hours=8.0,
        home_base="LHR",
        start_location="LHR",
    )
    result = check_duty_assignment(roster, proposed, "easa")
    fdp = [
        f
        for f in result.new_or_worsened
        if f.rule_id == "EASA-FTL-205-TABLE" and f.kind == FindingKind.POTENTIAL_ISSUE
    ]
    assert not fdp


def test_assignment_reports_new_cumulative_exceedance():
    duties = [
        make_duty(
            day=date(2026, 3, 1) + timedelta(days=i),
            flight_hours=10.0,
            source_row=i + 2,
            flight_id=f"F{i}",
        )
        for i in range(10)
    ]
    roster = make_roster(duties)
    proposed = build_proposed_duty(
        crew_id="C1",
        crew_name="Crew One",
        duty_date=date(2026, 3, 11),
        start="06:00",
        end="16:00",
        flight_hours=0.1,
        home_base="LHR",
        start_location="LHR",
        flight_id="OVER",
    )
    result = check_duty_assignment(roster, proposed, "easa")
    b1 = [
        f
        for f in result.new_or_worsened
        if f.rule_id == "EASA-FTL-210-B1" and f.kind == FindingKind.POTENTIAL_ISSUE
    ]
    assert len(b1) == 1
    assert b1[0].actual == 100.1


def test_assignment_does_not_attribute_other_crew_findings():
    roster = make_roster(
        [
            make_duty(crew_id="C1", name="Alpha", start="06:00", end="16:00"),
            make_duty(crew_id="C2", name="Bravo", start="06:00", end="16:00", source_row=3, flight_id="X2"),
        ]
    )
    proposed = build_proposed_duty(
        crew_id="C1",
        crew_name="Alpha",
        duty_date=date(2026, 6, 2),
        start="06:00",
        end="19:06",
        flight_hours=8.0,
        home_base="LHR",
        start_location="LHR",
    )
    result = check_duty_assignment(roster, proposed, "easa")
    assert all(f.crew_id == "C1" for f in result.new_or_worsened)


def test_assignment_is_deterministic():
    roster = make_roster([make_duty(start="06:00", end="16:00")])
    proposed = build_proposed_duty(
        crew_id="C1",
        crew_name="Crew One",
        duty_date=date(2026, 6, 2),
        start="06:00",
        end="19:06",
        flight_hours=8.0,
        home_base="LHR",
        start_location="LHR",
    )
    first = check_duty_assignment(roster, proposed, "easa")
    second = check_duty_assignment(roster, proposed, "easa")
    assert [f.finding_id for f in first.new_or_worsened] == [f.finding_id for f in second.new_or_worsened]
