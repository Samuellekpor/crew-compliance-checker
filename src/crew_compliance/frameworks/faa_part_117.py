from __future__ import annotations

from datetime import date

from crew_compliance.domain.models import RuleMetadata, Ruleset
from crew_compliance.engine.hour_rules import RollingFlightHoursRule, RollingHoursOverlapRule
from crew_compliance.engine.registry import register_ruleset
from crew_compliance.engine.rest_rules import LookbackConsecutiveRestRule, MinRestBeforeDutyRule
from crew_compliance.frameworks.catalog import FAA_PART_117

EFFECTIVE = date(2014, 1, 4)
VERSION = "1.0.0"
RULESET_ID = "faa-117-v1"
COMMON_ASSUMPTIONS = (
    "Times are interpreted as naive operator-local datetimes; time zones are not converted.",
    "Where true FDP is not provided, duty start-to-end is used as an FDP proxy and is disclosed on findings.",
    "Positioning after the last operating sector can make duty longer than FDP; that inflates the FDP proxy.",
    "Cumulative limits cannot include flying for other certificate holders that is absent from the file (117.23(a)).",
)
COMMON_LIMITATIONS = (
    "Acclimated/theater status, Tables A/B/C, unaugmented vs augmented FDP, split duty, reserve, and 117.19 extensions are not implemented.",
    "117.11 daily flight time, 117.13/117.17 FDP, 117.25(c)(d)(f)(g), 117.27 consecutive nights, and the 8-hour sleep opportunity inside rest are not modeled.",
    "This framework must not be applied to Part 135 or all-cargo Part 121 operations.",
    "This is a screening review, not an approved compliance-monitoring system or legal determination.",
)


def _meta(rule_id: str, name: str, citation: str, description: str, parameters: dict, extra_lim: tuple[str, ...] = ()) -> RuleMetadata:
    return RuleMetadata(
        rule_id=rule_id,
        name=name,
        framework_id=FAA_PART_117.id,
        ruleset_id=RULESET_ID,
        ruleset_version=VERSION,
        rule_version="1.0.0",
        effective_date=EFFECTIVE,
        citation=citation,
        description=description,
        parameters=parameters,
        assumptions=COMMON_ASSUMPTIONS,
        limitations=COMMON_LIMITATIONS + extra_lim,
        exceptions_not_modeled=COMMON_LIMITATIONS,
        evaluation_mode="full",
    )


def build_ruleset() -> Ruleset:
    rules = (
        RollingFlightHoursRule(
            _meta(
                "FAA-117-23-B1",
                "Flight time — 100 h / 672 consecutive hours",
                "14 CFR § 117.23(b)(1)",
                "No flightcrew member may accept an assignment if total flight time would exceed 100 hours in any 672 consecutive hours.",
                {"window_hours": 672, "limit_hours": 100, "opening_window": "672h", "opening_metric": "flight_time"},
            )
        ),
        RollingFlightHoursRule(
            _meta(
                "FAA-117-23-B2",
                "Flight time — 1000 h / 365 consecutive calendar days",
                "14 CFR § 117.23(b)(2)",
                "No flightcrew member may accept an assignment if total flight time would exceed 1,000 hours in any 365 consecutive calendar days.",
                {"window_hours": 0, "window_days": 365, "limit_hours": 1000, "opening_window": "365day", "opening_metric": "flight_time"},
            )
        ),
        RollingHoursOverlapRule(
            _meta(
                "FAA-117-23-C1",
                "FDP — 60 h / 168 consecutive hours",
                "14 CFR § 117.23(c)(1)",
                "No flightcrew member may accept an assignment if total FDP would exceed 60 hours in any 168 consecutive hours.",
                {"window_hours": 168, "limit_hours": 60, "metric": "fdp_proxy", "opening_window": "168h", "opening_metric": "fdp"},
            )
        ),
        RollingHoursOverlapRule(
            _meta(
                "FAA-117-23-C2",
                "FDP — 190 h / 672 consecutive hours",
                "14 CFR § 117.23(c)(2)",
                "No flightcrew member may accept an assignment if total FDP would exceed 190 hours in any 672 consecutive hours.",
                {"window_hours": 672, "limit_hours": 190, "metric": "fdp_proxy", "opening_window": "672h", "opening_metric": "fdp"},
            )
        ),
        MinRestBeforeDutyRule(
            _meta(
                "FAA-117-25-E",
                "Rest immediately before FDP — 10 consecutive hours",
                "14 CFR § 117.25(e)",
                "A flightcrew member must be given at least 10 consecutive hours of rest immediately before beginning a reserve or FDP.",
                {"fixed_floor_hours": 10, "use_preceding": False},
                extra_lim=("The 8-hour sleep opportunity inside the rest period is not evaluated. Reserve vs FDP is not distinguished.",),
            )
        ),
        LookbackConsecutiveRestRule(
            _meta(
                "FAA-117-25-B",
                "30 consecutive hours rest in the prior 168 hours",
                "14 CFR § 117.25(b)",
                "Before beginning any reserve or FDP, a flightcrew member must be given at least 30 consecutive hours free from all duty in the 168 consecutive hours before the beginning of the reserve or FDP.",
                {"lookback_hours": 168, "required_consecutive_rest_hours": 30},
                extra_lim=("The 36-hour new-theater substitute in 117.25(c) is not modeled.",),
            )
        ),
    )
    return Ruleset(
        id=RULESET_ID,
        version=VERSION,
        framework_id=FAA_PART_117.id,
        display_name="FAA Part 117 screening ruleset v1",
        effective_date=EFFECTIVE,
        rules=rules,
        assumptions=COMMON_ASSUMPTIONS,
        limitations=COMMON_LIMITATIONS,
    )


def register() -> None:
    register_ruleset(build_ruleset())