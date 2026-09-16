from __future__ import annotations

import sys
from dataclasses import replace
from datetime import date, timedelta, time as clock_time
from html import escape
from pathlib import Path

_APP = Path(__file__).resolve().parent
_ROOT = _APP.parent
_SRC = _ROOT / "src"
for _path in (_SRC, _APP):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import streamlit as st

from crew_compliance.domain.enums import FindingKind
from crew_compliance.engine.assignment import build_proposed_duty, check_duty_assignment
from crew_compliance.engine.parameters import editable_slots
from crew_compliance.engine.registry import get_ruleset
from crew_compliance.engine.runner import run_analysis
from crew_compliance.frameworks import FRAMEWORKS, bootstrap
from crew_compliance.ingestion.common import IngestError
from crew_compliance.ingestion.loader import load_table
from crew_compliance.ingestion.mapping import ALIASES, CANONICAL_FIELDS
from crew_compliance.ingestion.credentials import normalize_credentials
from crew_compliance.ingestion.normalize import normalize_roster
from crew_compliance.ingestion.opening import normalize_opening_balances
from crew_compliance.ingestion.schemas import CREDENTIAL_ALIASES, CREDENTIAL_FIELDS, OPENING_ALIASES, OPENING_FIELDS
from crew_compliance.reporting.export import DISCLAIMER, export_csv, export_xlsx, findings_frame
from crew_compliance.reporting.gantt import build_gantt_view, render_gantt_html
from crew_compliance.reporting.pdf import export_pdf
from crew_compliance.reporting.templates import credential_template_xlsx, opening_balance_template_xlsx

from crew_compliance.integrations.lead import (
    INTEREST_OPTIONS,
    ROLE_OPTIONS,
    LeadPayload,
    LeadResult,
    submit_lead,
    validate_email,
)
from crew_compliance.samples.demo_rosters import DISCLAIMER as SAMPLE_DISCLAIMER
from crew_compliance.samples.demo_rosters import is_sample_filename, list_samples, sample_bytes, sample_filename

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


def _render_sample_downloads(framework_id: str) -> None:
    """Ungated sample access — value before email, near the roster uploader."""
    with st.expander("Don't have a roster? Try a sample file", expanded=False):
        st.caption(
            f"{SAMPLE_DISCLAIMER} Download a sample, then upload it above to run the checker."
        )
        samples = list_samples()
        for item in samples:
            sid = item["sample_id"]
            label = item["label"]
            preferred = item["framework_id"] == framework_id
            mark = " · best match for your framework" if preferred else ""
            c1, c2 = st.columns(2)
            with c1:
                if st.download_button(
                    f"{label} sample (CSV){mark}",
                    data=sample_bytes(sid, "csv"),
                    file_name=sample_filename(sid, "csv"),
                    mime="text/csv",
                    key=f"dl_{sid}_csv",
                ):
                    st.session_state["sample_downloaded"] = sid
                    st.session_state["sample_used"] = True
            with c2:
                if st.download_button(
                    f"{label} sample (Excel)",
                    data=sample_bytes(sid, "xlsx"),
                    file_name=sample_filename(sid, "xlsx"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_{sid}_xlsx",
                ):
                    st.session_state["sample_downloaded"] = sid
                    st.session_state["sample_used"] = True


def _unlock_report_exports(
    result,
    *,
    framework_id: str,
    company_name: str,
    logo_bytes: bytes | None,
) -> None:
    """
    CSV stays free. PDF and Excel require a one-time short lead form per session.
    External lead failures never hide the analysis the user already completed.
    """
    c1, c2, c3 = st.columns(3)
    c1.download_button(
        "Download CSV",
        data=export_csv(result),
        file_name="crew_compliance_report.csv",
        mime="text/csv",
        help="Download the findings table now — no email needed.",
    )

    unlocked = bool(st.session_state.get("lead_report_unlocked"))

    if not unlocked:
        st.markdown(
            bezel(
                "<div class='aside-kicker'>Get the full report</div>"
                "<p class='aside-copy'>Enter your email to download the PDF and Excel report. "
                "We may send occasional product updates. Your roster file is never used for marketing.</p>"
            ),
            unsafe_allow_html=True,
        )
        with st.form("lead_report_form", clear_on_submit=False):
            email = st.text_input("Work email", placeholder="you@airline.com")
            role = st.selectbox(
                "Your role (optional)",
                options=["", *ROLE_OPTIONS],
                format_func=lambda v: "Select one…" if v == "" else v,
            )
            interest = st.selectbox(
                "What should software help with next? (optional)",
                options=["", *INTEREST_OPTIONS],
                format_func=lambda v: "Select one…" if v == "" else v,
            )
            submitted = st.form_submit_button("Unlock PDF & Excel")

        if submitted:
            if not validate_email(email):
                st.error("Please enter a valid email address.")
            else:
                response = submit_lead(
                    LeadPayload(
                        email=email.strip(),
                        role=role or None,
                        interest=interest or None,
                        framework_id=framework_id,
                        sample_used=bool(st.session_state.get("sample_used")),
                        report_requested=True,
                    )
                )
                st.session_state["lead_email"] = email.strip().lower()
                st.session_state["lead_report_unlocked"] = True
                st.session_state["lead_interest"] = interest or None
                if response.result == LeadResult.INVALID:
                    st.session_state["lead_report_unlocked"] = False
                    st.error(response.detail)
                elif response.result == LeadResult.PARTIAL:
                    st.warning(response.detail)
                    st.rerun()
                else:
                    st.success("PDF and Excel are unlocked for this session.")
                    st.rerun()
        return

    c2.download_button(
        "Download Excel",
        data=export_xlsx(result),
        file_name="crew_compliance_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    c3.download_button(
        "Download PDF",
        data=export_pdf(result, company_name=company_name, logo_bytes=logo_bytes),
        file_name="crew_compliance_report.pdf",
        mime="application/pdf",
    )
    if st.session_state.get("lead_interest") in {"Crew scheduling", "Roster optimization"}:
        st.caption("Thanks — we’ll keep crew scheduling and roster optimization in mind.")


def main() -> None:
    inject_theme()
    st.markdown(
        """
        <div class="island-nav">
            <span class="dot" aria-hidden="true"></span>
            <span class="mark">Crew screening · free trial</span>
        </div>
        <div class="hero">
            <div class="rise d1">
                <span class="eyebrow">Flight time · duty · rest</span>
                <h1 class="hero-title">Crew<br>Compliance<br>Checker</h1>
                <p class="lede">Upload a roster, spot potential FTL issues in seconds, then review the findings with your aviation team.</p>
            </div>
            <div class="hero-aside rise d3">
        """
        + bezel(
            "<div class='aside-kicker'>Clear, cited limits</div>"
            "<p class='aside-copy'>Rules use published numbers — not an AI guess. Findings are flags for review, not legal rulings.</p>"
        )
        + "</div></div>",
        unsafe_allow_html=True,
    )

    st.markdown(bezel(f"<p class='notice-copy'>{DISCLAIMER}</p>", "rise d2"), unsafe_allow_html=True)

    section_heading("01  /  Setup", "Choose a framework and upload a roster")
    options = {fid: fw.display_name for fid, fw in FRAMEWORKS.items()}

    left, right = st.columns((1.15, 0.85), gap="large")
    with left:
        framework_id = st.selectbox(
            "Regulatory framework",
            options=list(options.keys()),
            format_func=lambda key: options[key],
        )
        dayfirst = st.selectbox(
            "Date format in your file",
            options=[False, True],
            format_func=lambda v: "YYYY-MM-DD (ISO)" if not v else "DD/MM/YYYY (day first)",
        )
        lookahead_days = st.selectbox(
            "Credential warning window",
            options=[30, 60, 90],
            format_func=lambda n: f"{n} days ahead",
            help="Only used if you upload a licenses / medicals file.",
        )
        company_name = st.text_input("Company name on PDF (optional)", placeholder="Operator name")
        logo_file = st.file_uploader("Company logo for PDF (optional)", type=["png", "jpg", "jpeg"])
    with right:
        if framework_id in FRAMEWORKS:
            st.markdown(
                bezel(f"<p class='notice-copy'>{FRAMEWORKS[framework_id].applicability}</p>"),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                bezel(
                    "<p class='notice-copy'>Choose a framework to see who it applies to.</p>"
                ),
                unsafe_allow_html=True,
            )

    parameter_overrides: dict[str, dict[str, float]] = {}
    if framework_id in FRAMEWORKS:
        ruleset = get_ruleset(framework_id)
        with st.expander("Adjust numeric limits (optional)"):
            st.caption(
                "Defaults are the published limits. Change a value only to test a stricter operator rule. "
                "Changes are recorded on findings and do not rewrite the regulation."
            )
            for slot in editable_slots(ruleset):
                widget_key = f"ovr_{framework_id}_{slot['rule_id']}_{slot['key']}"
                value = st.number_input(
                    f"{slot['rule_id']} · {slot['key']}",
                    min_value=0.0,
                    value=float(slot["default"]),
                    help=f"{slot['citation']} — {slot['rule_name']}",
                    key=widget_key,
                )
                if abs(float(value) - float(slot["default"])) > 1e-9:
                    parameter_overrides.setdefault(slot["rule_id"], {})[slot["key"]] = float(value)

    uploaded = st.file_uploader("Roster file (CSV or Excel)", type=["csv", "xlsx"])
    _render_sample_downloads(framework_id)
    opening_file = st.file_uploader(
        "Opening balances (optional)",
        type=["csv", "xlsx"],
        help=(
            "Hours already flown or on duty before this roster starts. "
            "If you upload this file, a missing crew/window row is treated as unknown — never as zero."
        ),
    )
    st.download_button(
        "Download opening-balances template",
        data=opening_balance_template_xlsx(),
        file_name="opening_balances_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Blank spreadsheet with suggested column headers.",
    )
    credential_file = st.file_uploader(
        "Licenses, qualifications, and medicals (optional)",
        type=["csv", "xlsx"],
        help="One row per crew member per credential. Missing expiry dates show up as insufficient data.",
    )
    st.download_button(
        "Download credentials template",
        data=credential_template_xlsx(),
        file_name="credentials_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Blank spreadsheet with suggested column headers.",
    )

    if uploaded is None:
        st.markdown(
            bezel(
                "<p class='notice-copy'>Start by uploading a roster, or download a sample above and upload that. "
                "Avoid confidential airline data on shared or public machines.</p>"
            ),
            unsafe_allow_html=True,
        )
        return
    if framework_id not in FRAMEWORKS:
        return

    if is_sample_filename(uploaded.name):
        st.session_state["sample_used"] = True

    try:
        table = load_table(uploaded.getvalue(), filename=uploaded.name)
    except IngestError as exc:
        st.error(str(exc))
        return

    section_heading("02  /  Columns", "Match your spreadsheet columns")
    st.caption("Confirm each field maps to the right column, then run the analysis.")
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
        st.caption("Map opening-balance columns. Matching crew fields reuse the roster mapping when possible.")
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

    credential_mapping: dict[str, str | None] | None = None
    credential_table = None
    if credential_file is not None:
        try:
            credential_table = load_table(credential_file.getvalue(), filename=credential_file.name)
        except IngestError as exc:
            st.error(str(exc))
            return
        st.caption("Map credential columns. Matching crew fields reuse the roster mapping when possible.")
        cred_prior = {field: mapping.get(field) for field in CREDENTIAL_FIELDS}
        if not cred_prior.get("role"):
            cred_prior["role"] = mapping.get("position")
        if opening_mapping:
            for field in ("crew_id", "crew_name", "role"):
                if not cred_prior.get(field) and opening_mapping.get(field):
                    cred_prior[field] = opening_mapping[field]
        credential_mapping = column_mapping_form(
            list(credential_table.columns),
            fields=CREDENTIAL_FIELDS,
            aliases=CREDENTIAL_ALIASES,
            key_prefix="credential",
            prior=cred_prior,
        )
        st.dataframe(credential_table.head(20), use_container_width=True, hide_index=True)

    if st.button("Analyze roster"):
        rows = table.to_dict(orient="records")
        try:
            roster = normalize_roster(rows, mapping, source_name=uploaded.name, dayfirst=bool(dayfirst))
        except Exception as exc:
            st.error(f"Could not read this roster: {exc}")
            return
        if not roster.duties:
            st.error("No usable duty rows after validation. Check the messages below.")
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
        credential_book = None
        credential_issues = ()
        if credential_table is not None and credential_mapping is not None and credential_file is not None:
            credential_book = normalize_credentials(
                credential_table.to_dict(orient="records"),
                credential_mapping,
                source_name=credential_file.name,
                dayfirst=bool(dayfirst),
            )
            credential_issues = credential_book.validation_issues
        with st.spinner(f"Checking {len(roster.duties):,} duties..."):
            result = run_analysis(
                roster,
                framework_id,
                opening_balances=opening_book,
                credentials=credential_book,
                credential_lookahead_days=int(lookahead_days),
                parameter_overrides=parameter_overrides or None,
            )
        st.session_state["result"] = result
        st.session_state["roster"] = roster
        st.session_state["analysis_framework_id"] = framework_id
        st.session_state["analysis_kwargs"] = {
            "opening_balances": opening_book,
            "credentials": credential_book,
            "credential_lookahead_days": int(lookahead_days),
            "parameter_overrides": parameter_overrides or None,
        }
        st.session_state["roster_issues"] = roster.validation_issues
        st.session_state["opening_issues"] = opening_issues
        st.session_state["credential_issues"] = credential_issues
        st.success("Analysis complete.")

    result = st.session_state.get("result")
    if result is None:
        return

    issues = st.session_state.get("roster_issues") or ()
    opening_issues = st.session_state.get("opening_issues") or ()
    credential_issues = st.session_state.get("credential_issues") or ()
    issue_count = len(issues) + len(opening_issues) + len(credential_issues)
    if issue_count:
        with st.expander(f"Data quality notes ({issue_count})"):
            for issue in issues:
                st.write(f"- Roster row {issue.source_row or '—'}: {issue.message}")
            for issue in opening_issues:
                st.write(f"- Opening-balances row {issue.source_row or '—'}: {issue.message}")
            for issue in credential_issues:
                st.write(f"- Credentials row {issue.source_row or '—'}: {issue.message}")

    section_heading("03  /  Results", "Screening summary")
    counts = result.counts_by_severity()
    st.markdown(
        f"""
        <div class="bento">
          {bezel(
            f"<span class='kpi-label'>Potential issues</span><div class='kpi-value lg'>{result.potential_issue_count()}</div>"
            f"<p class='kpi-note'>Flags for professional review — not final regulatory decisions.</p>",
            "span-7 rise d1",
          )}
          {bezel(
            f"<span class='kpi-label'>Crew reviewed</span><div class='kpi-value'>{result.crew_reviewed}</div>",
            "span-5 rise d2",
          )}
          {bezel(
            f"<span class='kpi-label'>Duties checked</span><div class='kpi-value'>{result.duties_analyzed}</div>",
            "span-4 rise d3",
          )}
          {bezel(
            f"<span class='kpi-label'>Flights checked</span><div class='kpi-value'>{result.flights_analyzed}</div>",
            "span-4 rise d4",
          )}
          {bezel(
            f"<span class='kpi-label'>Missing data</span><div class='kpi-value'>{result.insufficient_data_count()}</div>",
            "span-4 rise d5",
          )}
        </div>
        <div class="severity-row">
          {bezel(f"<span class='kpi-label'>Critical</span><em>{counts['critical']}</em>", "sev rise d1")}
          {bezel(f"<span class='kpi-label'>High</span><em>{counts['high']}</em>", "sev rise d2")}
          {bezel(f"<span class='kpi-label'>Medium</span><em>{counts['medium']}</em>", "sev rise d3")}
          {bezel(f"<span class='kpi-label'>Low</span><em>{counts['low']}</em>", "sev rise d4")}
          {bezel(f"<span class='kpi-label'>Missing data</span><em>{result.insufficient_data_count()}</em>", "sev rise d5")}
        </div>
        <p class="ruleset-stamp">{result.framework_name} · {result.ruleset_id} {result.ruleset_version}</p>
        """,
        unsafe_allow_html=True,
    )

    roster = st.session_state.get("roster")
    if roster is not None and roster.crew:
        section_heading("03b  /  What-if", "Check a proposed duty")
        with st.expander("Add one duty and see what would change"):
            st.caption(
                "Uses the same rules as your last analysis. Only new or worse findings for the selected crew are shown."
            )
            crew_options = {member.crew_id: member for member in roster.crew}
            crew_id = st.selectbox(
                "Crew member",
                options=list(crew_options.keys()),
                format_func=lambda cid: f"{crew_options[cid].name} ({cid})",
                key="assign_crew",
            )
            member = crew_options[crew_id]
            date_col, start_col, end_col = st.columns(3)
            default_day = roster.duties[-1].duty_date if roster.duties else date.today()
            duty_date = date_col.date_input("Duty date", value=default_day, key="assign_date")
            start = start_col.time_input("Duty start", value=clock_time(6, 0), key="assign_start")
            end = end_col.time_input("Duty end", value=clock_time(19, 0), key="assign_end")
            sector_col, hours_col = st.columns(2)
            sectors = sector_col.number_input("Sectors (0 = auto)", min_value=0, value=0, step=1, key="assign_sectors")
            flight_hours = hours_col.number_input("Flight hours", min_value=0.0, value=8.0, step=0.1, key="assign_fh")
            if st.button("Check this duty"):
                proposed = build_proposed_duty(
                    crew_id=member.crew_id,
                    crew_name=member.name,
                    duty_date=duty_date,
                    start=start.strftime("%H:%M"),
                    end=end.strftime("%H:%M"),
                    flight_hours=float(flight_hours),
                    sector_count=int(sectors) if int(sectors) >= 1 else None,
                    home_base=member.home_base,
                    start_location=member.home_base,
                    position=member.position,
                )
                st.session_state["assignment_check"] = check_duty_assignment(
                    roster,
                    proposed,
                    st.session_state["analysis_framework_id"],
                    **(st.session_state.get("analysis_kwargs") or {}),
                )
            check = st.session_state.get("assignment_check")
            if check is not None:
                if not check.new_or_worsened:
                    st.success("No new or worse findings for this crew.")
                else:
                    issues = sum(1 for item in check.new_or_worsened if item.kind == FindingKind.POTENTIAL_ISSUE)
                    if issues:
                        st.warning(f"{issues} new or worse potential issue(s) for this duty.")
                    else:
                        st.info("Only data-gap notices — no new potential issues.")
                    for item in check.new_or_worsened:
                        st.write(f"- **{item.kind.value}** · {item.rule_id} · {item.explanation}")

    if roster is not None and roster.duties:
        section_heading("03c  /  Timeline", "Roster calendar")
        st.caption(
            "Each bar is a duty from report to release. Pins mark findings on that duty. "
            "This is a screening view, not a full scheduler."
        )
        crew_ids = [member.crew_id for member in roster.crew]
        selected_crew = st.multiselect(
            "Show crew",
            options=crew_ids,
            format_func=lambda cid: next((m.name for m in roster.crew if m.crew_id == cid), cid),
            key="gantt_crew",
        )
        duty_dates = [d.duty_date for d in roster.duties]
        min_day, max_day = min(duty_dates), max(duty_dates)
        default_from = max(min_day, max_day - timedelta(days=13))
        from_col, to_col = st.columns(2)
        win_start = from_col.date_input("From", value=default_from, min_value=min_day, max_value=max_day, key="gantt_from")
        win_end = to_col.date_input("To", value=max_day, min_value=min_day, max_value=max_day, key="gantt_to")
        if win_end < win_start:
            win_start, win_end = win_end, win_start
        visible_crew = [m for m in roster.crew if not selected_crew or m.crew_id in selected_crew]
        visible_ids = {m.crew_id for m in visible_crew} or {d.crew_id for d in roster.duties}
        visible_duties = [d for d in roster.duties if d.crew_id in visible_ids]
        sliced = replace(roster, crew=tuple(visible_crew), duties=tuple(visible_duties))
        visible_findings = tuple(f for f in result.findings if f.crew_id in visible_ids)
        st.markdown(
            bezel(
                render_gantt_html(
                    build_gantt_view(sliced, visible_findings, window_start=win_start, window_end=win_end)
                ),
                "gantt-shell rise",
            ),
            unsafe_allow_html=True,
        )

    section_heading("04  /  Findings", "What needs review")
    frame = findings_frame(result)
    if frame.empty:
        st.markdown(bezel("<p class='notice-copy'>No findings for this roster.</p>"), unsafe_allow_html=True)
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

    section_heading("05  /  Detail", "Finding explanation")
    if view.empty:
        st.markdown(bezel("<p class='notice-copy'>No rows match these filters.</p>"), unsafe_allow_html=True)
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
                f"<div><div class='meta-line'>Limit · difference</div><p class='meta-val'>{escape(str(selected.required))} · {escape(str(selected.difference))}</p></div>"
                f"<div><div class='meta-line'>Opening balance</div><p class='meta-val'>{escape(_opening_balance_label(selected.evidence))}</p></div>"
                f"<div><div class='meta-line'>Credential</div><p class='meta-val'>{escape(_credential_label(selected.evidence))}</p></div>"
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

    section_heading("06  /  Export", "Download your report")
    logo_bytes = logo_file.getvalue() if logo_file is not None else None
    _unlock_report_exports(
        result,
        framework_id=st.session_state.get("analysis_framework_id") or framework_id,
        company_name=company_name,
        logo_bytes=logo_bytes,
    )


def _opening_balance_label(evidence: dict) -> str:
    status = evidence.get("opening_balance_status")
    if not status:
        return "Not used for this check"
    if status == "not_provided":
        return "No opening-balances file uploaded"
    if status == "missing":
        window = evidence.get("opening_balance_window") or "this window"
        return f"Missing for {window} — treated as unknown, not zero"
    hours = evidence.get("opening_balance_hours")
    as_of = evidence.get("opening_balance_as_of") or "unknown date"
    if status == "applied":
        return f"{hours} hours as of {as_of}"
    if status == "not_applied_window_complete_in_roster":
        return f"On file ({hours} h as of {as_of}) but not added — roster already covers this window"
    return str(status)


def _credential_label(evidence: dict) -> str:
    cred_type = evidence.get("credential_type")
    if not cred_type:
        return "Not used for this check"
    detail = evidence.get("credential_detail")
    expiry = evidence.get("expiry_date") or "expiry missing"
    label = f"{cred_type}" + (f" — {detail}" if detail else "")
    if evidence.get("expiry_date") is None:
        return f"{label} · expiry missing"
    bits = [f"{label} · expires {expiry}"]
    if evidence.get("scheduled_on_or_after_expiry"):
        bits.append("duty on or after expiry")
    elif evidence.get("scheduled_in_window"):
        bits.append("duty inside warning window")
    return " · ".join(bits)


main()