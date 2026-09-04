from __future__ import annotations

from datetime import datetime, timezone

from crew_compliance.domain.models import AnalysisResult, Roster
from crew_compliance.domain.opening import OpeningBalanceBook
from crew_compliance.engine.protocol import EvaluationContext
from crew_compliance.engine.registry import get_ruleset
from crew_compliance.frameworks import bootstrap


def run_analysis(
    roster: Roster,
    framework_id: str,
    ruleset_version: str | None = None,
    opening_balances: OpeningBalanceBook | None = None,
) -> AnalysisResult:
    bootstrap()
    ruleset = get_ruleset(framework_id, ruleset_version)
    ctx = EvaluationContext(
        framework_id,
        ruleset.id,
        ruleset.version,
        opening_balances=opening_balances,
    )
    findings = []
    for rule in ruleset.rules:
        findings.extend(rule.evaluate(roster, ctx))
    unique_flights = {d.flight_id for d in roster.duties if d.flight_id}
    framework_name = {
        "easa": "EASA Air Ops — Subpart FTL",
        "faa_part_117": "FAA 14 CFR Part 117",
    }.get(framework_id, framework_id)
    return AnalysisResult(
        analyzed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        source_name=roster.source_name,
        framework_id=framework_id,
        framework_name=framework_name,
        ruleset_id=ruleset.id,
        ruleset_version=ruleset.version,
        crew_reviewed=len({c.crew_id for c in roster.crew}),
        duties_analyzed=len(roster.duties),
        flights_analyzed=len(unique_flights),
        findings=tuple(findings),
        assumptions=ruleset.assumptions,
        limitations=ruleset.limitations,
        validation_issues=roster.validation_issues,
    )