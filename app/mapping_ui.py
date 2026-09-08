from __future__ import annotations

import streamlit as st

from crew_compliance.ingestion.mapping import auto_map_columns


def column_mapping_form(
    headers: list[str],
    *,
    fields: tuple[str, ...],
    aliases: dict[str, tuple[str, ...]],
    key_prefix: str,
    prior: dict[str, str | None] | None = None,
) -> dict[str, str | None]:
    """Reusable canonical-field mapping. Reuses a prior mapping when headers match."""
    cache_key = f"mapping_cache_{key_prefix}"
    header_fp = tuple(headers)
    stored = st.session_state.get(cache_key) or {}
    reuse = stored.get("headers") == header_fp
    seed = stored.get("mapping") if reuse else prior
    auto = auto_map_columns(headers, fields=fields, aliases=aliases, prior=seed)
    choices = ["— not mapped —"] + list(headers)
    mapping: dict[str, str | None] = {}
    cols = st.columns(3)
    for i, field in enumerate(fields):
        default = auto.get(field)
        index = choices.index(default) if default in choices else 0
        selected = cols[i % 3].selectbox(field, choices, index=index, key=f"{key_prefix}_{field}")
        mapping[field] = None if selected == "— not mapped —" else selected
    st.session_state[cache_key] = {"headers": header_fp, "mapping": mapping}
    return mapping
