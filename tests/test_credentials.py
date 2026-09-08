from __future__ import annotations

from datetime import date, timedelta

from crew_compliance.domain.credentials import Credential, CredentialBook
from crew_compliance.domain.enums import FindingKind, Severity
from crew_compliance.engine.runner import run_analysis
from crew_compliance.ingestion.mapping import auto_map_columns
from crew_compliance.ingestion.credentials import normalize_credentials
from crew_compliance.ingestion.schemas import CREDENTIAL_ALIASES, CREDENTIAL_FIELDS
from tests.helpers import make_duty, make_roster


def _book(*rows: Credential) -> CredentialBook:
    return CredentialBook(source_name="creds.csv", records=rows)


def test_no_credentials_file_does_not_emit_expiry_findings():
    result = run_analysis(make_roster([make_duty()]), "easa")
    assert not [f for f in result.findings if f.rule_id == "CRED-EXPIRY-1"]


def test_missing_expiry_is_insufficient_data():
    duties = [make_duty(day=date(2026, 6, 1), source_row=2, flight_id="A")]
    book = _book(Credential("C1", "Crew One", "pilot", "medical", None, None, 2))
    result = run_analysis(make_roster(duties), "easa", credentials=book)
    rows = [f for f in result.findings if f.rule_id == "CRED-EXPIRY-1"]
    assert len(rows) == 1
    assert rows[0].kind == FindingKind.INSUFFICIENT_DATA


def test_expiry_within_window_without_duty_in_window_is_medium():
    duties = [make_duty(crew_id="C2", name="Other", day=date(2026, 6, 1), source_row=2, flight_id="OTHER")]
    book = _book(Credential("C1", "Crew One", "pilot", "license", "ATPL", date(2026, 6, 20), 2))
    result = run_analysis(
        make_roster(duties),
        "easa",
        credentials=book,
        credential_lookahead_days=30,
    )
    rows = [f for f in result.findings if f.rule_id == "CRED-EXPIRY-1" and f.kind == FindingKind.POTENTIAL_ISSUE]
    assert len(rows) == 1
    assert rows[0].severity == Severity.MEDIUM
    assert rows[0].evidence["scheduled_in_window"] is False


def test_scheduled_during_window_raises_severity():
    duties = [
        make_duty(day=date(2026, 6, 1) + timedelta(days=i), source_row=i + 2, flight_id=f"F{i}")
        for i in range(5)
    ]
    book = _book(Credential("C1", "Crew One", "pilot", "medical", "Class 1", date(2026, 6, 10), 2))
    result = run_analysis(
        make_roster(duties),
        "easa",
        credentials=book,
        credential_lookahead_days=30,
    )
    rows = [f for f in result.findings if f.rule_id == "CRED-EXPIRY-1" and f.kind == FindingKind.POTENTIAL_ISSUE]
    assert len(rows) == 1
    assert rows[0].severity == Severity.HIGH
    assert rows[0].evidence["scheduled_in_window"] is True


def test_flying_after_expiry_is_critical():
    duties = [make_duty(day=date(2026, 6, 20), source_row=2, flight_id="LATE")]
    book = _book(Credential("C1", "Crew One", "pilot", "visa", "Schengen", date(2026, 6, 10), 2))
    result = run_analysis(
        make_roster(duties),
        "easa",
        credentials=book,
        credential_lookahead_days=30,
    )
    rows = [f for f in result.findings if f.rule_id == "CRED-EXPIRY-1" and f.kind == FindingKind.POTENTIAL_ISSUE]
    assert len(rows) == 1
    assert rows[0].severity == Severity.CRITICAL
    assert rows[0].evidence["scheduled_on_or_after_expiry"] is True


def test_outside_lookahead_is_not_flagged():
    duties = [make_duty(day=date(2026, 6, 1), source_row=2, flight_id="A")]
    book = _book(Credential("C1", "Crew One", "pilot", "license", None, date(2026, 12, 1), 2))
    result = run_analysis(
        make_roster(duties),
        "easa",
        credentials=book,
        credential_lookahead_days=30,
    )
    assert not [f for f in result.findings if f.rule_id == "CRED-EXPIRY-1"]


def test_credential_column_aliases():
    rows = [
        {
            "Crew": "C1",
            "Type": "Medical Certificate",
            "Detail": "Class 1",
            "Expires": "2026-07-01",
        }
    ]
    mapping = auto_map_columns(list(rows[0].keys()), fields=CREDENTIAL_FIELDS, aliases=CREDENTIAL_ALIASES)
    book = normalize_credentials(rows, mapping, "creds.csv")
    assert book.records[0].credential_type == "medical"
    assert book.records[0].expiry_date == date(2026, 7, 1)
