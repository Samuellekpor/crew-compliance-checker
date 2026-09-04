from __future__ import annotations

from datetime import date

from crew_compliance.domain.models import RuleMetadata, Ruleset
from crew_compliance.engine.hour_rules import CalendarDayHoursRule
from crew_compliance.engine.registry import register_ruleset
from crew_compliance.engine.rest_rules import MinRestBeforeDutyRule
from crew_compliance.frameworks.catalog import TRANSPORT_CANADA

EFFECTIVE = date(2018, 12, 12)
VERSION = "1.0.0"
RULESET_ID = "tc-cars-700-v1"
COMMON_ASSUMPTIONS = (
    "Times are interpreted as naive operator-local datetimes; time zones are not converted.",
    "Hours of work are taken from roster duty start–end. Reserve 33% and standby 100% counting in 700.29(3) are not applied.",
    "The 7-day hours-of-work screen uses the 60-hour limit in 700.29(1)(c), not the 70-hour 700.29(1)(d) option.",
)
COMMON_LIMITATIONS = (
    "Maximum FDP tables in 700.28, acclimatization, split duty, reserve, and FRMS exemptions are not implemented.",
    "Single-pilot 8 h / 24 h in 700.27(1)(d) is not evaluated.",
    "Rest travel time (11 h plus travel) and 10 h in suitable accommodation at home base are not distinguished; "
    "the screen uses 12 h at home base and 10 h away.",
    "This is a screening review, not an approved compliance-monitoring system or legal determination.",
)


def _meta(rule_id: str, name: str, citation: str, description: str, parameters: dict, extra_lim: tuple[str, ...] = ()) -> RuleMetadata:
    return RuleMetadata(
        rule_id=rule_id,
        name=name,
        framework_id=TRANSPORT_CANADA.id,
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
        CalendarDayHoursRule(
            _meta(
                "TC-700-27-A",
                "Flight time — 112 h / 28 consecutive days",
                "CAR 700.27(1)(a)",
                "An air operator shall not assign flight time if total flight time would exceed 112 hours in any 28 consecutive days.",
                {"window_days": 28, "limit_hours": 112, "opening_window": "28day", "opening_metric": "flight_time"},
            ),
            metric="flight_time",
        ),
        CalendarDayHoursRule(
            _meta(
                "TC-700-27-B",
                "Flight time — 300 h / 90 consecutive days",
                "CAR 700.27(1)(b)",
                "An air operator shall not assign flight time if total flight time would exceed 300 hours in any 90 consecutive days.",
                {"window_days": 90, "limit_hours": 300, "opening_window": "90day", "opening_metric": "flight_time"},
            ),
            metric="flight_time",
        ),
        CalendarDayHoursRule(
            _meta(
                "TC-700-27-C",
                "Flight time — 1000 h / 365 consecutive days",
                "CAR 700.27(1)(c)",
                "An air operator shall not assign flight time if total flight time would exceed 1,000 hours in any 365 consecutive days.",
                {"window_days": 365, "limit_hours": 1000, "opening_window": "365day", "opening_metric": "flight_time"},
            ),
            metric="flight_time",
        ),
        CalendarDayHoursRule(
            _meta(
                "TC-700-29-B",
                "Hours of work — 192 h / 28 consecutive days",
                "CAR 700.29(1)(b)",
                "An air operator shall not assign an FDP if hours of work would exceed 192 hours in any 28 consecutive days.",
                {"window_days": 28, "limit_hours": 192, "opening_window": "28day", "opening_metric": "duty_hours"},
            ),
            metric="duty_hours",
        ),
        CalendarDayHoursRule(
            _meta(
                "TC-700-29-C",
                "Hours of work — 60 h / 7 consecutive days",
                "CAR 700.29(1)(c)",
                "An air operator shall not assign an FDP if hours of work would exceed 60 hours in any 7 consecutive days "
                "(single-day-free-from-duty scheme). The 70-hour alternative in 700.29(1)(d) is not this screen.",
                {"window_days": 7, "limit_hours": 60, "opening_window": "7day", "opening_metric": "duty_hours"},
                extra_lim=("Single days free from duty in 700.29(1)(c)(i)–(ii) are not verified.",),
            ),
            metric="duty_hours",
        ),
        CalendarDayHoursRule(
            _meta(
                "TC-700-29-A",
                "Hours of work — 2200 h / 365 consecutive days",
                "CAR 700.29(1)(a)",
                "An air operator shall not assign an FDP if hours of work would exceed 2,200 hours in any 365 consecutive days.",
                {"window_days": 365, "limit_hours": 2200, "opening_window": "365day", "opening_metric": "duty_hours"},
            ),
            metric="duty_hours",
        ),
        MinRestBeforeDutyRule(
            _meta(
                "TC-700-40",
                "Rest after FDP — 12 h home / 10 h away",
                "CAR 700.40(1)",
                "Rest at the end of an FDP is screened before the next duty as at least 12 hours if the next duty "
                "starts at home base, or 10 hours away from home base.",
                {"home_base_floor_hours": 12, "away_floor_hours": 10, "use_preceding": False},
            )
        ),
    )
    return Ruleset(
        id=RULESET_ID,
        version=VERSION,
        framework_id=TRANSPORT_CANADA.id,
        display_name="Transport Canada CARS 700 screening ruleset v1",
        effective_date=EFFECTIVE,
        rules=rules,
        assumptions=COMMON_ASSUMPTIONS,
        limitations=COMMON_LIMITATIONS,
    )


def register() -> None:
    register_ruleset(build_ruleset())
