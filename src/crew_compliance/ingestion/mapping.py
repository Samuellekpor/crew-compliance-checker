from __future__ import annotations

CANONICAL_FIELDS = (
    "crew_id",
    "crew_name",
    "position",
    "home_base",
    "duty_date",
    "duty_start",
    "duty_end",
    "flight_id",
    "flight_start",
    "flight_end",
    "flight_hours",
    "is_positioning",
    "duty_kind",
    "start_location",
    "end_location",
    "captain",
    "first_officer",
)

ALIASES: dict[str, tuple[str, ...]] = {
    "crew_id": ("crew_id", "crew", "crew member", "crewmember", "name", "staff no", "staff_no", "emp id"),
    "crew_name": ("crew_name", "crew name", "full name"),
    "position": ("position", "rank", "role", "function"),
    "home_base": ("home_base", "home base", "base"),
    "duty_date": ("duty_date", "date", "duty date", "flight date", "roster date"),
    "duty_start": ("duty_start", "duty start", "report", "report time", "check in", "check-in"),
    "duty_end": ("duty_end", "duty end", "release", "off duty", "duty finish"),
    "flight_id": ("flight_id", "flight", "flight no", "flightno", "flt", "sector", "pairing"),
    "flight_start": ("flight_start", "std", "atd", "block off", "off block", "dep", "departure"),
    "flight_end": ("flight_end", "sta", "ata", "block on", "on block", "arr", "arrival"),
    "flight_hours": ("flight_hours", "hours", "block hours", "block", "ft", "flight time"),
    "is_positioning": ("is_positioning", "positioning", "deadhead", "dhd", "paxing"),
    "duty_kind": ("duty_kind", "duty type", "dutytype", "type"),
    "start_location": ("start_location", "from", "origin", "dep station", "report station"),
    "end_location": ("end_location", "to", "destination", "arr station"),
    "captain": ("captain", "pic", "pilot in command", "cmd", "commander"),
    "first_officer": ("first officer", "firstofficer", "fo", "f/o", "sic"),
}


def normalize_header(value: str) -> str:
    return " ".join(str(value).strip().lower().replace("_", " ").split())


def auto_map_columns(
    headers: list[str],
    fields: tuple[str, ...] | None = None,
    aliases: dict[str, tuple[str, ...]] | None = None,
    prior: dict[str, str | None] | None = None,
) -> dict[str, str | None]:
    lookup = {normalize_header(h): h for h in headers}
    header_set = set(headers)
    use_fields = fields or CANONICAL_FIELDS
    use_aliases = aliases or ALIASES
    mapping: dict[str, str | None] = {field: None for field in use_fields}
    if prior:
        for field in use_fields:
            header = prior.get(field)
            if header in header_set:
                mapping[field] = header
    for field, field_aliases in use_aliases.items():
        if field not in mapping or mapping[field]:
            continue
        for alias in field_aliases:
            header = lookup.get(normalize_header(alias))
            if header:
                mapping[field] = header
                break
    return mapping