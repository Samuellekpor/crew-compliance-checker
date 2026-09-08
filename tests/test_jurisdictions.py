from __future__ import annotations

from datetime import date, timedelta

from crew_compliance.domain.enums import FindingKind
from crew_compliance.engine.runner import run_analysis
from crew_compliance.frameworks import FRAMEWORKS, bootstrap
from tests.helpers import make_duty, make_roster


def test_all_v2_frameworks_are_registered():
    bootstrap()
    assert set(FRAMEWORKS) == {"easa", "faa_part_117", "uk_caa", "transport_canada", "casa"}
    for framework_id in FRAMEWORKS:
        result = run_analysis(make_roster([make_duty()]), framework_id)
        assert result.framework_id == framework_id
        assert result.findings


def test_uk_28_day_flight_time_matches_published_100h():
    duties = [
        make_duty(day=date(2026, 3, 1) + timedelta(days=i), flight_hours=10.0, source_row=i + 2, flight_id=f"F{i}")
        for i in range(11)
    ]
    result = run_analysis(make_roster(duties), "uk_caa")
    rows = [f for f in result.findings if f.rule_id == "UK-FTL-210-B1" and f.kind == FindingKind.POTENTIAL_ISSUE]
    assert len(rows) == 1
    assert rows[0].required == 100
    assert rows[0].actual == 110


def test_transport_canada_112h_28_day_limit():
    duties = [
        make_duty(day=date(2026, 3, 1) + timedelta(days=i), flight_hours=10.0, source_row=i + 2, flight_id=f"F{i}")
        for i in range(12)
    ]
    result = run_analysis(make_roster(duties), "transport_canada")
    rows = [f for f in result.findings if f.rule_id == "TC-700-27-A" and f.kind == FindingKind.POTENTIAL_ISSUE]
    assert len(rows) == 1
    assert rows[0].required == 112
    assert rows[0].actual == 120


def test_casa_appendix_2_100h_28_day_limit():
    duties = [
        make_duty(day=date(2026, 3, 1) + timedelta(days=i), flight_hours=10.0, source_row=i + 2, flight_id=f"F{i}")
        for i in range(11)
    ]
    result = run_analysis(make_roster(duties), "casa")
    rows = [f for f in result.findings if f.rule_id == "CASA-48-A2-11-1" and f.kind == FindingKind.POTENTIAL_ISSUE]
    assert len(rows) == 1
    assert rows[0].required == 100
    assert rows[0].actual == 110
