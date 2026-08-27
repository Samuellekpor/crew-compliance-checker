from __future__ import annotations

from datetime import date, timedelta

from crew_compliance.domain.enums import FindingKind
from crew_compliance.engine.runner import run_analysis
from tests.helpers import make_duty, make_roster


def test_easa_28_day_flight_time_boundary():
    duties = []
    for i in range(10):
        duties.append(
            make_duty(
                day=date(2026, 3, 1) + timedelta(days=i),
                flight_hours=10.0,
                source_row=i + 2,
                flight_id=f"F{i}",
            )
        )
    result = run_analysis(make_roster(duties), "easa")
    b1 = [f for f in result.findings if f.rule_id == "EASA-FTL-210-B1" and f.kind == FindingKind.POTENTIAL_ISSUE]
    assert not b1

    duties.append(
        make_duty(
            day=date(2026, 3, 11),
            flight_hours=0.1,
            source_row=20,
            flight_id="OVER",
        )
    )
    result = run_analysis(make_roster(duties), "easa")
    b1 = [f for f in result.findings if f.rule_id == "EASA-FTL-210-B1" and f.kind == FindingKind.POTENTIAL_ISSUE]
    assert len(b1) == 1
    assert b1[0].actual == 100.1
    assert b1[0].required == 100


def test_positioning_excluded_from_flight_time():
    duties = [
        make_duty(day=date(2026, 3, 1) + timedelta(days=i), flight_hours=10.0, source_row=i + 2, flight_id=f"F{i}")
        for i in range(8)
    ]
    duties.append(
        make_duty(
            day=date(2026, 3, 15),
            flight_hours=20.0,
            positioning=True,
            source_row=99,
            flight_id="DHD",
        )
    )
    result = run_analysis(make_roster(duties), "easa")
    b1 = [f for f in result.findings if f.rule_id == "EASA-FTL-210-B1" and f.kind == FindingKind.POTENTIAL_ISSUE]
    assert not b1


def test_easa_7_day_duty_exceedance():
    duties = [
        make_duty(
            day=date(2026, 4, 1) + timedelta(days=i),
            start="06:00",
            end="16:00",
            flight_hours=8,
            source_row=i + 2,
            flight_id=f"D{i}",
        )
        for i in range(7)
    ]
    result = run_analysis(make_roster(duties), "easa")
    a1 = [f for f in result.findings if f.rule_id == "EASA-FTL-210-A1" and f.kind == FindingKind.POTENTIAL_ISSUE]
    assert a1
    assert a1[0].actual == 70
    assert a1[0].required == 60


def test_easa_min_rest_home_base():
    duties = [
        make_duty(day=date(2026, 5, 1), start="06:00", end="18:00", source_row=2, flight_id="A"),
        make_duty(day=date(2026, 5, 2), start="04:00", end="12:00", source_row=3, flight_id="B"),
    ]
    result = run_analysis(make_roster(duties), "easa")
    rest = [f for f in result.findings if f.rule_id == "EASA-FTL-235-MINREST" and f.kind == FindingKind.POTENTIAL_ISSUE]
    assert rest
    assert rest[0].actual == 10
    assert rest[0].required == 12


def test_easa_min_rest_compliant_when_12h():
    duties = [
        make_duty(day=date(2026, 5, 1), start="06:00", end="16:00", source_row=2, flight_id="A"),
        make_duty(day=date(2026, 5, 2), start="04:00", end="12:00", source_row=3, flight_id="B"),
    ]
    result = run_analysis(make_roster(duties), "easa")
    rest = [f for f in result.findings if f.rule_id == "EASA-FTL-235-MINREST" and f.kind == FindingKind.POTENTIAL_ISSUE]
    assert not rest


def test_unknown_home_away_insufficient_between_10_and_12():
    duties = [
        make_duty(day=date(2026, 5, 1), start="06:00", end="16:00", source_row=2, flight_id="A", home_base=None, start_location=None),
        make_duty(day=date(2026, 5, 2), start="03:00", end="12:00", source_row=3, flight_id="B", home_base=None, start_location=None),
    ]
    result = run_analysis(make_roster(duties), "easa")
    rest = [f for f in result.findings if f.rule_id == "EASA-FTL-235-MINREST"]
    kinds = {f.kind for f in rest if f.duty_id and f.duty_id.endswith("-B")}
    assert FindingKind.INSUFFICIENT_DATA in {f.kind for f in rest}
    assert not any(f.kind == FindingKind.POTENTIAL_ISSUE and f.actual is not None and 10 <= f.actual < 12 for f in rest)


def test_faa_not_mixed_with_easa_ids():
    duties = [make_duty()]
    result = run_analysis(make_roster(duties), "faa_part_117")
    assert all(f.rule_id.startswith("FAA-") for f in result.findings)


def test_faa_10h_rest():
    duties = [
        make_duty(day=date(2026, 5, 1), start="06:00", end="20:00", source_row=2, flight_id="A"),
        make_duty(day=date(2026, 5, 2), start="04:00", end="12:00", source_row=3, flight_id="B"),
    ]
    result = run_analysis(make_roster(duties), "faa_part_117")
    rest = [f for f in result.findings if f.rule_id == "FAA-117-25-E" and f.kind == FindingKind.POTENTIAL_ISSUE]
    assert rest
    assert rest[0].actual == 8
    assert rest[0].required == 10


def test_faa_30h_in_168h():
    duties = []
    day = date(2026, 7, 1)
    for i in range(8):
        duties.append(
            make_duty(
                day=day + timedelta(days=i),
                start="06:00",
                end="18:00",
                source_row=i + 2,
                flight_id=f"N{i}",
            )
        )
    result = run_analysis(make_roster(duties), "faa_part_117")
    look = [f for f in result.findings if f.rule_id == "FAA-117-25-B" and f.kind == FindingKind.POTENTIAL_ISSUE]
    assert look


def test_incomplete_year_is_insufficient_not_pass():
    duties = [make_duty(day=date(2026, 3, 1), flight_hours=10, source_row=2)]
    result = run_analysis(make_roster(duties), "easa")
    year = [f for f in result.findings if f.rule_id == "EASA-FTL-210-B2"]
    assert year
    assert all(f.kind == FindingKind.INSUFFICIENT_DATA for f in year)


def test_ruleset_version_stamped():
    result = run_analysis(make_roster([make_duty()]), "easa")
    assert result.ruleset_version == "1.0.0"
    assert result.findings
    assert result.findings[0].ruleset_version == "1.0.0"