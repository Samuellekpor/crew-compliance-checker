from __future__ import annotations

from datetime import date, timedelta

from crew_compliance.domain.enums import FindingKind
from crew_compliance.domain.opening import OpeningBalance, OpeningBalanceBook
from crew_compliance.engine.runner import run_analysis
from crew_compliance.ingestion.mapping import auto_map_columns
from crew_compliance.ingestion.opening import normalize_opening_balances
from crew_compliance.ingestion.schemas import OPENING_ALIASES, OPENING_FIELDS
from tests.helpers import make_duty, make_roster


def _book(*rows: OpeningBalance) -> OpeningBalanceBook:
    return OpeningBalanceBook(source_name="opening.csv", records=rows)


def test_v1_unchanged_without_opening_file():
    duties = [
        make_duty(day=date(2026, 3, 1) + timedelta(days=i), flight_hours=10.0, source_row=i + 2, flight_id=f"F{i}")
        for i in range(10)
    ]
    result = run_analysis(make_roster(duties), "easa")
    b1 = [f for f in result.findings if f.rule_id == "EASA-FTL-210-B1" and f.kind == FindingKind.POTENTIAL_ISSUE]
    assert not b1


def test_missing_opening_row_is_insufficient_never_zero():
    duties = [
        make_duty(day=date(2026, 3, 20) + timedelta(days=i), flight_hours=5.0, source_row=i + 2, flight_id=f"F{i}")
        for i in range(3)
    ]
    empty_book = _book()
    result = run_analysis(make_roster(duties), "easa", opening_balances=empty_book)
    missing = [
        f
        for f in result.findings
        if f.rule_id == "EASA-FTL-210-B1" and f.kind == FindingKind.INSUFFICIENT_DATA
    ]
    assert missing
    assert missing[0].evidence.get("opening_balance_status") == "missing"
    assert "cannot be assumed" in missing[0].explanation.lower() or "cannot be assumed" in missing[0].explanation


def test_opening_balance_added_before_limit_compare():
    duties = [
        make_duty(day=date(2026, 3, 20) + timedelta(days=i), flight_hours=10.0, source_row=i + 2, flight_id=f"F{i}")
        for i in range(10)
    ]
    book = _book(
        OpeningBalance(
            crew_id="C1",
            crew_name="Crew One",
            role="pilot",
            window_type="28day",
            metric="flight_time",
            hours=5.0,
            as_of_date=date(2026, 3, 20),
            source_row=2,
        )
    )
    result = run_analysis(make_roster(duties), "easa", opening_balances=book)
    b1 = [f for f in result.findings if f.rule_id == "EASA-FTL-210-B1" and f.kind == FindingKind.POTENTIAL_ISSUE]
    assert len(b1) == 1
    assert b1[0].actual == 105.0
    assert b1[0].evidence.get("opening_balance_status") == "applied"
    assert b1[0].evidence.get("opening_balance_hours") == 5.0
    assert b1[0].evidence.get("opening_balance_as_of") == "2026-03-20"


def test_opening_aliases_and_normalize():
    rows = [
        {
            "Crew": "C1",
            "Window Type": "28-day",
            "Hours Already Accrued": "12.5",
            "As Of Date": "2026-03-01",
        }
    ]
    mapping = auto_map_columns(
        ["Crew", "Window Type", "Hours Already Accrued", "As Of Date"],
        fields=OPENING_FIELDS,
        aliases=OPENING_ALIASES,
    )
    book = normalize_opening_balances(rows, mapping, "open.csv")
    assert len(book.records) == 1
    assert book.records[0].window_type == "28day"
    assert book.records[0].hours == 12.5
    assert book.dropped_row_count == 0


def test_complete_in_roster_window_does_not_add_opening_hours():
    duties = [
        make_duty(day=date(2026, 3, 1) + timedelta(days=i), flight_hours=10.0, source_row=i + 2, flight_id=f"F{i}")
        for i in range(28)
    ]
    book = _book(
        OpeningBalance(
            crew_id="C1",
            crew_name="Crew One",
            role="pilot",
            window_type="28day",
            metric="flight_time",
            hours=5.0,
            as_of_date=date(2026, 3, 1),
            source_row=2,
        )
    )
    result = run_analysis(make_roster(duties), "easa", opening_balances=book)
    b1 = [f for f in result.findings if f.rule_id == "EASA-FTL-210-B1" and f.kind == FindingKind.POTENTIAL_ISSUE]
    assert len(b1) == 1
    assert b1[0].actual == 280.0
    assert b1[0].evidence.get("opening_balance_status") == "not_applied_window_complete_in_roster"
    assert b1[0].evidence.get("opening_balance_hours") == 5.0


def test_other_crew_with_opening_does_not_zero_fill_missing():
    duties = [
        make_duty(crew_id="C1", name="A", day=date(2026, 3, 20), flight_hours=8.0, source_row=2, flight_id="A1"),
        make_duty(crew_id="C2", name="B", day=date(2026, 3, 20), flight_hours=8.0, source_row=3, flight_id="B1"),
    ]
    book = _book(
        OpeningBalance("C1", "A", "pilot", "28day", "flight_time", 1.0, date(2026, 3, 20), 2)
    )
    result = run_analysis(make_roster(duties), "easa", opening_balances=book)
    c2 = [f for f in result.findings if f.crew_id == "C2" and f.rule_id == "EASA-FTL-210-B1"]
    assert c2
    assert all(f.kind == FindingKind.INSUFFICIENT_DATA for f in c2)
    assert all(f.evidence.get("opening_balance_status") == "missing" for f in c2)
