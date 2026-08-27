from __future__ import annotations

from typing import Protocol

from crew_compliance.domain.models import Finding, Roster, RuleMetadata


class EvaluationContext:
    def __init__(self, framework_id: str, ruleset_id: str, ruleset_version: str) -> None:
        self.framework_id = framework_id
        self.ruleset_id = ruleset_id
        self.ruleset_version = ruleset_version


class Rule(Protocol):
    metadata: RuleMetadata

    def required_inputs(self) -> frozenset[str]: ...

    def evaluate(self, roster: Roster, ctx: EvaluationContext) -> list[Finding]: ...