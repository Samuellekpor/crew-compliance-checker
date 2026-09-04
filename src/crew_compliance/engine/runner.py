from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from crew_compliance.domain.credentials import CredentialBook
from crew_compliance.domain.models import AnalysisResult, Roster
from crew_compliance.domain.opening import OpeningBalanceBook
from crew_compliance.engine.credential_rules import evaluate_credential_expiry
from crew_compliance.engine.protocol import EvaluationContext
from crew_compliance.engine.registry import get_ruleset
from crew_compliance.frameworks import FRAMEWORKS, bootstrap


def run_analysis(
    roster: Roster,
    framework_id: str,
    ruleset_version: str | None = None,
    opening_balances: OpeningBalanceBook | None = None,
    credentials: CredentialBook | None = None,
    credential_lookahead_days: int = 30,
    parameter_overrides: dict[str, dict[str, float]] | None = None,
) -> AnalysisResult:
    bootstrap()
    ruleset = get_ruleset(framework_id, ruleset_version)
    overrides = parameter_overrides or {}
    ctx = EvaluationContext(
        framework_id,
        ruleset.id,
        ruleset.version,
        opening_balances=opening_balances,
        parameter_overrides=overrides,
    )
    findings = []
    for rule in ruleset.rules:
        batch = rule.evaluate(roster, ctx)
        overlay = ctx.override_evidence(rule.metadata)
        if overlay:
            batch = [replace(item, evidence={**item.evidence, **overlay}) for item in batch]
        findings.extend(batch)
    if credentials is not None:
        findings.extend(
            evaluate_credential_expiry(roster, ctx, credentials, credential_lookahead_days)
        )
    unique_flights = {d.flight_id for d in roster.duties if d.flight_id}
    duty_dates = [d.duty_date for d in roster.duties]
    framework = FRAMEWORKS.get(framework_id)
    framework_name = framework.display_name if framework else framework_id
    extra_assumptions = ()
    if overrides:
        extra_assumptions = (
            "One or more published numeric limits were replaced by operator-entered values for this run. "
            "Findings that used an overlay record both the published and the operator values in evidence.",
        )
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
        assumptions=ruleset.assumptions + extra_assumptions,
        limitations=ruleset.limitations,
        validation_issues=roster.validation_issues,
        period_start=min(duty_dates) if duty_dates else None,
        period_end=max(duty_dates) if duty_dates else None,
        parameter_overrides=overrides,
    )