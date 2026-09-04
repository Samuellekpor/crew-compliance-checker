from __future__ import annotations

from datetime import date

from crew_compliance.domain.models import RuleMetadata, Ruleset
from crew_compliance.engine.hour_rules import CalendarDayHoursRule, RollingFlightHoursRule, RollingHoursOverlapRule
from crew_compliance.engine.registry import register_ruleset
from crew_compliance.engine.rest_rules import MinRestBeforeDutyRule
from crew_compliance.frameworks.catalog import CASA

EFFECTIVE = date(2019, 11, 18)
VERSION = "1.0.0"
RULESET_ID = "casa-48-1-a2-v1"
COMMON_ASSUMPTIONS = (
    "Times are interpreted as naive operator-local datetimes; time zones are not converted.",
    "This screen assumes the operator is using CAO 48.1 Appendix 2 (multi-pilot, not flight training).",
    "Off-duty immediately before the next duty is used as a proxy for the Appendix 2 clause 1 sleep-opportunity window.",
)
COMMON_LIMITATIONS = (
    "Appendix 2 Tables 2.1 / 3.1 FDP by acclimatised time and sectors are not implemented.",
    "Appendices 1 and 3–7, FRMS, split duty, late-FDP counts, and augmented operations are not modeled.",
    "The 8-hour sleep opportunity inside the 10/12-hour off-duty window is not separately verified.",
    "This is a screening review, not an approved compliance-monitoring system or legal determination.",
)


def _meta(rule_id: str, name: str, citation: str, description: str, parameters: dict, extra_lim: tuple[str, ...] = ()) -> RuleMetadata:
    return RuleMetadata(
        rule_id=rule_id,
        name=name,
        framework_id=CASA.id,
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
                "CASA-48-A2-11-1",
                "Cumulative flight time — 100 h / 28 days",
                "CAO 48.1 Appendix 2 cl 11.1",
                "Cumulative flight time during any consecutive 28-day period must not exceed 100 hours.",
                {"window_days": 28, "limit_hours": 100, "opening_window": "28day", "opening_metric": "flight_time"},
            ),
            metric="flight_time",
        ),
        RollingFlightHoursRule(
            _meta(
                "CASA-48-A2-11-2",
                "Cumulative flight time — 1000 h / 365 days",
                "CAO 48.1 Appendix 2 cl 11.2",
                "Cumulative flight time during any consecutive 365-day period must not exceed 1,000 hours.",
                {"window_hours": 0, "window_days": 365, "limit_hours": 1000, "opening_window": "365day", "opening_metric": "flight_time"},
            )
        ),
        RollingHoursOverlapRule(
            _meta(
                "CASA-48-A2-12-1",
                "Cumulative duty — 60 h / 168 consecutive hours",
                "CAO 48.1 Appendix 2 cl 12.1",
                "Cumulative duty during any consecutive 168-hour period must not exceed 60 hours.",
                {"window_hours": 168, "limit_hours": 60, "opening_window": "168h", "opening_metric": "duty_hours"},
            )
        ),
        RollingHoursOverlapRule(
            _meta(
                "CASA-48-A2-12-2",
                "Cumulative duty — 100 h / 336 consecutive hours",
                "CAO 48.1 Appendix 2 cl 12.2",
                "Cumulative duty during any consecutive 336-hour period must not exceed 100 hours.",
                {"window_hours": 336, "limit_hours": 100, "opening_window": "336h", "opening_metric": "duty_hours"},
            )
        ),
        MinRestBeforeDutyRule(
            _meta(
                "CASA-48-A2-1",
                "Off-duty before FDP — 12 h home / 10 h away",
                "CAO 48.1 Appendix 2 cl 1.1–1.2",
                "An FCM must have an off-duty period of at least 12 hours immediately before an FDP commencing "
                "at home base, or 10 hours away from home base, as the window that must contain 8 hours of sleep opportunity.",
                {"home_base_floor_hours": 12, "away_floor_hours": 10, "use_preceding": False},
            )
        ),
    )
    return Ruleset(
        id=RULESET_ID,
        version=VERSION,
        framework_id=CASA.id,
        display_name="CASA CAO 48.1 Appendix 2 screening ruleset v1",
        effective_date=EFFECTIVE,
        rules=rules,
        assumptions=COMMON_ASSUMPTIONS,
        limitations=COMMON_LIMITATIONS,
    )


def register() -> None:
    register_ruleset(build_ruleset())
