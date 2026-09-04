from __future__ import annotations

from crew_compliance.ingestion.mapping import ALIASES

OPENING_FIELDS = (
    "crew_id",
    "crew_name",
    "role",
    "window_type",
    "hours_already_accrued",
    "as_of_date",
    "metric",
)

OPENING_ALIASES: dict[str, tuple[str, ...]] = {
    "crew_id": ALIASES["crew_id"],
    "crew_name": ALIASES["crew_name"],
    "role": ("role", "position", "rank", "function"),
    "window_type": (
        "window_type",
        "window",
        "window type",
        "period",
        "limit type",
        "lookback",
    ),
    "hours_already_accrued": (
        "hours_already_accrued",
        "hours already accrued",
        "opening hours",
        "carry over",
        "carryover",
        "hours",
        "accrued",
    ),
    "as_of_date": ("as_of_date", "as of date", "as-of-date", "as of", "effective date", "date"),
    "metric": ("metric", "hours type", "hour type", "kind"),
}

CREDENTIAL_FIELDS = (
    "crew_id",
    "crew_name",
    "role",
    "credential_type",
    "credential_detail",
    "expiry_date",
)

CREDENTIAL_ALIASES: dict[str, tuple[str, ...]] = {
    "crew_id": ALIASES["crew_id"],
    "crew_name": ALIASES["crew_name"],
    "role": ("role", "position", "rank", "function"),
    "credential_type": (
        "credential_type",
        "credential type",
        "type",
        "certificate type",
        "qual type",
    ),
    "credential_detail": (
        "credential_detail",
        "credential detail",
        "detail",
        "description",
        "rating",
        "notes",
    ),
    "expiry_date": ("expiry_date", "expiry", "expiry date", "expires", "valid until"),
}
