from __future__ import annotations

WINDOW_ALIASES: dict[str, str] = {
    "7day": "7day",
    "7-day": "7day",
    "7 day": "7day",
    "7 days": "7day",
    "14day": "14day",
    "14-day": "14day",
    "14 day": "14day",
    "14 days": "14day",
    "28day": "28day",
    "28-day": "28day",
    "28 day": "28day",
    "28 days": "28day",
    "28day_flight": "28day",
    "28day flight": "28day",
    "28day_duty": "28day_duty",
    "28day duty": "28day_duty",
    "annual": "annual",
    "calendar year": "annual",
    "year": "annual",
    "900h": "annual",
    "12month": "12month",
    "12-month": "12month",
    "12 month": "12month",
    "12 months": "12month",
    "1000h": "12month",
    "168h": "168h",
    "168": "168h",
    "168 hour": "168h",
    "168 hours": "168h",
    "672h": "672h",
    "672": "672h",
    "672 hour": "672h",
    "672 hours": "672h",
    "672h_fdp": "672h_fdp",
    "672h fdp": "672h_fdp",
    "365day": "365day",
    "365": "365day",
    "365 day": "365day",
    "365 days": "365day",
    "other": "other",
}

METRIC_ALIASES: dict[str, str] = {
    "flight": "flight_time",
    "flight_time": "flight_time",
    "flight time": "flight_time",
    "block": "flight_time",
    "duty": "duty_hours",
    "duty_hours": "duty_hours",
    "duty hours": "duty_hours",
    "fdp": "fdp",
    "fdp_proxy": "fdp",
}


def normalize_window_type(value: str | None) -> str | None:
    if not value:
        return None
    key = " ".join(str(value).strip().lower().replace("_", " ").split())
    compact = key.replace(" ", "")
    return WINDOW_ALIASES.get(key) or WINDOW_ALIASES.get(compact) or compact or None


def normalize_metric(value: str | None) -> str | None:
    if not value:
        return None
    key = " ".join(str(value).strip().lower().replace("_", " ").split())
    return METRIC_ALIASES.get(key) or METRIC_ALIASES.get(key.replace(" ", "_"))
