from __future__ import annotations

from typing import Protocol

from crew_compliance.domain.models import Finding, Roster, RuleMetadata
from crew_compliance.domain.opening import OpeningBalanceBook


class EvaluationContext:
    def __init__(
        self,
        framework_id: str,
        ruleset_id: str,
        ruleset_version: str,
        opening_balances: OpeningBalanceBook | None = None,
        parameter_overrides: dict[str, dict[str, float]] | None = None,
    ) -> None:
        self.framework_id = framework_id
        self.ruleset_id = ruleset_id
        self.ruleset_version = ruleset_version
        self.opening_balances = opening_balances
        self.parameter_overrides = parameter_overrides or {}

    def parameters(self, metadata: RuleMetadata) -> dict:
        merged = dict(metadata.parameters)
        overlay = self.parameter_overrides.get(metadata.rule_id) or {}
        merged.update(overlay)
        return merged

    def override_evidence(self, metadata: RuleMetadata) -> dict:
        overlay = self.parameter_overrides.get(metadata.rule_id) or {}
        if not overlay:
            return {}
        return {
            "operator_parameter_overrides": overlay,
            "published_parameters": {key: metadata.parameters.get(key) for key in overlay},
        }


class Rule(Protocol):
    metadata: RuleMetadata

    def required_inputs(self) -> frozenset[str]: ...

    def evaluate(self, roster: Roster, ctx: EvaluationContext) -> list[Finding]: ...