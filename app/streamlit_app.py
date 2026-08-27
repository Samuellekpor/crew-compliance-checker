from __future__ import annotations

import streamlit as st

from crew_compliance.engine.runner import run_analysis
from crew_compliance.frameworks import FRAMEWORKS, STUB_FRAMEWORKS, bootstrap
from crew_compliance.ingestion.common import IngestError
from crew_compliance.ingestion.loader import load_table
from crew_compliance.ingestion.mapping import CANONICAL_FIELDS, auto_map_columns
from crew_compliance.ingestion.normalize import normalize_roster
from crew_compliance.reporting.export import DISCLAIMER, export_csv, export_xlsx, findings_frame

st.set_page_config(page_title="Crew Compliance Checker", layout="wide", page_icon="✈")

bootstrap()

CSS = """
<style>
    .block-container { padding-top: 1.4rem; }
    h1 { letter-spacing: 0.02em; }
    .disclaimer {
        background: #f4f1ea;
        border-left: 4px solid #8a6d3b;
        padding: 0.8rem 1rem;
        color: #3d3426;
        font-size: 0.92rem;
    }
    .kpi { background: #0f2744; color: #f7f4ee; padding: 0.85rem 1rem; border-radius: 6px; }
    .kpi span { display: block; font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase; color: #c9b896; }
    .kpi strong { font-size: 1.6rem; }
</style>
"""


def main() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    st.title("Crew Compliance Checker")
    st.caption("Upload a crew roster. Detect potential crew FTL compliance issues in seconds.")
    st.markdown(f'<div class="disclaimer">{DISCLAIMER}</div>', unsafe_allow_html=True)

    st.header("Upload & configuration")
    implemented = {fid: fw.display_name for fid, fw in FRAMEWORKS.items()}
    stub_labels = {fid: f"{label} (not implemented in V1)" for fid, label in STUB_FRAMEWORKS}
    options = {**implemented, **stub_labels}
    framework_id = st.selectbox(
        "Regulatory framework",
        options=list(options.keys()),
        format_func=lambda key: options[key],
    )
    if framework_id in FRAMEWORKS:
        st.info(FRAMEWORKS[framework_id].applicability)
    else:
        st.warning("This framework is listed for roadmap purposes only and cannot be analyzed in V1.")

    dayfirst = st.selectbox(
        "Date format",
        options=[False, True],
        format_func=lambda v: "YYYY-MM-DD / ISO (recommended)" if not v else "DD/MM/YYYY (day first)",
    )
    uploaded = st.file_uploader("Upload roster (CSV or XLSX)", type=["csv", "xlsx"])

    if uploaded is None:
        st.info("No file uploaded yet. A synthetic sample is available at `samples/sample_roster.csv`.")
        return
    if framework_id not in FRAMEWORKS:
        return

    try:
        table = load_table(uploaded.getvalue(), filename=uploaded.name)
    except IngestError as exc:
        st.error(str(exc))
        return

    st.subheader("Column mapping")
    st.caption("Rules never depend on spreadsheet headers. Confirm the mapping, then analyze.")
    auto = auto_map_columns(list(table.columns))
    headers = ["— not mapped —"] + list(table.columns)
    mapping: dict[str, str | None] = {}
    cols = st.columns(3)
    for i, field in enumerate(CANONICAL_FIELDS):
        default = auto.get(field)
        index = headers.index(default) if default in headers else 0
        selected = cols[i % 3].selectbox(field, headers, index=index, key=f"map_{field}")
        mapping[field] = None if selected == "— not mapped —" else selected

    st.dataframe(table.head(20), use_container_width=True, hide_index=True)

    if st.button("Analyze roster", type="primary"):
        rows = table.to_dict(orient="records")
        try:
            roster = normalize_roster(rows, mapping, source_name=uploaded.name, dayfirst=bool(dayfirst))
        except Exception as exc:
            st.error(f"The roster could not be normalized: {exc}")
            return
        if not roster.duties:
            st.error("No usable duty rows remained after validation. Review the messages below.")
            for issue in roster.validation_issues:
                st.write(f"- Row {issue.source_row}: {issue.message}")
            return
        with st.spinner(f"Analyzing {len(roster.duties):,} duties..."):
            result = run_analysis(roster, framework_id)
        st.session_state["result"] = result
        st.session_state["roster_issues"] = roster.validation_issues
        st.success("Analysis complete.")

    result = st.session_state.get("result")
    if result is None:
        return

    issues = st.session_state.get("roster_issues") or ()
    if issues:
        with st.expander(f"Validation messages ({len(issues)})"):
            for issue in issues:
                st.write(f"- Row {issue.source_row or '—'}: {issue.message}")

    st.header("Compliance summary")
    counts = result.counts_by_severity()
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f'<div class="kpi"><span>Crew reviewed</span><strong>{result.crew_reviewed}</strong></div>', unsafe_allow_html=True)
    k2.markdown(f'<div class="kpi"><span>Duties analyzed</span><strong>{result.duties_analyzed}</strong></div>', unsafe_allow_html=True)
    k3.markdown(f'<div class="kpi"><span>Flights analyzed</span><strong>{result.flights_analyzed}</strong></div>', unsafe_allow_html=True)
    k4.markdown(
        f'<div class="kpi"><span>Potential findings</span><strong>{result.potential_issue_count()}</strong></div>',
        unsafe_allow_html=True,
    )
    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("Critical", counts["critical"])
    s2.metric("High", counts["high"])
    s3.metric("Medium", counts["medium"])
    s4.metric("Low", counts["low"])
    s5.metric("Insufficient data", result.insufficient_data_count())
    st.caption(
        f"{result.framework_name} · ruleset {result.ruleset_id} {result.ruleset_version}"
    )

    st.header("Findings")
    frame = findings_frame(result)
    if frame.empty:
        st.write("No findings were generated.")
        return

    f1, f2, f3, f4, f5 = st.columns(5)
    severity = f1.multiselect("Severity", sorted(frame["severity"].unique()))
    crew = f2.multiselect("Crew member", sorted(frame["crew_name"].unique()))
    rule = f3.multiselect("Rule", sorted(frame["rule_id"].unique()))
    kind = f4.multiselect("Kind", sorted(frame["kind"].unique()))
    date_filter = f5.multiselect("Date", sorted({d for d in frame["date"].tolist() if d}))
    view = frame.copy()
    if severity:
        view = view[view["severity"].isin(severity)]
    if crew:
        view = view[view["crew_name"].isin(crew)]
    if rule:
        view = view[view["rule_id"].isin(rule)]
    if kind:
        view = view[view["kind"].isin(kind)]
    if date_filter:
        view = view[view["date"].isin(date_filter)]

    display_cols = ["severity", "crew_name", "date", "rule_name", "actual", "required", "difference", "kind"]
    st.dataframe(view[display_cols], use_container_width=True, hide_index=True)

    st.header("Finding details")
    if view.empty:
        st.write("No rows match the current filters.")
    else:
        labels = {
            row.finding_id: f"{row.severity.upper()} · {row.crew_name} · {row.rule_id}"
            for row in view.itertuples()
        }
        selected_id = st.selectbox("Select a finding", list(labels.keys()), format_func=lambda k: labels[k])
        selected = next(f for f in result.findings if f.finding_id == selected_id)
        st.markdown(f"**{selected.rule_name}** (`{selected.rule_id}`)")
        st.write(f"Regulatory reference: {selected.citation}")
        st.write(f"Crew member: {selected.crew_name} ({selected.crew_id})")
        st.write(f"Duty: {selected.duty_id or '—'} · Flight: {selected.flight_id or '—'}")
        st.write(f"Actual: {selected.actual} {selected.units} · Required: {selected.required} · Difference: {selected.difference}")
        st.write(selected.explanation)
        st.json(selected.evidence)
        st.markdown("**Assumptions**")
        for item in selected.assumptions:
            st.write(f"- {item}")
        st.markdown("**Limitations**")
        for item in selected.limitations:
            st.write(f"- {item}")

    st.header("Report")
    c1, c2 = st.columns(2)
    c1.download_button("Export CSV", data=export_csv(result), file_name="crew_compliance_report.csv", mime="text/csv")
    c2.download_button(
        "Export Excel",
        data=export_xlsx(result),
        file_name="crew_compliance_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


main()