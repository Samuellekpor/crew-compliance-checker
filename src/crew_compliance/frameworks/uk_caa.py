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
from crew_compliance.frameworks.catalog import UK_CAA

EFFECTIVE = date(2014, 2, 18)
VERSION = "1.0.0"
RULESET_ID = "uk-ftl-v1"
COMMON_ASSUMPTIONS = (
    "Times are interpreted as naive operator-local datetimes; time zones are not converted.",
    "Assimilated ORO.FTL consecutive-day limits use calendar dates, not exact 24-hour multiples.",
    "CAWTR reg. 9(a)/(b) windows are screened as 12 consecutive calendar months; the statute measures "
    "the 12 months expiring at the end of the month before the month in question.",
    "CAWTR working time uses roster duty hours as a proxy; standby counting in reg. 9A is not applied.",
)
COMMON_LIMITATIONS = (
    "Daily FDP tables and CS-FTL.1 are not implemented.",
    "Standby, reserve, split duty, reduced rest, commander's discretion, and operator FTSS are not modeled.",
    "This is a screening review, not an approved compliance-monitoring system or legal determination.",
)


def _meta(rule_id: str, name: str, citation: str, description: str, parameters: dict, extra_lim: tuple[str, ...] = (), mode: str = "full") -> RuleMetadata:
    return RuleMetadata(
        rule_id=rule_id,
        name=name,
        framework_id=UK_CAA.id,
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
                "UK-FTL-210-B1",
                "Maximum flight time — 100 h / 28 consecutive days",
                "UK ORO.FTL.210(b)(1)",
                "Total operating flight time in any 28 consecutive calendar days shall not exceed 100 hours.",
                {"window_days": 28, "limit_hours": 100, "opening_window": "28day", "opening_metric": "flight_time"},
            ),
            metric="flight_time",
        ),
        CalendarYearFlightRule(
            _meta(
                "UK-FTL-210-B2",
                "Maximum flight time — 900 h / calendar year",
                "UK ORO.FTL.210(b)(2)",
                "Total operating flight time in any calendar year shall not exceed 900 hours.",
                {"limit_hours": 900, "opening_window": "annual", "opening_metric": "flight_time"},
            )
        ),
        CalendarMonthsFlightRule(
            _meta(
                "UK-FTL-210-B3",
                "Maximum flight time — 1000 h / 12 calendar months",
                "UK ORO.FTL.210(b)(3)",
                "Total operating flight time in any 12 consecutive calendar months shall not exceed 1000 hours.",
                {"limit_hours": 1000, "window_months": 12, "opening_window": "12month", "opening_metric": "flight_time"},
            )
        ),
        CalendarDayHoursRule(
            _meta(
                "UK-FTL-210-A1",
                "Maximum duty — 60 h / 7 consecutive days",
                "UK ORO.FTL.210(a)(1)",
                "Total duty periods in any 7 consecutive calendar days shall not exceed 60 hours.",
                {"window_days": 7, "limit_hours": 60, "opening_window": "7day", "opening_metric": "duty_hours"},
            ),
            metric="duty_hours",
        ),
        CalendarDayHoursRule(
            _meta(
                "UK-FTL-210-A2",
                "Maximum duty — 110 h / 14 consecutive days",
                "UK ORO.FTL.210(a)(2)",
                "Total duty periods in any 14 consecutive calendar days shall not exceed 110 hours.",
                {"window_days": 14, "limit_hours": 110, "opening_window": "14day", "opening_metric": "duty_hours"},
            ),
            metric="duty_hours",
        ),
        CalendarDayHoursRule(
            _meta(
                "UK-FTL-210-A3",
                "Maximum duty — 190 h / 28 consecutive days",
                "UK ORO.FTL.210(a)(3)",
                "Total duty periods in any 28 consecutive calendar days shall not exceed 190 hours.",
                {"window_days": 28, "limit_hours": 190, "opening_window": "28day", "opening_metric": "duty_hours"},
            ),
            metric="duty_hours",
        ),
        MinRestBeforeDutyRule(
            _meta(
                "UK-FTL-235-MINREST",
                "Minimum rest before FDP",
                "UK ORO.FTL.235(a)(1) and (b)",
                "Rest before the next FDP must be at least as long as the preceding duty period, "
                "or 12 hours at home base / 10 hours away from home base, whichever is greater.",
                {"home_base_floor_hours": 12, "away_floor_hours": 10},
                extra_lim=("Reduced rest and the 8-hour sleep opportunity inside rest are not modeled.",),
            )
        ),
        RecurrentExtendedRestScreenRule(
            _meta(
                "UK-FTL-235-D-SCREEN",
                "Recurrent extended recovery rest — partial screen",
                "UK ORO.FTL.235(d)",
                "Partial screen for a 36-hour rest with no more than 168 hours from the end of one "
                "such rest to the start of the next. Two local nights are not evaluated.",
                {"rest_hours": 36, "max_gap_hours": 168},
                extra_lim=("Two local nights are not evaluated.",),
                mode="partial",
            )
        ),
        CalendarMonthsFlightRule(
            _meta(
                "UK-CAWTR-9-A",
                "CAWTR — 900 h block flying time / 12 months",
                "Civil Aviation (Working Time) Regulations 2004 reg. 9(a)",
                "No person may act as a crew member if aggregate block flying time in the 12 months "
                "expiring at the end of the previous month exceeds 900 hours.",
                {"limit_hours": 900, "window_months": 12, "opening_window": "12month", "opening_metric": "flight_time"},
                extra_lim=(
                    "Screened as any 12 consecutive calendar months of operating flight time on the roster, "
                    "not the statutory month-end lookback.",
                ),
            )
        ),
        CalendarMonthsFlightRule(
            _meta(
                "UK-CAWTR-9-B",
                "CAWTR — 2000 h working time / 12 months",
                "Civil Aviation (Working Time) Regulations 2004 reg. 9(b)",
                "Total annual working time shall not exceed 2,000 hours in the 12 months expiring "
                "at the end of the previous month.",
                {
                    "limit_hours": 2000,
                    "window_months": 12,
                    "metric": "duty_hours",
                    "opening_window": "12month",
                    "opening_metric": "duty_hours",
                },
                extra_lim=("Standby counting under regulation 9A is not applied. Duty span is the working-time proxy.",),
            )
        ),
    )
    return Ruleset(
        id=RULESET_ID,
        version=VERSION,
        framework_id=UK_CAA.id,
        display_name="UK CAA FTL screening ruleset v1",
        effective_date=EFFECTIVE,
        rules=rules,
        assumptions=COMMON_ASSUMPTIONS,
        limitations=COMMON_LIMITATIONS,
    )


def register() -> None:
    register_ruleset(build_ruleset())
