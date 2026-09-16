from __future__ import annotations

"""
Synthetic demonstration rosters for the lead-magnet trial experience.

All names, IDs, and flight numbers are fictional. Files are labelled
"Synthetic demonstration data — not for operational use."

SAMPLE_CASES documents which crew / rule each intentional finding maps to.
tests/test_samples.py asserts those expectations against the live engine.
"""

import csv
import io
from dataclasses import dataclass
from typing import Iterable

from openpyxl import Workbook

DISCLAIMER = "Synthetic demonstration data — not for operational use."

# Canonical headers — match ingestion aliases so auto-mapping succeeds without UI tweaks.
HEADERS = (
    "crew_id",
    "crew_name",
    "position",
    "home_base",
    "duty_date",
    "duty_start",
    "duty_end",
    "flight_id",
    "flight_hours",
    "is_positioning",
    "start_location",
    "sectors",
    "fdp_hours",
    "acclimatisation",
)


@dataclass(frozen=True)
class SampleCase:
    """Documents one intentional demo scenario for developers and tests."""

    sample_id: str
    framework_id: str
    crew_id: str
    rule_id: str
    kind: str  # potential_issue | insufficient_data | compliant
    reason: str


SAMPLE_CASES: tuple[SampleCase, ...] = (
    # ── EASA ──────────────────────────────────────────────────────────────
    SampleCase(
        "easa",
        "easa",
        "EA1",
        "—",
        "compliant",
        "Ana Correia: well-spaced short duties with ≥12 h rest — no potential issues expected for A1/min-rest/FDP table.",
    ),
    SampleCase(
        "easa",
        "easa",
        "EA2",
        "EASA-FTL-210-A1",
        "potential_issue",
        "Boris Schäfer: seven 10 h duties in seven consecutive calendar days → 70 h duty vs 60 h limit.",
    ),
    SampleCase(
        "easa",
        "easa",
        "EA3",
        "EASA-FTL-235-MINREST",
        "potential_issue",
        "Cleo Nakamura: 12 h duty ending 18:00, next report 04:00 → 10 h rest vs 12 h home-base floor.",
    ),
    SampleCase(
        "easa",
        "easa",
        "EA3",
        "EASA-FTL-205-TABLE",
        "potential_issue",
        "Cleo Nakamura: 06:00 report, 1 sector, duty span 13.5 h → above Table 2 limit of 13.0 h.",
    ),
    SampleCase(
        "easa",
        "easa",
        "EA4",
        "EASA-FTL-205-TABLE",
        "insufficient_data",
        "David Mensah: positioning-only duty with no sector count — table cell cannot be selected.",
    ),
    SampleCase(
        "easa",
        "easa",
        "EA4",
        "EASA-FTL-205-TABLE",
        "compliant",
        "David Mensah: 06:00–19:00 (13.0 h) equals Table 2 limit — not a potential issue.",
    ),
    # ── FAA ───────────────────────────────────────────────────────────────
    SampleCase(
        "faa",
        "faa_part_117",
        "FA1",
        "—",
        "compliant",
        "Ellen Park: short week within Part 117 rest and Table B limits.",
    ),
    SampleCase(
        "faa",
        "faa_part_117",
        "FA2",
        "FAA-117-23-B1",
        "potential_issue",
        "Frank Osei: 100.1 h flight time inside any 672 consecutive hours.",
    ),
    SampleCase(
        "faa",
        "faa_part_117",
        "FA3",
        "FAA-117-25-E",
        "potential_issue",
        "Grace Torres: 8 h rest before next FDP vs 10 h required by § 117.25(e).",
    ),
    SampleCase(
        "faa",
        "faa_part_117",
        "FA3",
        "FAA-117-13-TABLE-B",
        "potential_issue",
        "Grace Torres: 07:00 report, 1 segment, 14.1 h FDP proxy → above Table B 14.0 h.",
    ),
    SampleCase(
        "faa",
        "faa_part_117",
        "FA4",
        "FAA-117-25-B",
        "potential_issue",
        "Hugo Lefort: eight consecutive 12 h duties leave no 30 h rest block inside 168 h.",
    ),
    SampleCase(
        "faa",
        "faa_part_117",
        "FA4",
        "FAA-117-13-TABLE-B",
        "insufficient_data",
        "Hugo Lefort: positioning-only duty with no sector count — Table B cell cannot be selected.",
    ),
)


def _easa_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    # EA1 — compliant baseline (LHR)
    for i, (day, start, end, fid, hours) in enumerate(
        (
            ("2026-07-06", "08:00", "14:00", "EA101", "5.0"),
            ("2026-07-09", "08:00", "15:00", "EA102", "5.5"),
            ("2026-07-13", "09:00", "15:00", "EA103", "5.0"),
            ("2026-07-17", "08:00", "14:30", "EA104", "5.2"),
        ),
        start=1,
    ):
        rows.append(_row("EA1", "Ana Correia", "Captain", "LHR", day, start, end, fid, hours, "false", "LHR", "1", "", "acclimatised"))

    # EA2 — 7×10 h duty in 7 consecutive days → EASA-FTL-210-A1 (70 > 60)
    for i in range(7):
        day = f"2026-07-{10 + i:02d}"
        rows.append(
            _row(
                "EA2",
                "Boris Schäfer",
                "Captain",
                "FRA",
                day,
                "06:00",
                "16:00",
                f"EA2{i:02d}",
                "8.0",
                "false",
                "FRA",
                "1",
                "",
                "acclimatised",
            )
        )

    # EA3 — insufficient rest (10 h < 12) then later FDP table exceedance (13.5 > 13)
    rows.append(_row("EA3", "Cleo Nakamura", "First Officer", "AMS", "2026-07-20", "06:00", "18:00", "EA301", "9.0", "false", "AMS", "1", "", "acclimatised"))
    rows.append(_row("EA3", "Cleo Nakamura", "First Officer", "AMS", "2026-07-21", "04:00", "12:00", "EA302", "6.0", "false", "AMS", "1", "", "acclimatised"))
    rows.append(_row("EA3", "Cleo Nakamura", "First Officer", "AMS", "2026-07-25", "06:00", "19:30", "EA303", "10.0", "false", "AMS", "1", "", "acclimatised"))

    # EA4 — positioning-only (insufficient sectors) + boundary equal-to-limit FDP
    rows.append(_row("EA4", "David Mensah", "Captain", "CDG", "2026-07-28", "10:00", "14:00", "EA401DHD", "", "true", "CDG", "", "", "acclimatised"))
    rows.append(_row("EA4", "David Mensah", "Captain", "CDG", "2026-07-30", "06:00", "19:00", "EA402", "9.0", "false", "CDG", "1", "", "acclimatised"))

    return rows


def _faa_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    # FA1 — compliant baseline (JFK)
    for day, start, end, fid, hours in (
        ("2026-08-03", "08:00", "14:00", "FA101", "5.0"),
        ("2026-08-06", "09:00", "15:00", "FA102", "5.0"),
        ("2026-08-10", "08:00", "13:30", "FA103", "4.5"),
    ):
        rows.append(_row("FA1", "Ellen Park", "Captain", "JFK", day, start, end, fid, hours, "false", "JFK", "1", "", "acclimatised"))

    # FA2 — 10 × 10.0 h + 0.1 h inside 672 h → FAA-117-23-B1
    for i in range(10):
        day = f"2026-08-{1 + i:02d}"
        rows.append(
            _row(
                "FA2",
                "Frank Osei",
                "Captain",
                "ORD",
                day,
                "06:00",
                "16:00",
                f"FA2{i:02d}",
                "10.0",
                "false",
                "ORD",
                "1",
                "",
                "acclimatised",
            )
        )
    rows.append(
        _row("FA2", "Frank Osei", "Captain", "ORD", "2026-08-12", "06:00", "08:00", "FA2OVER", "0.1", "false", "ORD", "1", "", "acclimatised")
    )

    # FA3 — 8 h rest (< 10) then Table B exceedance (14.1 > 14)
    rows.append(_row("FA3", "Grace Torres", "First Officer", "DFW", "2026-08-15", "06:00", "20:00", "FA301", "10.0", "false", "DFW", "1", "", "acclimatised"))
    rows.append(_row("FA3", "Grace Torres", "First Officer", "DFW", "2026-08-16", "04:00", "12:00", "FA302", "6.0", "false", "DFW", "1", "", "acclimatised"))
    rows.append(_row("FA3", "Grace Torres", "First Officer", "DFW", "2026-08-20", "07:00", "21:06", "FA303", "11.0", "false", "DFW", "1", "", "acclimatised"))

    # FA4 — no 30 h rest in 168 h + positioning-only insufficient data
    for i in range(8):
        day = f"2026-08-{1 + i:02d}"
        rows.append(
            _row(
                "FA4",
                "Hugo Lefort",
                "Captain",
                "LAX",
                day,
                "06:00",
                "18:00",
                f"FA4{i:02d}",
                "8.0",
                "false",
                "LAX",
                "1",
                "",
                "acclimatised",
            )
        )
    rows.append(_row("FA4", "Hugo Lefort", "Captain", "LAX", "2026-08-14", "10:00", "14:00", "FA4DHD", "", "true", "LAX", "", "", "acclimatised"))

    return rows


def _row(
    crew_id: str,
    crew_name: str,
    position: str,
    home_base: str,
    duty_date: str,
    duty_start: str,
    duty_end: str,
    flight_id: str,
    flight_hours: str,
    is_positioning: str,
    start_location: str,
    sectors: str,
    fdp_hours: str,
    acclimatisation: str,
) -> dict[str, str]:
    return {
        "crew_id": crew_id,
        "crew_name": crew_name,
        "position": position,
        "home_base": home_base,
        "duty_date": duty_date,
        "duty_start": duty_start,
        "duty_end": duty_end,
        "flight_id": flight_id,
        "flight_hours": flight_hours,
        "is_positioning": is_positioning,
        "start_location": start_location,
        "sectors": sectors,
        "fdp_hours": fdp_hours,
        "acclimatisation": acclimatisation,
    }


_SAMPLE_BUILDERS = {
    "easa": ("easa", "EASA", _easa_rows),
    "faa": ("faa_part_117", "FAA", _faa_rows),
}


def list_samples() -> list[dict[str, str]]:
    """UI-facing catalog of downloadable samples."""
    return [
        {
            "sample_id": sample_id,
            "framework_id": framework_id,
            "label": label,
            "csv_name": sample_filename(sample_id, "csv"),
            "xlsx_name": sample_filename(sample_id, "xlsx"),
        }
        for sample_id, (framework_id, label, _) in _SAMPLE_BUILDERS.items()
    ]


def sample_filename(sample_id: str, fmt: str) -> str:
    return f"{sample_id}_sample.{fmt}"


def sample_rows(sample_id: str) -> list[dict[str, str]]:
    if sample_id not in _SAMPLE_BUILDERS:
        raise KeyError(f"Unknown sample_id: {sample_id}")
    return _SAMPLE_BUILDERS[sample_id][2]()


def sample_bytes(sample_id: str, fmt: str = "csv") -> bytes:
    """Return downloadable bytes for a sample roster (csv or xlsx)."""
    rows = sample_rows(sample_id)
    if fmt == "csv":
        return _to_csv(rows)
    if fmt == "xlsx":
        return _to_xlsx(rows, title=f"{sample_id.upper()} sample roster")
    raise ValueError(f"Unsupported sample format: {fmt}")


def is_sample_filename(name: str | None) -> bool:
    if not name:
        return False
    lowered = name.strip().lower()
    return any(
        lowered == sample_filename(sid, fmt)
        for sid in _SAMPLE_BUILDERS
        for fmt in ("csv", "xlsx")
    ) or lowered == "sample_roster.csv"


def _to_csv(rows: Iterable[dict[str, str]]) -> bytes:
    buf = io.StringIO()
    # Leading comment line is not valid CSV for pandas — put disclaimer in a cell note via filename/UI only.
    writer = csv.DictWriter(buf, fieldnames=list(HEADERS), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, "") for key in HEADERS})
    return buf.getvalue().encode("utf-8")


def _to_xlsx(rows: list[dict[str, str]], title: str) -> bytes:
    # First sheet must be header + data rows — load_table reads sheetnames[0] only.
    workbook = Workbook()
    data = workbook.active
    data.title = "Data"
    for col, header in enumerate(HEADERS, start=1):
        data.cell(1, col, header)
    for r_idx, row in enumerate(rows, start=2):
        for c_idx, header in enumerate(HEADERS, start=1):
            data.cell(r_idx, c_idx, row.get(header, ""))
    notes = workbook.create_sheet("About")
    notes["A1"] = DISCLAIMER
    notes["A2"] = title
    notes["A3"] = "Names, IDs, and flight numbers are fictional. Upload the Data sheet contents via the CSV/XLSX download."
    buf = io.BytesIO()
    workbook.save(buf)
    return buf.getvalue()
