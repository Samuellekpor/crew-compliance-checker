from __future__ import annotations

from datetime import date

from crew_compliance.domain.models import RuleMetadata, Ruleset
from crew_compliance.engine.hour_rules import (
    CalendarDayHoursRule,
    CalendarMonthsFlightRule,
    CalendarYearFlightRule,
)
from crew_compliance.engine.registry import register_ruleset
from crew_compliance.engine.rest_rules import MinRestBeforeDutyRule, RecurrentExtendedRestScreenRule
from crew_compliance.frameworks.catalog import EASA

EFFECTIVE = date(2014, 2, 18)
VERSION = "1.0.0"
RULESET_ID = "easa-ftl-v1"
COMMON_ASSUMPTIONS = (
    "Times are interpreted as naive operator-local datetimes; time zones are not converted.",
    "Consecutive-day limits use calendar dates, not exact 24-hour multiples.",
    "Positioning counts as duty and does not count as operating flight time (ORO.FTL.215(b)).",
    "Where only a duty date and block hours exist, those hours are treated as operating flight time on that date.",
)
COMMON_LIMITATIONS = (
    "Daily FDP tables (ORO.FTL.205 / CS-FTL.1) are not implemented.",
    "Standby, reserve, split duty, reduced rest, commander's discretion, and operator-specific FTSS are not modeled.",
    "This is a screening review, not an approved compliance-monitoring system or legal determination.",
)


def _meta(rule_id: str, name: str, citation: str, description: str, parameters: dict, extra_lim: tuple[str, ...] = (), mode: str = "full") -> RuleMetadata:
    return RuleMetadata(
        rule_id=rule_id,
        name=name,
        framework_id=EASA.id,
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
        evaluation_mode=mode,
        required_inputs=frozenset(parameters.get("required_inputs", ())),
    )


def build_ruleset() -> Ruleset:
    rules = (
        CalendarDayHoursRule(
            _meta(
                "EASA-FTL-210-B1",
                "Maximum flight time — 100 h / 28 consecutive days",
                "ORO.FTL.210(b)(1)",
                "Total operating flight time in any 28 consecutive calendar days shall not exceed 100 hours.",
                {"window_days": 28, "limit_hours": 100},
            ),
            metric="flight_time",
        ),
        CalendarYearFlightRule(
            _meta(
                "EASA-FTL-210-B2",
                "Maximum flight time — 900 h / calendar year",
                "ORO.FTL.210(b)(2)",
                "Total operating flight time in any calendar year shall not exceed 900 hours.",
                {"limit_hours": 900},
            )
        ),
        CalendarMonthsFlightRule(
            _meta(
                "EASA-FTL-210-B3",
                "Maximum flight time — 1000 h / 12 calendar months",
                "ORO.FTL.210(b)(3)",
                "Total operating flight time in any 12 consecutive calendar months shall not exceed 1000 hours.",
                {"limit_hours": 1000, "window_months": 12},
            )
        ),
        CalendarDayHoursRule(
            _meta(
                "EASA-FTL-210-A1",
                "Maximum duty — 60 h / 7 consecutive days",
                "ORO.FTL.210(a)(1)",
                "Total duty periods in any 7 consecutive calendar days shall not exceed 60 hours.",
                {"window_days": 7, "limit_hours": 60},
                extra_lim=('The qualitative "spread as evenly as practicable" requirement is not evaluated.',),
            ),
            metric="duty_hours",
        ),
        CalendarDayHoursRule(
            _meta(
                "EASA-FTL-210-A2",
                "Maximum duty — 110 h / 14 consecutive days",
                "ORO.FTL.210(a)(2)",
                "Total duty periods in any 14 consecutive calendar days shall not exceed 110 hours.",
                {"window_days": 14, "limit_hours": 110},
            ),
            metric="duty_hours",
        ),
        CalendarDayHoursRule(
            _meta(
                "EASA-FTL-210-A3",
                "Maximum duty — 190 h / 28 consecutive days",
                "ORO.FTL.210(a)(3)",
                "Total duty periods in any 28 consecutive calendar days shall not exceed 190 hours.",
                {"window_days": 28, "limit_hours": 190},
            ),
            metric="duty_hours",
        ),
        MinRestBeforeDutyRule(
            _meta(
                "EASA-FTL-235-MINREST",
                "Minimum rest before FDP",
                "ORO.FTL.235(a)(1) and (b)",
                "Rest before the next FDP must be at least as long as the preceding duty period, "
                "or 12 hours at home base / 10 hours away from home base, whichever is greater.",
                {"home_base_floor_hours": 12, "away_floor_hours": 10},
                extra_lim=(
                    "8-hour sleep opportunity, travel time to suitable accommodation, and reduced rest are not modeled.",
                    "V1 applies the rest test before the next duty period (FDP is not separately identified).",
                ),
            )
        ),
        RecurrentExtendedRestScreenRule(
            _meta(
                "EASA-FTL-235-D-SCREEN",
                "Recurrent extended recovery rest — partial screen",
                "ORO.FTL.235(d)",
                "Partial screen for a 36-hour rest with no more than 168 hours from the end of one "
                "such rest to the start of the next. Two local nights are not evaluated.",
                {"rest_hours": 36, "max_gap_hours": 168},
                extra_lim=(
                    "Two local nights, twice-per-month local days, and CS-FTL.1.235 additions are not evaluated.",
                ),
                mode="partial",
            )
        ),
    )
    return Ruleset(
        id=RULESET_ID,
        version=VERSION,
        framework_id=EASA.id,
        display_name="EASA FTL screening ruleset v1",
        effective_date=EFFECTIVE,
        rules=rules,
        assumptions=COMMON_ASSUMPTIONS,
        limitations=COMMON_LIMITATIONS,
    )


def register() -> None:
    register_ruleset(build_ruleset())