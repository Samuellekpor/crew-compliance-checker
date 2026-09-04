from __future__ import annotations

import sys
from html import escape
from pathlib import Path

_APP = Path(__file__).resolve().parent
_ROOT = _APP.parent
_SRC = _ROOT / "src"
for _path in (_SRC, _APP):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import streamlit as st

from crew_compliance.engine.runner import run_analysis
from crew_compliance.frameworks import FRAMEWORKS, STUB_FRAMEWORKS, bootstrap
from crew_compliance.ingestion.common import IngestError
from crew_compliance.ingestion.loader import load_table
from crew_compliance.ingestion.mapping import ALIASES, CANONICAL_FIELDS
from crew_compliance.ingestion.normalize import normalize_roster
from crew_compliance.ingestion.opening import normalize_opening_balances
from crew_compliance.ingestion.schemas import OPENING_ALIASES, OPENING_FIELDS
from crew_compliance.reporting.export import DISCLAIMER, export_csv, export_xlsx, findings_frame

from mapping_ui import column_mapping_form

st.set_page_config(page_title="Crew Compliance Checker", layout="wide", page_icon="·")

bootstrap()

THEME_CSS = (Path(__file__).parent / "theme.css").read_text(encoding="utf-8")


def inject_theme() -> None:
    st.markdown(
        f"<style>{THEME_CSS}</style><div class='app-grain' aria-hidden='true'></div>",
        unsafe_allow_html=True,
    )


def bezel(inner: str, extra_class: str = "") -> str:
    return (
        f"<div class='bezel {extra_class}'><div class='bezel-inner'>{inner}</div></div>"
    )


def section_heading(eyebrow: str, title: str) -> None:
    st.markdown(
        f"<div class='section-head rise'><span class='eyebrow'>{eyebrow}</span>"
        f"<h2>{title}</h2></div>",
        unsafe_allow_html=True,
    )


def main() -> None:
    inject_theme()
    st.markdown(
        """
        <div class="island-nav">
            <span class="dot" aria-hidden="true"></span>
            <span class="mark">Local screening · V2</span>
        </div>
        <div class="hero">
            <div class="rise d1">
                <span class="eyebrow">Flight time · duty · rest</span>
                <h1 class="hero-title">Crew<br>Compliance<br>Checker</h1>
                <p class="lede">Upload a crew roster. Detect potential FTL compliance issues in seconds — then review with a qualified aviation professional.</p>
            </div>
            <div class="hero-aside rise d3">
        """
        + bezel(
            "<div class='aside-kicker'>Deterministic engine</div>"
            "<p class='aside-copy'>Cited limits. No model deciding legality. Findings require review.</p>"
        )
        + "</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown(bezel(f"<p class='notice-copy'>{DISCLAIMER}</p>", "rise d2"), unsafe_allow_html=True)

    section_heading("01  /  Configuration", "Upload & framework")
    implemented = {fid: fw.display_name for fid, fw in FRAMEWORKS.items()}
    stub_labels = {fid: f"{label} — not in V1" for fid, label in STUB_FRAMEWORKS}
    options = {**implemented, **stub_labels}

    left, right = st.columns((1.15, 0.85), gap="large")
    with left:
        framework_id = st.selectbox(
            "Regulatory framework",
            options=list(options.keys()),
            format_func=lambda key: options[key],
        )
        dayfirst = st.selectbox(
            "Date format",
            options=[False, True],
            format_func=lambda v: "YYYY-MM-DD / ISO" if not v else "DD/MM/YYYY (day first)",
        )
    with right:
        if framework_id in FRAMEWORKS:
            st.markdown(
                bezel(f"<p class='notice-copy'>{FRAMEWORKS[framework_id].applicability}</p>"),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                bezel(
                    "<p class='notice-copy'>This jurisdiction is listed for the product roadmap only and cannot be analyzed in V1.</p>"
                ),
                unsafe_allow_html=True,
            )

    uploaded = st.file_uploader("Roster file — CSV or XLSX", type=["csv", "xlsx"])
    opening_file = st.file_uploader(
        "Opening balances — CSV or XLSX (optional)",
        type=["csv", "xlsx"],
        help=(
            "Carry-over hours already accrued before this roster file. Optional at the app level. "
            "Once uploaded, a missing row for a crew member and window type is treated as "
            "insufficient data — never as zero."
        ),
    )

    if uploaded is None:
        st.markdown(
            bezel(
                "<p class='notice-copy'>No file yet. A synthetic demonstration roster lives at <em>samples/sample_roster.csv</em>. Do not use confidential airline data on a shared machine.</p>"
            ),
            unsafe_allow_html=True,
        )
        return
    if framework_id not in FRAMEWORKS:
        return

    try:
        table = load_table(uploaded.getvalue(), filename=uploaded.name)
    except IngestError as exc:
        st.error(str(exc))
        return

    section_heading("02  /  Normalization", "Column mapping")
    st.caption("The engine never reads spreadsheet headers. Confirm the mapping, then analyze.")
    mapping = column_mapping_form(
        list(table.columns),
        fields=CANONICAL_FIELDS,
        aliases=ALIASES,
        key_prefix="roster",
    )
    st.dataframe(table.head(20), use_container_width=True, hide_index=True)

    opening_mapping: dict[str, str | None] | None = None
    opening_table = None
    if opening_file is not None:
        try:
            opening_table = load_table(opening_file.getvalue(), filename=opening_file.name)
        except IngestError as exc:
            st.error(str(exc))
            return
        st.caption(
            "Opening-balance columns. Shared crew fields reuse the roster mapping when headers match."
        )
        prior = {field: mapping.get(field) for field in OPENING_FIELDS}
        if not prior.get("role"):
            prior["role"] = mapping.get("position")
        opening_mapping = column_mapping_form(
            list(opening_table.columns),
            fields=OPENING_FIELDS,
            aliases=OPENING_ALIASES,
            key_prefix="opening",
            prior=prior,
        )
        st.dataframe(opening_table.head(20), use_container_width=True, hide_index=True)

    if st.button("Analyze roster"):
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
        opening_book = None
        opening_issues = ()
        if opening_table is not None and opening_mapping is not None and opening_file is not None:
            opening_book = normalize_opening_balances(
                opening_table.to_dict(orient="records"),
                opening_mapping,
                source_name=opening_file.name,
                dayfirst=bool(dayfirst),
            )
            opening_issues = opening_book.validation_issues
        with st.spinner(f"Analyzing {len(roster.duties):,} duties..."):
            result = run_analysis(roster, framework_id, opening_balances=opening_book)
        st.session_state["result"] = result
        st.session_state["roster_issues"] = roster.validation_issues
        st.session_state["opening_issues"] = opening_issues
        st.success("Analysis complete.")

    result = st.session_state.get("result")
    if result is None:
        return

    issues = st.session_state.get("roster_issues") or ()
    opening_issues = st.session_state.get("opening_issues") or ()
    if issues or opening_issues:
        with st.expander(f"Validation messages ({len(issues) + len(opening_issues)})"):
            for issue in issues:
                st.write(f"- Roster row {issue.source_row or '—'}: {issue.message}")
            for issue in opening_issues:
                st.write(f"- Opening-balances row {issue.source_row or '—'}: {issue.message}")

    section_heading("03  /  Screening", "Compliance summary")
    counts = result.counts_by_severity()
    st.markdown(
        f"""
        <div class="bento">
          {bezel(
            f"<span class='kpi-label'>Potential findings</span><div class='kpi-value lg'>{result.potential_issue_count()}</div>"
            f"<p class='kpi-note'>Issues that require professional review — not regulatory determinations.</p>",
            "span-7 rise d1",
          )}
          {bezel(
            f"<span class='kpi-label'>Crew reviewed</span><div class='kpi-value'>{result.crew_reviewed}</div>",
            "span-5 rise d2",
          )}
          {bezel(
            f"<span class='kpi-label'>Duties analyzed</span><div class='kpi-value'>{result.duties_analyzed}</div>",
            "span-4 rise d3",
          )}
          {bezel(
            f"<span class='kpi-label'>Flights analyzed</span><div class='kpi-value'>{result.flights_analyzed}</div>",
            "span-4 rise d4",
          )}
          {bezel(
            f"<span class='kpi-label'>Insufficient data</span><div class='kpi-value'>{result.insufficient_data_count()}</div>",
            "span-4 rise d5",
          )}
        </div>
        <div class="severity-row">
          {bezel(f"<span class='kpi-label'>Critical</span><em>{counts['critical']}</em>", "sev rise d1")}
          {bezel(f"<span class='kpi-label'>High</span><em>{counts['high']}</em>", "sev rise d2")}
          {bezel(f"<span class='kpi-label'>Medium</span><em>{counts['medium']}</em>", "sev rise d3")}
          {bezel(f"<span class='kpi-label'>Low</span><em>{counts['low']}</em>", "sev rise d4")}
          {bezel(f"<span class='kpi-label'>Coverage</span><em>{result.insufficient_data_count()}</em>", "sev rise d5")}
        </div>
        <p class="ruleset-stamp">{result.framework_name} · {result.ruleset_id} {result.ruleset_version}</p>
        """,
        unsafe_allow_html=True,
    )

    section_heading("04  /  Review", "Findings")
    frame = findings_frame(result)
    if frame.empty:
        st.markdown(bezel("<p class='notice-copy'>No findings were generated for this roster.</p>"), unsafe_allow_html=True)
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

    section_heading("05  /  Evidence", "Finding details")
    if view.empty:
        st.markdown(bezel("<p class='notice-copy'>No rows match the current filters.</p>"), unsafe_allow_html=True)
    else:
        labels = {
            row.finding_id: f"{row.severity.upper()} · {row.crew_name} · {row.rule_id}"
            for row in view.itertuples()
        }
        selected_id = st.selectbox("Select a finding", list(labels.keys()), format_func=lambda k: labels[k])
        selected = next(f for f in result.findings if f.finding_id == selected_id)
        assumptions = "".join(f"<li>{escape(item)}</li>" for item in selected.assumptions)
        limitations = "".join(f"<li>{escape(item)}</li>" for item in selected.limitations)
        st.markdown(
            bezel(
                f"<span class='eyebrow'>{escape(selected.citation)}</span>"
                f"<h2 style='margin-top:0.4rem'>{escape(selected.rule_name)}</h2>"
                f"<p class='notice-copy'>{escape(selected.explanation)}</p>"
                "<div class='detail-grid' style='margin-top:1.25rem'>"
                f"<div><div class='meta-line'>Crew</div><p class='meta-val'>{escape(selected.crew_name)} ({escape(selected.crew_id)})</p></div>"
                f"<div><div class='meta-line'>Duty / flight</div><p class='meta-val'>{escape(selected.duty_id or '—')} · {escape(selected.flight_id or '—')}</p></div>"
                f"<div><div class='meta-line'>Actual</div><p class='meta-val'>{escape(str(selected.actual))} {escape(selected.units)}</p></div>"
                f"<div><div class='meta-line'>Required · difference</div><p class='meta-val'>{escape(str(selected.required))} · {escape(str(selected.difference))}</p></div>"
                f"<div><div class='meta-line'>Opening balance</div><p class='meta-val'>{escape(_opening_balance_label(selected.evidence))}</p></div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        with st.expander("Evidence, assumptions, and limitations"):
            st.json(selected.evidence)
            st.markdown("**Assumptions**")
            st.markdown(assumptions, unsafe_allow_html=True)
            st.markdown("**Limitations**")
            st.markdown(limitations, unsafe_allow_html=True)

    section_heading("06  /  Record", "Export the screening")
    c1, c2 = st.columns(2)
    c1.download_button("Export CSV", data=export_csv(result), file_name="crew_compliance_report.csv", mime="text/csv")
    c2.download_button(
        "Export Excel",
        data=export_xlsx(result),
        file_name="crew_compliance_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _opening_balance_label(evidence: dict) -> str:
    status = evidence.get("opening_balance_status")
    if not status:
        return "Not used by this check"
    if status == "not_provided":
        return "No opening-balances file uploaded"
    if status == "missing":
        window = evidence.get("opening_balance_window") or "this window"
        return f"Missing for {window} — not assumed to be zero"
    hours = evidence.get("opening_balance_hours")
    as_of = evidence.get("opening_balance_as_of") or "unknown date"
    if status == "applied":
        return f"{hours} hours as of {as_of}"
    if status == "not_applied_window_complete_in_roster":
        return f"On file ({hours} h as of {as_of}) but not added — roster already covers the window"
    return str(status)


main()