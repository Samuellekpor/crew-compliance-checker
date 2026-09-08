from __future__ import annotations

from dataclasses import replace
from datetime import time

from crew_compliance.domain.enums import FindingKind
from crew_compliance.engine.fdp_tables import (
    lookup_casa_app2_table21,
    lookup_easa_table2,
    lookup_easa_table3,
    lookup_faa_table_b,
    lookup_tc_700_28,
)
from crew_compliance.engine.runner import run_analysis
from tests.helpers import make_duty, make_roster


def _fdp(findings, rule_id: str):
    return [f for f in findings if f.rule_id == rule_id]


def test_easa_table2_cell_0600_1_2_sectors_is_13h():
    limit, citation = lookup_easa_table2(time(6, 0), 1)
    assert limit == 13.0
    assert "Table 2" in citation


def test_easa_table3_1_2_sectors_is_11h():
    limit, _ = lookup_easa_table3(2)
    assert limit == 11.0
    limit8, _ = lookup_easa_table3(8)
    assert limit8 == 9.0


def test_faa_table_b_0700_1_segment_is_14h():
    limit, citation = lookup_faa_table_b(time(7, 0), 1)
    assert limit == 14.0
    assert "Table B" in citation


def test_casa_table21_0700_1_to_3_sectors_is_13h():
    limit, _ = lookup_casa_app2_table21(time(7, 0), 1)
    assert limit == 13.0


def test_tc_700_28_0700_1_flight_avg_over_50min_is_13h():
    limit, citation = lookup_tc_700_28(time(7, 0), 1, 8.0)
    assert limit == 13.0
    assert citation == "CAR 700.28(4)"


def test_easa_fdp_equal_to_table_is_not_an_issue():
    result = run_analysis(make_roster([make_duty(start="06:00", end="19:00")]), "easa")
    issues = [f for f in _fdp(result.findings, "EASA-FTL-205-TABLE") if f.kind == FindingKind.POTENTIAL_ISSUE]
    assert not issues


def test_easa_fdp_above_table_is_potential_issue():
    result = run_analysis(make_roster([make_duty(start="06:00", end="19:06")]), "easa")
    issues = [f for f in _fdp(result.findings, "EASA-FTL-205-TABLE") if f.kind == FindingKind.POTENTIAL_ISSUE]
    assert len(issues) == 1
    assert issues[0].required == 13.0
    assert issues[0].actual == 13.1


def test_easa_unknown_uses_table_3():
    result = run_analysis(
        make_roster([make_duty(start="06:00", end="17:06", acclimatisation="unknown")]),
        "easa",
    )
    issues = [f for f in _fdp(result.findings, "EASA-FTL-205-TABLE") if f.kind == FindingKind.POTENTIAL_ISSUE]
    assert len(issues) == 1
    assert issues[0].required == 11.0


def test_faa_fdp_equal_and_over_table_b():
    ok = run_analysis(make_roster([make_duty(start="07:00", end="21:00")]), "faa_part_117")
    assert not [f for f in _fdp(ok.findings, "FAA-117-13-TABLE-B") if f.kind == FindingKind.POTENTIAL_ISSUE]
    over = run_analysis(make_roster([make_duty(start="07:00", end="21:06")]), "faa_part_117")
    issues = [f for f in _fdp(over.findings, "FAA-117-13-TABLE-B") if f.kind == FindingKind.POTENTIAL_ISSUE]
    assert len(issues) == 1
    assert issues[0].required == 14.0
    assert issues[0].actual == 14.1


def test_casa_fdp_equal_and_over_table_21():
    ok = run_analysis(make_roster([make_duty(start="07:00", end="20:00")]), "casa")
    assert not [f for f in _fdp(ok.findings, "CASA-48-A2-T21") if f.kind == FindingKind.POTENTIAL_ISSUE]
    over = run_analysis(make_roster([make_duty(start="07:00", end="20:06")]), "casa")
    issues = [f for f in _fdp(over.findings, "CASA-48-A2-T21") if f.kind == FindingKind.POTENTIAL_ISSUE]
    assert len(issues) == 1
    assert issues[0].required == 13.0
    assert issues[0].actual == 13.1


def test_tc_fdp_equal_and_over_700_28():
    ok = run_analysis(make_roster([make_duty(start="07:00", end="20:00", flight_hours=8.0)]), "transport_canada")
    assert not [f for f in _fdp(ok.findings, "TC-700-28-TABLE") if f.kind == FindingKind.POTENTIAL_ISSUE]
    over = run_analysis(make_roster([make_duty(start="07:00", end="20:06", flight_hours=8.0)]), "transport_canada")
    issues = [f for f in _fdp(over.findings, "TC-700-28-TABLE") if f.kind == FindingKind.POTENTIAL_ISSUE]
    assert len(issues) == 1
    assert issues[0].required == 13.0
    assert issues[0].actual == 13.1


def test_missing_duty_times_are_insufficient_data():
    duty = replace(make_duty(), duty_start=None, duty_end=None)
    result = run_analysis(make_roster([duty]), "easa")
    rows = _fdp(result.findings, "EASA-FTL-205-TABLE")
    assert rows
    assert all(f.kind == FindingKind.INSUFFICIENT_DATA for f in rows)


def test_tc_missing_average_flight_duration_is_insufficient():
    duty = replace(make_duty(start="07:00", end="20:00"), flight_hours=None, flight_start=None, flight_end=None)
    result = run_analysis(make_roster([duty]), "transport_canada")
    rows = _fdp(result.findings, "TC-700-28-TABLE")
    assert rows
    assert all(f.kind == FindingKind.INSUFFICIENT_DATA for f in rows)


def test_existing_easa_10h_duty_stays_under_fdp_table():
    result = run_analysis(make_roster([make_duty(start="06:00", end="16:00")]), "easa")
    issues = [f for f in _fdp(result.findings, "EASA-FTL-205-TABLE") if f.kind == FindingKind.POTENTIAL_ISSUE]
    assert not issues
