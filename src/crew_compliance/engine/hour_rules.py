from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Iterable

from crew_compliance.domain.enums import FindingKind
from crew_compliance.domain.models import DutyPeriod, Finding, Roster, RuleMetadata
from crew_compliance.engine.findings import build_finding
from crew_compliance.engine.opening_support import apply_opening_hours, missing_opening_finding
from crew_compliance.engine.protocol import EvaluationContext, Rule
from crew_compliance.engine.severity import hour_exceedance_severity
from crew_compliance.engine.windows import overlap_hours


def _crew_name(roster: Roster, crew_id: str) -> str:
    for member in roster.crew:
        if member.crew_id == crew_id:
            return member.name
    return crew_id


def _flight_events(duties: Iterable[DutyPeriod]) -> list[tuple[DutyPeriod, date, datetime, float]]:
    events = []
    for duty in duties:
        hours = duty.operating_flight_hours()
        if hours is None:
            continue
        events.append((duty, duty.duty_date, duty.event_time(), hours))
    return events


def _duty_intervals(duties: Iterable[DutyPeriod]) -> list[DutyPeriod]:
    return [d for d in duties if d.duty_start and d.duty_end and d.duty_end > d.duty_start]


class CalendarDayHoursRule:
    """Sum a metric over any N consecutive calendar days."""

    def __init__(self, metadata: RuleMetadata, metric: str) -> None:
        self.metadata = metadata
        self.metric = metric  # flight_time | duty_hours

    def required_inputs(self) -> frozenset[str]:
        if self.metric == "flight_time":
            return self.metadata.required_inputs or frozenset({"crew_id", "duty_date", "flight_hours"})
        return self.metadata.required_inputs or frozenset({"crew_id", "duty_date", "duty_hours"})

    def evaluate(self, roster: Roster, ctx: EvaluationContext) -> list[Finding]:
        window_days = int(self.metadata.parameters["window_days"])
        limit = float(self.metadata.parameters["limit_hours"])
        opening_window = str(self.metadata.parameters.get("opening_window") or "")
        opening_metric = self.metadata.parameters.get("opening_metric") or self.metric
        findings: list[Finding] = []
        by_crew: dict[str, list[DutyPeriod]] = defaultdict(list)
        for duty in roster.duties:
            by_crew[duty.crew_id].append(duty)

        for crew_id, duties in by_crew.items():
            name = _crew_name(roster, crew_id)
            points: list[tuple[DutyPeriod, date, float]] = []
            missing = False
            for duty in duties:
                if self.metric == "flight_time":
                    hours = duty.operating_flight_hours()
                    if hours is None and not duty.is_positioning:
                        missing = True
                        continue
                    points.append((duty, duty.duty_date, hours or 0.0))
                else:
                    hours = duty.computed_duty_hours()
                    if hours is None:
                        missing = True
                        continue
                    points.append((duty, duty.duty_date, hours))

            if missing and not points:
                findings.append(
                    build_finding(
                        self.metadata,
                        kind=FindingKind.INSUFFICIENT_DATA,
                        crew_id=crew_id,
                        crew_name=name,
                        severity=hour_exceedance_severity(0, limit),
                        explanation=(
                            "This rule could not be evaluated because required hour values "
                            "are missing for this crew member."
                        ),
                        extra_limitations=("Required input data was not present on the roster.",),
                    )
                )
                continue
            if not points:
                continue
            if ctx.opening_balances is not None and opening_window:
                if ctx.opening_balances.get(crew_id, opening_window, opening_metric) is None:
                    findings.append(
                        missing_opening_finding(
                            self.metadata,
                            crew_id=crew_id,
                            crew_name=name,
                            window_type=opening_window,
                            limit=limit,
                        )
                    )
                    continue

            min_date = min(p[1] for p in points)
            worst: tuple[float, date, date, DutyPeriod, dict] | None = None
            incomplete_under = False
            for _, end_date, _ in points:
                start_date = end_date - timedelta(days=window_days - 1)
                in_period = sum(h for _, d, h in points if start_date <= d <= end_date)
                incomplete = min_date > start_date
                total, still_incomplete, opening_ev = apply_opening_hours(
                    in_period, incomplete, ctx, crew_id, opening_window, opening_metric
                )
                if total is None:
                    continue
                if total > limit:
                    anchor = next(p[0] for p in points if p[1] == end_date)
                    if worst is None or total > worst[0]:
                        worst = (total, start_date, end_date, anchor, opening_ev)
                elif still_incomplete:
                    incomplete_under = True

            if worst:
                total, start_date, end_date, anchor, opening_ev = worst
                findings.append(
                    build_finding(
                        self.metadata,
                        kind=FindingKind.POTENTIAL_ISSUE,
                        crew_id=crew_id,
                        crew_name=name,
                        severity=hour_exceedance_severity(total, limit),
                        actual=round(total, 2),
                        required=limit,
                        event_time=anchor.event_time(),
                        duty_id=anchor.duty_id,
                        flight_id=anchor.flight_id,
                        evidence={
                            "window_start": start_date.isoformat(),
                            "window_end": end_date.isoformat(),
                            "window_days": window_days,
                            "metric": self.metric,
                            "lookback_incomplete": min_date > start_date,
                            **opening_ev,
                        },
                        explanation=(
                            f"{name} accrued {total:.1f} {self.metric.replace('_', ' ')} hours "
                            f"in the {window_days}-day window ending {end_date.isoformat()}, "
                            f"which exceeds the {limit:.0f}-hour limit. This is a potential "
                            "compliance issue and requires review."
                        ),
                        extra_limitations=(
                            ("Roster lookback does not fully cover this window.",)
                            if min_date > start_date and opening_ev.get("opening_balance_status") == "not_provided"
                            else ()
                        ),
                    )
                )
            elif incomplete_under:
                findings.append(
                    build_finding(
                        self.metadata,
                        kind=FindingKind.INSUFFICIENT_DATA,
                        crew_id=crew_id,
                        crew_name=name,
                        severity=hour_exceedance_severity(0, limit),
                        required=limit,
                        evidence={"opening_balance_status": "not_provided"} if ctx.opening_balances is None else {},
                        explanation=(
                            f"The roster does not cover a full {window_days} consecutive "
                            f"calendar days for {name}. A value at or below {limit:.0f} hours "
                            "cannot be treated as compliant."
                        ),
                    )
                )
        return findings


class CalendarYearFlightRule:
    def __init__(self, metadata: RuleMetadata) -> None:
        self.metadata = metadata

    def required_inputs(self) -> frozenset[str]:
        return frozenset({"crew_id", "duty_date", "flight_hours"})

    def evaluate(self, roster: Roster, ctx: EvaluationContext) -> list[Finding]:
        limit = float(self.metadata.parameters["limit_hours"])
        opening_window = str(self.metadata.parameters.get("opening_window") or "annual")
        opening_metric = self.metadata.parameters.get("opening_metric") or "flight_time"
        findings: list[Finding] = []
        by_crew: dict[str, list[DutyPeriod]] = defaultdict(list)
        for duty in roster.duties:
            by_crew[duty.crew_id].append(duty)

        for crew_id, duties in by_crew.items():
            name = _crew_name(roster, crew_id)
            events = _flight_events(duties)
            if not events:
                findings.append(
                    build_finding(
                        self.metadata,
                        kind=FindingKind.INSUFFICIENT_DATA,
                        crew_id=crew_id,
                        crew_name=name,
                        severity=hour_exceedance_severity(0, limit),
                        explanation="Operating flight hours are missing, so calendar-year flight time cannot be evaluated.",
                    )
                )
                continue
            if ctx.opening_balances is not None:
                if ctx.opening_balances.get(crew_id, opening_window, opening_metric) is None:
                    findings.append(
                        missing_opening_finding(
                            self.metadata,
                            crew_id=crew_id,
                            crew_name=name,
                            window_type=opening_window,
                            limit=limit,
                        )
                    )
                    continue
            years = {event[1].year for event in events}
            for year in sorted(years):
                year_events = [e for e in events if e[1].year == year]
                in_period = sum(e[3] for e in year_events)
                min_date = min(e[1] for e in year_events)
                max_date = max(e[1] for e in year_events)
                full_year = min_date <= date(year, 1, 1) and max_date >= date(year, 12, 31)
                incomplete = not full_year
                total, still_incomplete, opening_ev = apply_opening_hours(
                    in_period, incomplete, ctx, crew_id, opening_window, opening_metric
                )
                if total is None:
                    continue
                anchor = year_events[-1][0]
                if total > limit:
                    findings.append(
                        build_finding(
                            self.metadata,
                            kind=FindingKind.POTENTIAL_ISSUE,
                            crew_id=crew_id,
                            crew_name=name,
                            severity=hour_exceedance_severity(total, limit),
                            actual=round(total, 2),
                            required=limit,
                            event_time=anchor.event_time(),
                            duty_id=anchor.duty_id,
                            evidence={"year": year, "full_year_covered": full_year, **opening_ev},
                            explanation=(
                                f"{name} accrued {total:.1f} operating flight hours in calendar "
                                f"year {year}, which exceeds {limit:.0f} hours. This is a "
                                "potential compliance issue and requires review."
                            ),
                        )
                    )
                elif still_incomplete:
                    findings.append(
                        build_finding(
                            self.metadata,
                            kind=FindingKind.INSUFFICIENT_DATA,
                            crew_id=crew_id,
                            crew_name=name,
                            severity=hour_exceedance_severity(0, limit),
                            actual=round(in_period, 2),
                            required=limit,
                            event_time=anchor.event_time(),
                            evidence={"year": year, "full_year_covered": False, **opening_ev},
                            explanation=(
                                f"The roster does not cover all of calendar year {year} for {name}. "
                                f"Observed operating flight time is {in_period:.1f} hours, which is "
                                f"at or below {limit:.0f}, but the year cannot be conclusively evaluated."
                            ),
                        )
                    )
        return findings


class CalendarMonthsFlightRule:
    def __init__(self, metadata: RuleMetadata) -> None:
        self.metadata = metadata

    def required_inputs(self) -> frozenset[str]:
        return frozenset({"crew_id", "duty_date", "flight_hours"})

    def evaluate(self, roster: Roster, ctx: EvaluationContext) -> list[Finding]:
        limit = float(self.metadata.parameters["limit_hours"])
        months = int(self.metadata.parameters["window_months"])
        opening_window = str(self.metadata.parameters.get("opening_window") or "12month")
        opening_metric = self.metadata.parameters.get("opening_metric") or "flight_time"
        findings: list[Finding] = []
        by_crew: dict[str, list[DutyPeriod]] = defaultdict(list)
        for duty in roster.duties:
            by_crew[duty.crew_id].append(duty)

        for crew_id, duties in by_crew.items():
            name = _crew_name(roster, crew_id)
            events = _flight_events(duties)
            if not events:
                findings.append(
                    build_finding(
                        self.metadata,
                        kind=FindingKind.INSUFFICIENT_DATA,
                        crew_id=crew_id,
                        crew_name=name,
                        severity=hour_exceedance_severity(0, limit),
                        explanation="Operating flight hours are missing, so 12-month flight time cannot be evaluated.",
                    )
                )
                continue
            if ctx.opening_balances is not None:
                if ctx.opening_balances.get(crew_id, opening_window, opening_metric) is None:
                    findings.append(
                        missing_opening_finding(
                            self.metadata,
                            crew_id=crew_id,
                            crew_name=name,
                            window_type=opening_window,
                            limit=limit,
                        )
                    )
                    continue
            min_date = min(e[1] for e in events)
            month_ends = {(e[1].year, e[1].month) for e in events}
            worst = None
            incomplete_under = False
            for year, month in month_ends:
                start_year = year
                start_month = month - months + 1
                while start_month <= 0:
                    start_month += 12
                    start_year -= 1
                window_start = date(start_year, start_month, 1)
                if month == 12:
                    window_end = date(year + 1, 1, 1) - timedelta(days=1)
                else:
                    window_end = date(year, month + 1, 1) - timedelta(days=1)
                in_period = sum(e[3] for e in events if window_start <= e[1] <= window_end)
                incomplete = min_date > window_start
                total, still_incomplete, opening_ev = apply_opening_hours(
                    in_period, incomplete, ctx, crew_id, opening_window, opening_metric
                )
                if total is None:
                    continue
                if total > limit:
                    anchor = next(e[0] for e in events if e[1].year == year and e[1].month == month)
                    if worst is None or total > worst[0]:
                        worst = (total, window_start, window_end, anchor, incomplete, opening_ev)
                elif still_incomplete:
                    incomplete_under = True
            if worst:
                total, window_start, window_end, anchor, incomplete, opening_ev = worst
                findings.append(
                    build_finding(
                        self.metadata,
                        kind=FindingKind.POTENTIAL_ISSUE,
                        crew_id=crew_id,
                        crew_name=name,
                        severity=hour_exceedance_severity(total, limit),
                        actual=round(total, 2),
                        required=limit,
                        event_time=anchor.event_time(),
                        duty_id=anchor.duty_id,
                        evidence={
                            "window_start": window_start.isoformat(),
                            "window_end": window_end.isoformat(),
                            "lookback_incomplete": incomplete,
                            **opening_ev,
                        },
                        explanation=(
                            f"{name} accrued {total:.1f} operating flight hours in the "
                            f"{months} calendar months ending {window_end.isoformat()}, "
                            f"which exceeds {limit:.0f} hours. This is a potential "
                            "compliance issue and requires review."
                        ),
                    )
                )
            elif incomplete_under:
                findings.append(
                    build_finding(
                        self.metadata,
                        kind=FindingKind.INSUFFICIENT_DATA,
                        crew_id=crew_id,
                        crew_name=name,
                        severity=hour_exceedance_severity(0, limit),
                        required=limit,
                        explanation=(
                            f"The roster does not cover a full {months} consecutive calendar "
                            f"months for {name}. The {limit:.0f}-hour limit cannot be conclusively evaluated."
                        ),
                    )
                )
        return findings


class RollingHoursOverlapRule:
    """Sum overlapping duty or FDP-proxy hours in a consecutive-hour window."""

    def __init__(self, metadata: RuleMetadata) -> None:
        self.metadata = metadata

    def required_inputs(self) -> frozenset[str]:
        return frozenset({"crew_id", "duty_start", "duty_end"})

    def evaluate(self, roster: Roster, ctx: EvaluationContext) -> list[Finding]:
        window_hours = float(self.metadata.parameters["window_hours"])
        limit = float(self.metadata.parameters["limit_hours"])
        opening_window = str(self.metadata.parameters.get("opening_window") or "")
        opening_metric = self.metadata.parameters.get("opening_metric")
        findings: list[Finding] = []
        by_crew: dict[str, list[DutyPeriod]] = defaultdict(list)
        for duty in roster.duties:
            by_crew[duty.crew_id].append(duty)

        for crew_id, duties in by_crew.items():
            name = _crew_name(roster, crew_id)
            intervals = _duty_intervals(duties)
            if not intervals:
                findings.append(
                    build_finding(
                        self.metadata,
                        kind=FindingKind.INSUFFICIENT_DATA,
                        crew_id=crew_id,
                        crew_name=name,
                        severity=hour_exceedance_severity(0, limit),
                        explanation="Duty start and end times are required to evaluate this consecutive-hour limitation.",
                    )
                )
                continue
            if ctx.opening_balances is not None and opening_window:
                if ctx.opening_balances.get(crew_id, opening_window, opening_metric) is None:
                    findings.append(
                        missing_opening_finding(
                            self.metadata,
                            crew_id=crew_id,
                            crew_name=name,
                            window_type=opening_window,
                            limit=limit,
                        )
                    )
                    continue
            min_start = min(d.duty_start for d in intervals if d.duty_start)
            worst = None
            incomplete_under = False
            for anchor in intervals:
                assert anchor.duty_end and anchor.duty_start
                window_end = anchor.duty_end
                window_start = window_end - timedelta(hours=window_hours)
                in_period = sum(
                    overlap_hours(d.duty_start, d.duty_end, window_start, window_end)  # type: ignore[arg-type]
                    for d in intervals
                    if d.duty_start and d.duty_end
                )
                incomplete = min_start > window_start
                total, still_incomplete, opening_ev = apply_opening_hours(
                    in_period, incomplete, ctx, crew_id, opening_window, opening_metric
                )
                if total is None:
                    continue
                if total > limit:
                    if worst is None or total > worst[0]:
                        worst = (total, window_start, window_end, anchor, incomplete, opening_ev)
                elif still_incomplete:
                    incomplete_under = True
            if worst:
                total, window_start, window_end, anchor, incomplete, opening_ev = worst
                findings.append(
                    build_finding(
                        self.metadata,
                        kind=FindingKind.POTENTIAL_ISSUE,
                        crew_id=crew_id,
                        crew_name=name,
                        severity=hour_exceedance_severity(total, limit),
                        actual=round(total, 2),
                        required=limit,
                        event_time=anchor.event_time(),
                        duty_id=anchor.duty_id,
                        evidence={
                            "window_start": window_start.isoformat(),
                            "window_end": window_end.isoformat(),
                            "window_hours": window_hours,
                            "lookback_incomplete": incomplete,
                            "metric": self.metadata.parameters.get("metric", "duty_or_fdp_proxy"),
                            **opening_ev,
                        },
                        explanation=(
                            f"{name} accrued {total:.1f} hours in the {window_hours:.0f}-hour "
                            f"window ending {window_end.isoformat()}, exceeding {limit:.0f} hours. "
                            "This is a potential compliance issue and requires review."
                        ),
                        extra_limitations=(
                            ("Duty span used as an FDP proxy where true FDP was not provided.",)
                            if self.metadata.parameters.get("metric") == "fdp_proxy"
                            else ()
                        ),
                    )
                )
            elif incomplete_under:
                findings.append(
                    build_finding(
                        self.metadata,
                        kind=FindingKind.INSUFFICIENT_DATA,
                        crew_id=crew_id,
                        crew_name=name,
                        severity=hour_exceedance_severity(0, limit),
                        required=limit,
                        explanation=(
                            f"The roster does not cover a full {window_hours:.0f} consecutive "
                            f"hours before one or more duties for {name}. The limit cannot be conclusively evaluated."
                        ),
                    )
                )
        return findings


class RollingFlightHoursRule:
    def __init__(self, metadata: RuleMetadata) -> None:
        self.metadata = metadata

    def required_inputs(self) -> frozenset[str]:
        return frozenset({"crew_id", "flight_hours"})

    def evaluate(self, roster: Roster, ctx: EvaluationContext) -> list[Finding]:
        window_hours = float(self.metadata.parameters["window_hours"])
        limit = float(self.metadata.parameters["limit_hours"])
        window_days = int(self.metadata.parameters.get("window_days", 0))
        opening_window = str(self.metadata.parameters.get("opening_window") or "")
        opening_metric = self.metadata.parameters.get("opening_metric") or "flight_time"
        findings: list[Finding] = []
        by_crew: dict[str, list[DutyPeriod]] = defaultdict(list)
        for duty in roster.duties:
            by_crew[duty.crew_id].append(duty)

        for crew_id, duties in by_crew.items():
            name = _crew_name(roster, crew_id)
            events = _flight_events(duties)
            if not events:
                findings.append(
                    build_finding(
                        self.metadata,
                        kind=FindingKind.INSUFFICIENT_DATA,
                        crew_id=crew_id,
                        crew_name=name,
                        severity=hour_exceedance_severity(0, limit),
                        explanation="Operating flight hours are required to evaluate this rolling flight-time limit.",
                    )
                )
                continue
            if ctx.opening_balances is not None and opening_window:
                if ctx.opening_balances.get(crew_id, opening_window, opening_metric) is None:
                    findings.append(
                        missing_opening_finding(
                            self.metadata,
                            crew_id=crew_id,
                            crew_name=name,
                            window_type=opening_window,
                            limit=limit,
                        )
                    )
                    continue
            min_time = min(e[2] for e in events)
            worst = None
            incomplete_under = False
            for duty, day, event_time, _hours in events:
                if window_days:
                    start_date = day - timedelta(days=window_days - 1)
                    in_period = sum(h for _, d, _, h in events if start_date <= d <= day)
                    window_start = datetime.combine(start_date, datetime.min.time())
                    incomplete = min(e[1] for e in events) > start_date
                else:
                    window_start = event_time - timedelta(hours=window_hours)
                    in_period = sum(h for _, _, t, h in events if window_start < t <= event_time)
                    incomplete = min_time > window_start
                total, still_incomplete, opening_ev = apply_opening_hours(
                    in_period, incomplete, ctx, crew_id, opening_window, opening_metric
                )
                if total is None:
                    continue
                if total > limit:
                    if worst is None or total > worst[0]:
                        worst = (total, window_start, event_time, duty, incomplete, opening_ev)
                elif still_incomplete:
                    incomplete_under = True
            if worst:
                total, window_start, event_time, duty, incomplete, opening_ev = worst
                findings.append(
                    build_finding(
                        self.metadata,
                        kind=FindingKind.POTENTIAL_ISSUE,
                        crew_id=crew_id,
                        crew_name=name,
                        severity=hour_exceedance_severity(total, limit),
                        actual=round(total, 2),
                        required=limit,
                        event_time=event_time,
                        duty_id=duty.duty_id,
                        flight_id=duty.flight_id,
                        evidence={
                            "window_start": window_start.isoformat(),
                            "window_end": event_time.isoformat(),
                            "lookback_incomplete": incomplete,
                            **opening_ev,
                        },
                        explanation=(
                            f"{name} accrued {total:.1f} operating flight hours in the evaluated "
                            f"window ending {event_time.isoformat()}, exceeding {limit:.0f} hours. "
                            "This is a potential compliance issue and requires review."
                        ),
                    )
                )
            elif incomplete_under:
                findings.append(
                    build_finding(
                        self.metadata,
                        kind=FindingKind.INSUFFICIENT_DATA,
                        crew_id=crew_id,
                        crew_name=name,
                        severity=hour_exceedance_severity(0, limit),
                        required=limit,
                        explanation=(
                            f"The roster lookback for {name} is incomplete for this rolling "
                            "flight-time limit, so a result at or below the limit is not conclusive."
                        ),
                    )
                )
        return findings


# Satisfy Rule protocol for type checkers
_RULE_TYPES: tuple[type[Rule], ...] = (
    CalendarDayHoursRule,
    CalendarYearFlightRule,
    CalendarMonthsFlightRule,
    RollingHoursOverlapRule,
    RollingFlightHoursRule,
)