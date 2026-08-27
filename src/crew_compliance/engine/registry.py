from __future__ import annotations

from crew_compliance.domain.models import Ruleset

_RULESETS: dict[tuple[str, str], Ruleset] = {}
_DEFAULT: dict[str, str] = {}


def register_ruleset(ruleset: Ruleset) -> None:
    _RULESETS[(ruleset.framework_id, ruleset.version)] = ruleset
    _DEFAULT[ruleset.framework_id] = ruleset.version


def get_ruleset(framework_id: str, version: str | None = None) -> Ruleset:
    ver = version or _DEFAULT.get(framework_id)
    if not ver:
        raise KeyError(f"No ruleset registered for framework '{framework_id}'.")
    key = (framework_id, ver)
    if key not in _RULESETS:
        raise KeyError(f"No ruleset '{ver}' for framework '{framework_id}'.")
    return _RULESETS[key]


def list_framework_ids() -> list[str]:
    return sorted({fid for fid, _ver in _RULESETS})