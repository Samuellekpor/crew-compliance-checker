from __future__ import annotations

from datetime import date, timedelta

from crew_compliance.domain.enums import FindingKind
from crew_compliance.engine.runner import run_analysis
from tests.helpers import make_duty, make_roster


def test_published_easa_limit_unchanged_without_overlay():
    duties = [
        make_duty(day=date(2026, 3, 1) + timedelta(days=i), flight_hours=10.0, source_row=i + 2, flight_id=f"F{i}")
        for i in range(10)
    ]
    result = run_analysis(make_roster(duties), "easa")
    b1 = [f for f in result.findings if f.rule_id == "EASA-FTL-210-B1" and f.kind == FindingKind.POTENTIAL_ISSUE]
    assert not b1


def test_operator_overlay_tightens_limit_without_changing_published_default():
    duties = [
        make_duty(day=date(2026, 3, 1) + timedelta(days=i), flight_hours=10.0, source_row=i + 2, flight_id=f"F{i}")
        for i in range(10)
    ]
    result = run_analysis(
        make_roster(duties),
        "easa",
        parameter_overrides={"EASA-FTL-210-B1": {"limit_hours": 50}},
    )
    b1 = [f for f in result.findings if f.rule_id == "EASA-FTL-210-B1" and f.kind == FindingKind.POTENTIAL_ISSUE]
    assert len(b1) == 1
    assert b1[0].required == 50
    assert b1[0].actual == 100
    assert b1[0].evidence["operator_parameter_overrides"]["limit_hours"] == 50
    assert b1[0].evidence["published_parameters"]["limit_hours"] == 100
