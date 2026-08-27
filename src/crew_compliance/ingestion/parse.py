from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

import pandas as pd


def parse_bool(value: Any) -> bool:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "positioning", "deadhead", "dhd"}


def parse_date(value: Any, dayfirst: bool = False) -> date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return pd.to_datetime(value, unit="d", origin="1899-12-30").date()
        except (ValueError, OverflowError, Exception):
            return None
    parsed = pd.to_datetime(value, errors="coerce", dayfirst=dayfirst)
    if pd.isna(parsed):
        return None
    return parsed.date()


def parse_time(value: Any) -> time | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, time):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= float(value) < 1.5:
        minutes = int(round(float(value) * 24 * 60))
        minutes = minutes % (24 * 60)
        return time(minutes // 60, minutes % 60)
    parsed = pd.to_datetime(str(value).strip(), errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.time()


def parse_datetime(date_val: Any, time_val: Any | None, dayfirst: bool = False) -> datetime | None:
    if isinstance(date_val, datetime) and time_val is None:
        return date_val.replace(tzinfo=None)
    d = parse_date(date_val, dayfirst=dayfirst)
    if d is None:
        if isinstance(date_val, str) and " " in date_val.strip():
            parsed = pd.to_datetime(date_val, errors="coerce", dayfirst=dayfirst)
            if not pd.isna(parsed):
                return parsed.to_pydatetime().replace(tzinfo=None)
        return None
    if time_val is None or (isinstance(time_val, float) and pd.isna(time_val)):
        return datetime.combine(d, time.min)
    if isinstance(time_val, datetime):
        return datetime.combine(d, time_val.time())
    t = parse_time(time_val)
    if t is None:
        return None
    return datetime.combine(d, t)


def parse_hours(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = str(value).strip().replace(",", ".")
    if ":" in text:
        parts = text.split(":")
        try:
            hours = int(parts[0])
            minutes = int(parts[1]) if len(parts) > 1 else 0
            return hours + minutes / 60.0
        except ValueError:
            return None
    try:
        return float(text)
    except ValueError:
        return None


def apply_overnight_wrap(start: datetime, end: datetime) -> datetime:
    if end.date() == start.date() and end.time() <= start.time():
        return end + timedelta(days=1)
    return end