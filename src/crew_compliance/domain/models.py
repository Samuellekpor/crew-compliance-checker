from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from crew_compliance.domain.enums import DutyKind, FindingKind, Position, Severity


@dataclass(frozen=True)
class Source:
    title: str
    locator: str
    url: str | None = None
    retrieved: str | None = None


@dataclass(frozen=True)
class RegulatoryFramework:
    id: str
    display_name: str
    jurisdiction: str
    applicability: str
    sources: tuple[Source, ...]
    default_ruleset_id: str
    icao_enforceable: bool = False


@dataclass(frozen=True)
class RuleMetadata:
    rule_id: str
    name: str
    framework_id: str
    ruleset_id: str
    ruleset_version: str
    rule_version: str
    effective_date: date
    citation: str
    description: str
    parameters: dict[str, Any]
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]
    exceptions_not_modeled: tuple[str, ...]
    evaluation_mode: str = "full"
    required_inputs: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class CrewMember:
    crew_id: str
    name: str
    position: Position = Position.UNKNOWN
    home_base: str | None = None


@dataclass(frozen=True)
class Flight:
    flight_id: str | None
    flight_start: datetime | None
    flight_end: datetime | None
    flight_hours: float | None
    is_operating: bool


@dataclass(frozen=True)
class DutyPeriod:
    duty_id: str
    crew_id: str
    crew_name: str
    position: Position
    home_base: str | None
    duty_date: date
    duty_start: datetime | None
    duty_end: datetime | None
    duty_hours: float | None
    is_positioning: bool
    duty_kind: DutyKind
    start_location: str | None
    end_location: str | None
    flight_id: str | None
    flight_start: datetime | None
    flight_end: datetime | None
    flight_hours: float | None
    source_row: int

    def operating_flight_hours(self) -> float | None:
        if self.is_positioning:
            return 0.0
        if self.flight_hours is not None:
            return self.flight_hours
        if self.flight_start and self.flight_end and self.flight_end > self.flight_start:
            return (self.flight_end - self.flight_start).total_seconds() / 3600.0
        return None

    def computed_duty_hours(self) -> float | None:
        if self.duty_hours is not None:
            return self.duty_hours
        if self.duty_start and self.duty_end and self.duty_end > self.duty_start:
            return (self.duty_end - self.duty_start).total_seconds() / 3600.0
        return None

    def event_time(self) -> datetime:
        if self.duty_end:
            return self.duty_end
        if self.flight_end:
            return self.flight_end
        if self.duty_start:
            return self.duty_start
        return datetime.combine(self.duty_date, datetime.min.time())

    def starts_at_home_base(self) -> bool | None:
        if not self.home_base or not self.start_location:
            return None
        return self.home_base.strip().lower() == self.start_location.strip().lower()


@dataclass(frozen=True)
class ValidationIssue:
    message: str
    source_row: int | None = None
    field: str | None = None
    severity: str = "error"


@dataclass(frozen=True)
class Roster:
    source_name: str
    crew: tuple[CrewMember, ...]
    duties: tuple[DutyPeriod, ...]
    flights: tuple[Flight, ...]
    validation_issues: tuple[ValidationIssue, ...] = ()
    dropped_row_count: int = 0
    date_order: str = "iso"

    def duties_for(self, crew_id: str) -> tuple[DutyPeriod, ...]:
        rows = [d for d in self.duties if d.crew_id == crew_id]
        return tuple(sorted(rows, key=lambda d: (d.event_time(), d.source_row)))


@dataclass(frozen=True)
class Finding:
    finding_id: str
    kind: FindingKind
    rule_id: str
    rule_name: str
    framework_id: str
    ruleset_version: str
    rule_version: str
    citation: str
    crew_id: str
    crew_name: str
    duty_id: str | None
    flight_id: str | None
    event_time: datetime | None
    actual: float | None
    required: float | None
    difference: float | None
    units: str
    severity: Severity
    evidence: dict[str, Any]
    explanation: str
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class AnalysisResult:
    analyzed_at: datetime
    source_name: str
    framework_id: str
    framework_name: str
    ruleset_id: str
    ruleset_version: str
    crew_reviewed: int
    duties_analyzed: int
    flights_analyzed: int
    findings: tuple[Finding, ...]
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]
    validation_issues: tuple[ValidationIssue, ...]
    period_start: date | None = None
    period_end: date | None = None

    def counts_by_severity(self) -> dict[str, int]:
        counts = {s.value: 0 for s in Severity}
        for finding in self.findings:
            if finding.kind == FindingKind.POTENTIAL_ISSUE:
                counts[finding.severity.value] += 1
        return counts

    def potential_issue_count(self) -> int:
        return sum(1 for f in self.findings if f.kind == FindingKind.POTENTIAL_ISSUE)

    def insufficient_data_count(self) -> int:
        return sum(1 for f in self.findings if f.kind == FindingKind.INSUFFICIENT_DATA)


@dataclass(frozen=True)
class Ruleset:
    id: str
    version: str
    framework_id: str
    display_name: str
    effective_date: date
    rules: tuple[Any, ...]
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]