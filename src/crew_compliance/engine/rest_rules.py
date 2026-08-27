from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from crew_compliance.domain.enums import FindingKind
from crew_compliance.domain.models import DutyPeriod, Finding, Roster, RuleMetadata
from crew_compliance.engine.findings import build_finding
from crew_compliance.engine.protocol import EvaluationContext
from crew_compliance.engine.severity import rest_shortfall_severity
from crew_compliance.engine.windows import longest_free_hours


def _crew_name(roster: Roster, crew_id: str) -> str:
    for member in roster.crew:
        if member.crew_id == crew_id:
            return member.name
    return crew_id


def _sorted_timed_duties(duties: list[DutyPeriod]) -> list[DutyPeriod]:
    timed = [d for d in duties if d.duty_start and d.duty_end and d.duty_end > d.duty_start]
    return sorted(timed, key=lambda d: d.duty_start or d.event_time())


class MinRestBeforeDutyRule:
    """Rest before a duty must be at least max(preceding duty, floor)."""

    def __init__(self, metadata: RuleMetadata) -> None:
        self.metadata = metadata

    def required_inputs(self) -> frozenset[str]:
        return frozenset({"crew_id", "duty_start", "duty_end"})

    def evaluate(self, roster: Roster, ctx: EvaluationContext) -> list[Finding]:
        del ctx
        home_floor = float(self.metadata.parameters.get("home_base_floor_hours", 0))
        away_floor = float(self.metadata.parameters.get("away_floor_hours", 0))
        fixed_floor = self.metadata.parameters.get("fixed_floor_hours")
        findings: list[Finding] = []
        by_crew: dict[str, list[DutyPeriod]] = defaultdict(list)
        for duty in roster.duties:
            by_crew[duty.crew_id].append(duty)

        for crew_id, duties in by_crew.items():
            name = _crew_name(roster, crew_id)
            timed = _sorted_timed_duties(duties)
            if not timed:
                findings.append(
                    build_finding(
                        self.metadata,
                        kind=FindingKind.INSUFFICIENT_DATA,
                        crew_id=crew_id,
                        crew_name=name,
                        severity=rest_shortfall_severity(0, 1),
                        explanation="Duty start and end times are required to evaluate rest.",
                    )
                )
                continue
            findings.append(
                build_finding(
                    self.metadata,
                    kind=FindingKind.INSUFFICIENT_DATA,
                    crew_id=crew_id,
                    crew_name=name,
                    severity=rest_shortfall_severity(0, 1),
                    duty_id=timed[0].duty_id,
                    event_time=timed[0].duty_start,
                    explanation=(
                        f"The roster does not include a prior duty for {name} before "
                        f"{timed[0].duty_start.isoformat() if timed[0].duty_start else 'the first duty'}. "
                        "Minimum rest before that duty cannot be conclusively evaluated."
                    ),
                )
            )
            for previous, current in zip(timed, timed[1:]):
                assert previous.duty_end and current.duty_start
                rest_hours = (current.duty_start - previous.duty_end).total_seconds() / 3600.0
                preceding = previous.computed_duty_hours() or 0.0
                use_preceding = bool(self.metadata.parameters.get("use_preceding", True))
                if fixed_floor is not None:
                    required = (
                        max(preceding, float(fixed_floor)) if use_preceding else float(fixed_floor)
                    )
                    home_away_unknown = False
                else:
                    at_home = current.starts_at_home_base()
                    if at_home is True:
                        floor = home_floor
                        home_away_unknown = False
                    elif at_home is False:
                        floor = away_floor
                        home_away_unknown = False
                    else:
                        floor = away_floor
                        home_away_unknown = True
                    required = max(preceding, floor)

                if use_preceding and rest_hours < preceding:
                    findings.append(
                        build_finding(
                            self.metadata,
                            kind=FindingKind.POTENTIAL_ISSUE,
                            crew_id=crew_id,
                            crew_name=name,
                            severity=rest_shortfall_severity(rest_hours, preceding),
                            actual=round(rest_hours, 2),
                            required=round(preceding, 2),
                            difference=round(rest_hours - preceding, 2),
                            duty_id=current.duty_id,
                            event_time=current.duty_start,
                            evidence={"preceding_duty_id": previous.duty_id, "reason": "shorter_than_preceding_duty"},
                            explanation=(
                                f"{name} had {rest_hours:.1f} hours rest before the duty starting "
                                f"{current.duty_start.isoformat()}, which is shorter than the preceding "
                                f"duty period of {preceding:.1f} hours. This is a potential compliance "
                                "issue and requires review."
                            ),
                        )
                    )
                    continue

                if home_away_unknown and rest_hours >= home_floor:
                    continue
                if home_away_unknown and rest_hours >= away_floor:
                    findings.append(
                        build_finding(
                            self.metadata,
                            kind=FindingKind.INSUFFICIENT_DATA,
                            crew_id=crew_id,
                            crew_name=name,
                            severity=rest_shortfall_severity(rest_hours, home_floor),
                            actual=round(rest_hours, 2),
                            required=home_floor,
                            duty_id=current.duty_id,
                            event_time=current.duty_start,
                            explanation=(
                                f"{name} had {rest_hours:.1f} hours rest, which meets the away-from-base "
                                f"floor of {away_floor:.0f} hours but is below the home-base floor of "
                                f"{home_floor:.0f} hours. Home/away cannot be determined from the roster."
                            ),
                        )
                    )
                    continue

                if rest_hours < required:
                    findings.append(
                        build_finding(
                            self.metadata,
                            kind=FindingKind.POTENTIAL_ISSUE,
                            crew_id=crew_id,
                            crew_name=name,
                            severity=rest_shortfall_severity(rest_hours, required),
                            actual=round(rest_hours, 2),
                            required=round(required, 2),
                            difference=round(rest_hours - required, 2),
                            duty_id=current.duty_id,
                            event_time=current.duty_start,
                            evidence={"preceding_duty_id": previous.duty_id, "required_formula": "max(preceding_duty, floor)"},
                            explanation=(
                                f"{name} had {rest_hours:.1f} hours rest before the duty starting "
                                f"{current.duty_start.isoformat()}; at least {required:.1f} hours were "
                                "required. This is a potential compliance issue and requires review."
                            ),
                        )
                    )
        return findings


class LookbackConsecutiveRestRule:
    """Require N consecutive hours free of duty in the H hours before duty start."""

    def __init__(self, metadata: RuleMetadata) -> None:
        self.metadata = metadata

    def required_inputs(self) -> frozenset[str]:
        return frozenset({"crew_id", "duty_start", "duty_end"})

    def evaluate(self, roster: Roster, ctx: EvaluationContext) -> list[Finding]:
        del ctx
        lookback_hours = float(self.metadata.parameters["lookback_hours"])
        required_rest = float(self.metadata.parameters["required_consecutive_rest_hours"])
        findings: list[Finding] = []
        by_crew: dict[str, list[DutyPeriod]] = defaultdict(list)
        for duty in roster.duties:
            by_crew[duty.crew_id].append(duty)

        for crew_id, duties in by_crew.items():
            name = _crew_name(roster, crew_id)
            timed = _sorted_timed_duties(duties)
            if not timed:
                findings.append(
                    build_finding(
                        self.metadata,
                        kind=FindingKind.INSUFFICIENT_DATA,
                        crew_id=crew_id,
                        crew_name=name,
                        severity=rest_shortfall_severity(0, required_rest),
                        explanation="Duty start and end times are required to evaluate lookback rest.",
                    )
                )
                continue
            intervals = [(d.duty_start, d.duty_end) for d in timed if d.duty_start and d.duty_end]
            min_start = min(d.duty_start for d in timed if d.duty_start)
            for duty in timed:
                assert duty.duty_start
                window_end = duty.duty_start
                window_start = window_end - timedelta(hours=lookback_hours)
                free = longest_free_hours(intervals, window_start, window_end)  # type: ignore[arg-type]
                incomplete = min_start > window_start
                if free + 1e-9 >= required_rest:
                    continue
                if incomplete:
                    findings.append(
                        build_finding(
                            self.metadata,
                            kind=FindingKind.INSUFFICIENT_DATA,
                            crew_id=crew_id,
                            crew_name=name,
                            severity=rest_shortfall_severity(free, required_rest),
                            actual=round(free, 2),
                            required=required_rest,
                            duty_id=duty.duty_id,
                            event_time=duty.duty_start,
                            explanation=(
                                f"Lookback of {lookback_hours:.0f} hours before {duty.duty_start.isoformat()} "
                                f"is incomplete for {name}. A {required_rest:.0f}-hour consecutive rest period "
                                "was not found in the available data and cannot be ruled out earlier in the lookback."
                            ),
                        )
                    )
                else:
                    findings.append(
                        build_finding(
                            self.metadata,
                            kind=FindingKind.POTENTIAL_ISSUE,
                            crew_id=crew_id,
                            crew_name=name,
                            severity=rest_shortfall_severity(free, required_rest),
                            actual=round(free, 2),
                            required=required_rest,
                            difference=round(free - required_rest, 2),
                            duty_id=duty.duty_id,
                            event_time=duty.duty_start,
                            evidence={"lookback_hours": lookback_hours, "longest_free_hours": round(free, 2)},
                            explanation=(
                                f"Before the duty starting {duty.duty_start.isoformat()}, {name} had "
                                f"{free:.1f} consecutive hours free of duty in the prior {lookback_hours:.0f} "
                                f"hours; {required_rest:.0f} consecutive hours are required. This is a "
                                "potential compliance issue and requires review."
                            ),
                        )
                    )
        return findings


class RecurrentExtendedRestScreenRule:
    """Partial screen: 36h rest periods no more than 168h apart (end to next start)."""

    def __init__(self, metadata: RuleMetadata) -> None:
        self.metadata = metadata

    def required_inputs(self) -> frozenset[str]:
        return frozenset({"crew_id", "duty_start", "duty_end"})

    def evaluate(self, roster: Roster, ctx: EvaluationContext) -> list[Finding]:
        del ctx
        rest_hours = float(self.metadata.parameters["rest_hours"])
        max_gap_hours = float(self.metadata.parameters["max_gap_hours"])
        findings: list[Finding] = []
        by_crew: dict[str, list[DutyPeriod]] = defaultdict(list)
        for duty in roster.duties:
            by_crew[duty.crew_id].append(duty)

        for crew_id, duties in by_crew.items():
            name = _crew_name(roster, crew_id)
            timed = _sorted_timed_duties(duties)
            if len(timed) < 2:
                findings.append(
                    build_finding(
                        self.metadata,
                        kind=FindingKind.INSUFFICIENT_DATA,
                        crew_id=crew_id,
                        crew_name=name,
                        severity=rest_shortfall_severity(0, rest_hours),
                        explanation=(
                            "Not enough timed duties are present to screen recurrent extended recovery rest."
                        ),
                    )
                )
                continue
            rests: list[tuple[DutyPeriod, DutyPeriod, float]] = []
            for previous, current in zip(timed, timed[1:]):
                assert previous.duty_end and current.duty_start
                gap = (current.duty_start - previous.duty_end).total_seconds() / 3600.0
                rests.append((previous, current, gap))
            rerrp = [(p, c, g) for p, c, g in rests if g + 1e-9 >= rest_hours]
            span_hours = (timed[-1].duty_end - timed[0].duty_start).total_seconds() / 3600.0  # type: ignore[operator]
            if not rerrp:
                kind = FindingKind.INSUFFICIENT_DATA if span_hours <= max_gap_hours else FindingKind.POTENTIAL_ISSUE
                findings.append(
                    build_finding(
                        self.metadata,
                        kind=kind,
                        crew_id=crew_id,
                        crew_name=name,
                        severity=rest_shortfall_severity(0, rest_hours),
                        actual=0.0,
                        required=rest_hours,
                        explanation=(
                            f"No rest period of at least {rest_hours:.0f} hours was found for {name}. "
                            + (
                                "The roster span is too short to conclude that recurrent extended rest is missing."
                                if kind == FindingKind.INSUFFICIENT_DATA
                                else "The interval between such rests cannot exceed 168 hours. This is a potential "
                                "compliance issue (partial screen; local-night criteria are not evaluated) and requires review."
                            )
                        ),
                    )
                )
                continue
            for (p1, c1, _g1), (p2, c2, _g2) in zip(rerrp, rerrp[1:]):
                assert c1.duty_start and p2.duty_end
                between = (c2.duty_start - p1.duty_end).total_seconds() / 3600.0
                # time from end of first RERRP (c1.duty_start is start of next duty after rest)
                # End of RERRP is current.duty_start of the rest tuple... actually rest is
                # previous.duty_end -> current.duty_start. End of RERRP is current.duty_start.
                # Start of next RERRP is p2.duty_end.
                rerrp_end = c1.duty_start
                next_start = p2.duty_end
                gap = (next_start - rerrp_end).total_seconds() / 3600.0
                if gap > max_gap_hours:
                    findings.append(
                        build_finding(
                            self.metadata,
                            kind=FindingKind.POTENTIAL_ISSUE,
                            crew_id=crew_id,
                            crew_name=name,
                            severity=rest_shortfall_severity(max_gap_hours - (gap - max_gap_hours), max_gap_hours),
                            actual=round(gap, 2),
                            required=max_gap_hours,
                            duty_id=c2.duty_id,
                            event_time=c2.duty_start,
                            evidence={"rerrp_end": rerrp_end.isoformat(), "next_rerrp_start": next_start.isoformat()},
                            explanation=(
                                f"For {name}, {gap:.1f} hours elapsed between the end of one "
                                f"{rest_hours:.0f}-hour rest period and the start of the next, "
                                f"which exceeds {max_gap_hours:.0f} hours. This is a potential "
                                "compliance issue from a partial screen (2 local nights are not evaluated)."
                            ),
                        )
                    )
            last_rerrp_end = rerrp[-1][1].duty_start
            roster_end = timed[-1].duty_end
            if last_rerrp_end and roster_end:
                tail = (roster_end - last_rerrp_end).total_seconds() / 3600.0
                if tail > max_gap_hours:
                    findings.append(
                        build_finding(
                            self.metadata,
                            kind=FindingKind.POTENTIAL_ISSUE,
                            crew_id=crew_id,
                            crew_name=name,
                            severity=rest_shortfall_severity(0, rest_hours),
                            actual=round(tail, 2),
                            required=max_gap_hours,
                            event_time=roster_end,
                            explanation=(
                                f"More than {max_gap_hours:.0f} hours of rostered duty elapsed after the last "
                                f"{rest_hours:.0f}-hour rest identified for {name}, with no subsequent "
                                "extended rest in the file. This is a potential compliance issue from a "
                                "partial screen and requires review."
                            ),
                        )
                    )
        return findings