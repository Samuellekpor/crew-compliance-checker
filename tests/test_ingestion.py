from __future__ import annotations

from datetime import date, timedelta
from io import BytesIO

import pandas as pd

from crew_compliance.ingestion.loader import load_table
from crew_compliance.ingestion.mapping import auto_map_columns
from crew_compliance.ingestion.pipeline import ingest_roster
from crew_compliance.ingestion.parse import apply_overnight_wrap, parse_datetime, parse_hours
from datetime import datetime, time


def test_csv_and_xlsx_ingestion(tmp_path):
    csv_path = tmp_path / "roster.csv"
    csv_path.write_text(
        "Date,Flight,Captain,Hours\n2026-06-01,XX1,Ada,4.5\n",
        encoding="utf-8",
    )
    roster = ingest_roster(csv_path)
    assert len(roster.duties) == 1
    assert roster.duties[0].crew_id == "Ada"
    assert roster.duties[0].flight_hours == 4.5

    frame = pd.DataFrame({"Date": ["2026-06-01"], "Flight": ["XX1"], "Captain": ["Ada"], "Hours": [4.5]})
    xlsx = tmp_path / "roster.xlsx"
    frame.to_excel(xlsx, index=False)
    x_roster = ingest_roster(xlsx)
    assert x_roster.duties[0].crew_id == "Ada"


def test_wide_format_explodes_captain_and_fo(tmp_path):
    path = tmp_path / "wide.csv"
    path.write_text(
        "Date,Flight,Captain,First Officer,Hours\n2026-06-01,XX1,Ada,Bea,5\n",
        encoding="utf-8",
    )
    roster = ingest_roster(path)
    assert {d.crew_id for d in roster.duties} == {"Ada", "Bea"}


def test_invalid_date_is_dropped(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("Date,Crew,Hours\nnot-a-date,Ada,5\n", encoding="utf-8")
    roster = ingest_roster(path)
    assert roster.duties == ()
    assert roster.dropped_row_count == 1
    assert roster.validation_issues


def test_overnight_wrap():
    start = datetime(2026, 6, 1, 22, 0)
    end = datetime(2026, 6, 1, 6, 0)
    wrapped = apply_overnight_wrap(start, end)
    assert wrapped.day == 2
    assert wrapped.hour == 6


def test_parse_hours_hhmm():
    assert parse_hours("8:30") == 8.5


def test_auto_map_aliases():
    mapping = auto_map_columns(["Duty Date", "PIC", "Block Hours", "Flt"])
    assert mapping["duty_date"] == "Duty Date"
    assert mapping["captain"] == "PIC"
    assert mapping["flight_hours"] == "Block Hours"
    assert mapping["flight_id"] == "Flt"