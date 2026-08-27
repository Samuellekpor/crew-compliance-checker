from __future__ import annotations

from crew_compliance.domain.enums import DutyKind, Position
from crew_compliance.ingestion.parse import parse_bool, parse_date, parse_datetime, parse_hours

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_ROWS = 50_000


class IngestError(Exception):
    pass


def classify_position(value: str | None) -> Position:
    if not value:
        return Position.UNKNOWN
    text = value.strip().lower()
    if text in {"captain", "cpt", "pic", "cmd", "commander", "ca"}:
        return Position.CAPTAIN
    if text in {"first officer", "fo", "f/o", "sic", "first_officer"}:
        return Position.FO
    return Position.UNKNOWN


def classify_duty_kind(value: str | None, is_positioning: bool) -> DutyKind:
    if is_positioning:
        return DutyKind.POSITIONING
    if not value:
        return DutyKind.UNKNOWN
    text = value.strip().lower()
    if text in {"positioning", "deadhead", "dhd"}:
        return DutyKind.POSITIONING
    if text in {"flight", "operating", "sector", "op"}:
        return DutyKind.OPERATING_FLIGHT
    if text in {"standby", "reserve", "training", "office", "sim"}:
        return DutyKind.OTHER
    return DutyKind.UNKNOWN


def mapped_value(row: dict, mapping: dict[str, str | None], field: str):
    header = mapping.get(field)
    if not header:
        return None
    return row.get(header)


def build_duty_kwargs(row: dict, mapping: dict[str, str | None], dayfirst: bool) -> dict:
    duty_date = parse_date(mapped_value(row, mapping, "duty_date"), dayfirst=dayfirst)
    start_raw = mapped_value(row, mapping, "duty_start")
    end_raw = mapped_value(row, mapping, "duty_end")
    duty_start = parse_datetime(duty_date, start_raw, dayfirst=dayfirst) if duty_date else parse_datetime(start_raw, None, dayfirst=dayfirst)
    duty_end = parse_datetime(duty_date, end_raw, dayfirst=dayfirst) if duty_date else parse_datetime(end_raw, None, dayfirst=dayfirst)
    flight_hours = parse_hours(mapped_value(row, mapping, "flight_hours"))
    is_positioning = parse_bool(mapped_value(row, mapping, "is_positioning"))
    kind = classify_duty_kind(
        None if mapped_value(row, mapping, "duty_kind") is None else str(mapped_value(row, mapping, "duty_kind")),
        is_positioning,
    )
    if kind == DutyKind.POSITIONING:
        is_positioning = True
    return {
        "duty_date": duty_date,
        "duty_start": duty_start,
        "duty_end": duty_end,
        "flight_id": _str(mapped_value(row, mapping, "flight_id")),
        "flight_start": parse_datetime(duty_date, mapped_value(row, mapping, "flight_start"), dayfirst=dayfirst)
        if duty_date
        else parse_datetime(mapped_value(row, mapping, "flight_start"), None, dayfirst=dayfirst),
        "flight_end": parse_datetime(duty_date, mapped_value(row, mapping, "flight_end"), dayfirst=dayfirst)
        if duty_date
        else parse_datetime(mapped_value(row, mapping, "flight_end"), None, dayfirst=dayfirst),
        "flight_hours": flight_hours,
        "is_positioning": is_positioning,
        "duty_kind": kind,
        "home_base": _str(mapped_value(row, mapping, "home_base")),
        "start_location": _str(mapped_value(row, mapping, "start_location")),
        "end_location": _str(mapped_value(row, mapping, "end_location")),
        "position": classify_position(_str(mapped_value(row, mapping, "position"))),
    }


def _str(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "nat"}:
        return None
    return text