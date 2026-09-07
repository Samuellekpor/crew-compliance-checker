from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, time

from crew_compliance.domain.enums import FindingKind, Severity
from crew_compliance.domain.models import Finding
from crew_compliance.reporting.gantt import build_gantt_view, render_gantt_html
from tests.helpers import make_duty, make_roster


def _finding(**kwargs) -> Finding:
    defaults = dict(
        finding_id="f1",
        kind=FindingKind.POTENTIAL_ISSUE,
        rule_id="EASA-FTL-205-TABLE",
        rule_name="Daily FDP",
        framework_id="easa",
        ruleset_version="1.0.0",
        rule_version="1.0.0",
        citation="ORO.FTL.205",
        crew_id="C1",
        crew_name="Crew One",
        duty_id=None,
        flight_id=None,
        event_time=None,
        actual=13.1,
        required=13.0,
        difference=0.1,
        units="hours",
        severity=Severity.MEDIUM,
        evidence={},
        explanation="FDP exceeds the table.",
        assumptions=(),
        limitations=(),
    )
    defaults.update(kwargs)
    return Finding(**defaults)


def test_pin_attaches_to_the_cited_duty():
    first = make_duty(start="06:00", end="16:00", flight_id="A")
    second = make_duty(day=date(2026, 6, 2), start="06:00", end="19:06", flight_id="B", source_row=3)
    roster = make_roster([first, second])
    view = build_gantt_view(
        roster,
        [_finding(duty_id=second.duty_id, event_time=second.duty_end, finding_id="pin-b")],
    )
    lane = view.lanes[0]
    by_id = {bar.duty_id: bar for bar in lane.bars}
    assert not by_id[first.duty_id].pins
    assert by_id[second.duty_id].pins[0].finding_id == "pin-b"
    assert by_id[second.duty_id].pins[0].offset_ratio == 1.0


def test_pin_falls_back_to_the_duty_covering_event_time():
    duty = make_duty(start="06:00", end="16:00")
    roster = make_roster([duty])
    mid = datetime.combine(date(2026, 6, 1), time(12, 0))
    view = build_gantt_view(roster, [_finding(event_time=mid, finding_id="mid")])
    assert view.lanes[0].bars[0].pins[0].finding_id == "mid"
    assert abs(view.lanes[0].bars[0].pins[0].offset_ratio - 0.6) < 1e-9


def test_date_only_duty_spans_the_calendar_day():
    duty = replace(make_duty(), duty_start=None, duty_end=None)
    view = build_gantt_view(make_roster([duty]))
    bar = view.lanes[0].bars[0]
    assert bar.date_only
    assert bar.start == datetime(2026, 6, 1, 0, 0)
    assert bar.end == datetime(2026, 6, 2, 0, 0)


def test_unmatched_crew_finding_stays_unattached():
    roster = make_roster([make_duty()])
    view = build_gantt_view(
        roster,
        [_finding(crew_id="C9", crew_name="Other", finding_id="loose")],
    )
    extra = [lane for lane in view.lanes if lane.crew_id == "C9"]
    assert extra
    assert extra[0].unattached[0].finding_id == "loose"
    assert not extra[0].bars


def test_html_pins_finding_on_the_duty_bar():
    duty = make_duty(start="06:00", end="16:00", flight_id="BA050")
    roster = make_roster([duty])
    view = build_gantt_view(roster, [_finding(duty_id=duty.duty_id, finding_id="pin-1")])
    html = render_gantt_html(view)
    assert "Crew One" in html
    assert "BA050" in html
    assert 'data-finding-id="pin-1"' in html
    assert "gantt-pin" in html


def test_html_escapes_crew_names():
    duty = make_duty(name='<script>x</script>')
    html = render_gantt_html(build_gantt_view(make_roster([duty])))
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_overnight_bar_keeps_actual_start_and_end():
    duty = make_duty(start="22:00", end="06:00")
    view = build_gantt_view(make_roster([duty]))
    bar = view.lanes[0].bars[0]
    assert bar.start.hour == 22
    assert bar.end.date() == date(2026, 6, 2)
    assert bar.end.hour == 6
