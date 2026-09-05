from __future__ import annotations

from collections import defaultdict

from crew_compliance.domain.enums import FindingKind
from crew_compliance.domain.models import DutyPeriod, Finding, Roster, RuleMetadata
from crew_compliance.engine.fdp_tables import (
    lookup_casa_app2_table21,
    lookup_easa_table2,
    lookup_easa_table3,
    lookup_faa_table_b,
    lookup_tc_700_28,
)
from crew_compliance.engine.findings import build_finding
from crew_compliance.engine.protocol import EvaluationContext
from crew_compliance.engine.severity import hour_exceedance_severity


def _crew_name(roster: Roster, crew_id: str) -> str:
    for member in roster.crew:
        if member.crew_id == crew_id:
            return member.name
    return crew_id


def _acclimatisation(duties: list[DutyPeriod]) -> str:
    for duty in duties:
        if duty.acclimatisation:
            return duty.acclimatisation
    return "acclimatised"


def _group_fdps(duties: list[DutyPeriod]) -> tuple[dict[tuple[str, object], list[DutyPeriod]], list[DutyPeriod]]:
    groups: dict[tuple[str, object], list[DutyPeriod]] = defaultdict(list)
    untimed: list[DutyPeriod] = []
    for duty in duties:
        if not duty.duty_start or not duty.duty_end:
            untimed.append(duty)
            continue
        start = duty.duty_start.replace(second=0, microsecond=0)
        groups[(duty.crew_id, start)].append(duty)
    return groups, untimed


def _sector_count(members: list[DutyPeriod]) -> int:
    explicit = [d.sector_count for d in members if d.sector_count]
    if explicit:
        return max(explicit)
    operating = [d for d in members if not d.is_positioning]
    return max(len(operating), 1) if operating else 0


def _fdp_hours(members: list[DutyPeriod]) -> float | None:
    explicit = [d.fdp_hours for d in members if d.fdp_hours is not None]
    if explicit:
        return max(explicit)
    starts = [d.duty_start for d in members if d.duty_start]
    ends = [d.duty_end for d in members if d.duty_end]
    if not starts or not ends:
        return None
    return (max(ends) - min(starts)).total_seconds() / 3600.0


def _avg_flight_hours(members: list[DutyPeriod], sectors: int) -> float | None:
    operating = [d for d in members if not d.is_positioning]
    hours = [d.operating_flight_hours() for d in operating]
    if any(h is None for h in hours) or not hours or sectors < 1:
        return None
    return sum(h or 0.0 for h in hours) / sectors


class DailyFdpTableRule:
    def __init__(self, metadata: RuleMetadata) -> None:
        self.metadata = metadata

    def required_inputs(self) -> frozenset[str]:
        return frozenset({"crew_id", "duty_start", "duty_end"})

    def evaluate(self, roster: Roster, ctx: EvaluationContext) -> list[Finding]:
        table = str(ctx.parameters(self.metadata).get("table") or "")
        findings: list[Finding] = []
        by_crew: dict[str, list[DutyPeriod]] = defaultdict(list)
        for duty in roster.duties:
            by_crew[duty.crew_id].append(duty)

        for crew_id, duties in by_crew.items():
            name = _crew_name(roster, crew_id)
            groups, untimed = _group_fdps(duties)
            if untimed and not groups:
                findings.append(
                    build_finding(
                        self.metadata,
                        kind=FindingKind.INSUFFICIENT_DATA,
                        crew_id=crew_id,
                        crew_name=name,
                        severity=hour_exceedance_severity(0, 1),
                        explanation=(
                            f"Duty start and end times are required to evaluate the daily FDP table for {name}."
                        ),
                    )
                )
                continue
            for _key, members in groups.items():
                findings.extend(self._evaluate_group(table, name, members))
        return findings

    def _evaluate_group(
        self,
        table: str,
        name: str,
        members: list[DutyPeriod],
    ) -> list[Finding]:
        members = sorted(members, key=lambda d: d.duty_start or d.event_time())
        anchor = members[0]
        crew_id = anchor.crew_id
        fdp = _fdp_hours(members)
        sectors = _sector_count(members)
        used_proxy = all(d.fdp_hours is None for d in members)
        if fdp is None:
            return [
                build_finding(
                    self.metadata,
                    kind=FindingKind.INSUFFICIENT_DATA,
                    crew_id=crew_id,
                    crew_name=name,
                    severity=hour_exceedance_severity(0, 1),
                    duty_id=anchor.duty_id,
                    event_time=anchor.duty_start,
                    explanation=f"FDP length cannot be determined for {name} on this duty.",
                )
            ]
        if sectors < 1:
            return [
                build_finding(
                    self.metadata,
                    kind=FindingKind.INSUFFICIENT_DATA,
                    crew_id=crew_id,
                    crew_name=name,
                    severity=hour_exceedance_severity(0, 1),
                    duty_id=anchor.duty_id,
                    event_time=anchor.duty_start,
                    explanation=(
                        f"Sector count is missing for {name} on this duty, and no operating flights "
                        "are present, so the FDP table cell cannot be selected."
                    ),
                )
            ]
        state = _acclimatisation(members)
        try:
            limit, cell_citation = self._limit(table, members, sectors, state)
        except ValueError as exc:
            return [
                build_finding(
                    self.metadata,
                    kind=FindingKind.INSUFFICIENT_DATA,
                    crew_id=crew_id,
                    crew_name=name,
                    severity=hour_exceedance_severity(0, 1),
                    duty_id=anchor.duty_id,
                    event_time=anchor.duty_start,
                    explanation=str(exc),
                    extra=anchor.duty_id,
                )
            ]
        evidence = {
            "fdp_start": anchor.duty_start.isoformat() if anchor.duty_start else None,
            "sectors": sectors,
            "fdp_hours": round(fdp, 2),
            "table_limit_hours": limit,
            "table_cell": cell_citation,
            "acclimatisation_assumed": state,
            "duty_span_used_as_fdp_proxy": used_proxy,
        }
        extra_lim = ("Duty start-to-end used as an FDP proxy because FDP was not in the file.",) if used_proxy else ()
        if fdp > limit + 1e-9:
            return [
                build_finding(
                    self.metadata,
                    kind=FindingKind.POTENTIAL_ISSUE,
                    crew_id=crew_id,
                    crew_name=name,
                    severity=hour_exceedance_severity(fdp, limit),
                    actual=round(fdp, 2),
                    required=limit,
                    event_time=anchor.event_time(),
                    duty_id=anchor.duty_id,
                    flight_id=anchor.flight_id,
                    evidence=evidence,
                    extra_limitations=extra_lim,
                    extra=anchor.duty_id,
                    explanation=(
                        f"{name} has a {fdp:.1f}-hour FDP starting {anchor.duty_start.strftime('%H:%M') if anchor.duty_start else '—'} "
                        f"with {sectors} sector(s). The table limit is {limit:.2f} hours ({cell_citation}). "
                        "This is a potential compliance issue and requires review."
                    ),
                )
            ]
        return []

    def _limit(
        self,
        table: str,
        members: list[DutyPeriod],
        sectors: int,
        state: str,
    ) -> tuple[float, str]:
        start = members[0].duty_start
        assert start is not None
        clock = start.time()
        if table == "easa_t2":
            if state == "unknown":
                return lookup_easa_table3(sectors)
            if state == "not_acclimated":
                raise ValueError(
                    "Not-acclimatised FDP is outside ORO.FTL.205 Tables 2 and 3 in this screen; "
                    "the cell is not guessed."
                )
            return lookup_easa_table2(clock, sectors)
        if table == "faa_b":
            limit, citation = lookup_faa_table_b(clock, sectors)
            if state in {"unknown", "not_acclimated"}:
                return limit - 0.5, f"{citation} minus 30 minutes (not acclimated, § 117.13(b))"
            return limit, citation
        if table == "casa_a2_t21":
            if state in {"unknown", "not_acclimated"}:
                raise ValueError(
                    "Unknown or not-acclimatised FDP uses Appendix 2 Table 3.1, which is not modeled. "
                    "Table 2.1 is not applied as a silent pass."
                )
            return lookup_casa_app2_table21(clock, sectors)
        if table == "tc_700_28":
            if state in {"unknown", "not_acclimated"}:
                raise ValueError(
                    "Acclimatization adjustments to CAR 700.28 are not modeled, so the table is not applied "
                    "when acclimatisation is unknown or not acclimated."
                )
            avg = _avg_flight_hours(members, sectors)
            if avg is None:
                raise ValueError(
                    f"Average scheduled flight duration for {members[0].crew_name} cannot be computed, "
                    "so the CAR 700.28 table (less than 30 min / 30–50 min / 50 min or more) cannot be selected."
                )
            return lookup_tc_700_28(clock, sectors, avg)
        raise ValueError(f"Unknown FDP table '{table}'.")
