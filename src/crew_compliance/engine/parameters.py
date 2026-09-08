from __future__ import annotations

from crew_compliance.domain.models import Ruleset

NUMERIC_OVERRIDE_KEYS = (
    "limit_hours",
    "window_days",
    "window_hours",
    "window_months",
    "home_base_floor_hours",
    "away_floor_hours",
    "fixed_floor_hours",
    "lookback_hours",
    "required_consecutive_rest_hours",
    "rest_hours",
    "max_gap_hours",
)


def editable_slots(ruleset: Ruleset) -> list[dict]:
    slots: list[dict] = []
    for rule in ruleset.rules:
        metadata = rule.metadata
        for key in NUMERIC_OVERRIDE_KEYS:
            if key not in metadata.parameters:
                continue
            value = metadata.parameters[key]
            if value is None:
                continue
            slots.append(
                {
                    "rule_id": metadata.rule_id,
                    "rule_name": metadata.name,
                    "citation": metadata.citation,
                    "key": key,
                    "default": float(value),
                }
            )
    return slots
