from __future__ import annotations

from crew_compliance.domain.enums import FindingKind
from crew_compliance.engine.runner import run_analysis
from crew_compliance.ingestion.pipeline import ingest_roster
from crew_compliance.samples.demo_rosters import (
    DISCLAIMER,
    SAMPLE_CASES,
    is_sample_filename,
    list_samples,
    sample_bytes,
    sample_filename,
    sample_rows,
)


def _issues(result, rule_id: str, crew_id: str):
    return [
        f
        for f in result.findings
        if f.rule_id == rule_id and f.crew_id == crew_id and f.kind == FindingKind.POTENTIAL_ISSUE
    ]


def _insufficient(result, rule_id: str, crew_id: str):
    return [
        f
        for f in result.findings
        if f.rule_id == rule_id and f.crew_id == crew_id and f.kind == FindingKind.INSUFFICIENT_DATA
    ]


def test_sample_catalog_lists_easa_and_faa():
    ids = {item["sample_id"] for item in list_samples()}
    assert ids == {"easa", "faa"}
    assert DISCLAIMER.startswith("Synthetic")


def test_sample_filenames_detected():
    assert is_sample_filename("easa_sample.csv")
    assert is_sample_filename("faa_sample.xlsx")
    assert is_sample_filename("sample_roster.csv")
    assert not is_sample_filename("airline_ops.csv")


def test_easa_sample_csv_loads_and_triggers_intended_findings():
    roster = ingest_roster(sample_bytes("easa", "csv"), filename=sample_filename("easa", "csv"))
    assert len(roster.crew) == 4
    assert len(roster.duties) >= 10
    result = run_analysis(roster, "easa")

    assert _issues(result, "EASA-FTL-210-A1", "EA2")
    assert _issues(result, "EASA-FTL-235-MINREST", "EA3")
    assert _issues(result, "EASA-FTL-205-TABLE", "EA3")
    assert _insufficient(result, "EASA-FTL-205-TABLE", "EA4")

    # Boundary equal-to-limit duty for EA4 must not itself be a potential FDP issue.
    ea4_fdp_issues = _issues(result, "EASA-FTL-205-TABLE", "EA4")
    assert not ea4_fdp_issues

    # Compliant crew should not appear on the intentional violation rules above.
    for rule_id in ("EASA-FTL-210-A1", "EASA-FTL-235-MINREST"):
        assert not _issues(result, rule_id, "EA1")


def test_faa_sample_csv_loads_and_triggers_intended_findings():
    roster = ingest_roster(sample_bytes("faa", "csv"), filename=sample_filename("faa", "csv"))
    assert len(roster.crew) == 4
    result = run_analysis(roster, "faa_part_117")

    assert _issues(result, "FAA-117-23-B1", "FA2")
    assert _issues(result, "FAA-117-25-E", "FA3")
    assert _issues(result, "FAA-117-13-TABLE-B", "FA3")
    assert _issues(result, "FAA-117-25-B", "FA4")
    assert _insufficient(result, "FAA-117-13-TABLE-B", "FA4")
    assert not _issues(result, "FAA-117-25-E", "FA1")


def test_xlsx_samples_match_csv_findings():
    for sample_id, framework_id in (("easa", "easa"), ("faa", "faa_part_117")):
        csv_roster = ingest_roster(sample_bytes(sample_id, "csv"), filename=sample_filename(sample_id, "csv"))
        xlsx_roster = ingest_roster(sample_bytes(sample_id, "xlsx"), filename=sample_filename(sample_id, "xlsx"))
        assert len(csv_roster.duties) == len(xlsx_roster.duties)
        csv_result = run_analysis(csv_roster, framework_id)
        xlsx_result = run_analysis(xlsx_roster, framework_id)
        csv_keys = {(f.rule_id, f.crew_id, f.kind) for f in csv_result.findings if f.kind == FindingKind.POTENTIAL_ISSUE}
        xlsx_keys = {(f.rule_id, f.crew_id, f.kind) for f in xlsx_result.findings if f.kind == FindingKind.POTENTIAL_ISSUE}
        assert csv_keys == xlsx_keys


def test_sample_cases_cover_documented_crews():
    easa_crews = {c.crew_id for c in SAMPLE_CASES if c.sample_id == "easa"}
    faa_crews = {c.crew_id for c in SAMPLE_CASES if c.sample_id == "faa"}
    assert easa_crews == {"EA1", "EA2", "EA3", "EA4"}
    assert faa_crews == {"FA1", "FA2", "FA3", "FA4"}
    assert {r["crew_id"] for r in sample_rows("easa")} == easa_crews
    assert {r["crew_id"] for r in sample_rows("faa")} == faa_crews
