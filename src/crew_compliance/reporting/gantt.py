from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from html import escape

from crew_compliance.domain.models import AnalysisResult, DutyPeriod, Finding, Roster


@dataclass(frozen=True)
class GanttPin:
    finding_id: str
    kind: str
    severity: str
    rule_id: str
    rule_name: str
    citation: str
    explanation: str
    offset_ratio: float


@dataclass(frozen=True)
class GanttBar:
    duty_id: str
    crew_id: str
    crew_name: str
    start: datetime
    end: datetime
    label: str
    is_positioning: bool
    date_only: bool
    pins: tuple[GanttPin, ...]


@dataclass(frozen=True)
class GanttLane:
    crew_id: str
    crew_name: str
    bars: tuple[GanttBar, ...]
    unattached: tuple[GanttPin, ...]


@dataclass(frozen=True)
class GanttView:
    range_start: datetime
    range_end: datetime
    lanes: tuple[GanttLane, ...]


def build_gantt_view(roster: Roster, findings: tuple[Finding, ...] | list[Finding] = ()) -> GanttView:
    duties_by_id = {duty.duty_id: duty for duty in roster.duties}
    duties_by_crew: dict[str, list[DutyPeriod]] = defaultdict(list)
    for duty in roster.duties:
        duties_by_crew[duty.crew_id].append(duty)

    pins_by_duty: dict[str, list[GanttPin]] = defaultdict(list)
    unattached_by_crew: dict[str, list[GanttPin]] = defaultdict(list)
    extra_crew: dict[str, str] = {}

    for finding in findings:
        extra_crew.setdefault(finding.crew_id, finding.crew_name)
        target = _target_duty(finding, duties_by_id, duties_by_crew.get(finding.crew_id, ()))
        pin = _pin_from_finding(finding, target)
        if target is None:
            unattached_by_crew[finding.crew_id].append(pin)
        else:
            pins_by_duty[target.duty_id].append(pin)

    lanes: list[GanttLane] = []
    seen_crew: set[str] = set()
    for member in roster.crew:
        seen_crew.add(member.crew_id)
        duties = sorted(duties_by_crew.get(member.crew_id, ()), key=lambda d: (d.event_time(), d.source_row))
        bars = tuple(_bar(duty, pins_by_duty.get(duty.duty_id, ())) for duty in duties)
        lanes.append(
            GanttLane(
                crew_id=member.crew_id,
                crew_name=member.name,
                bars=bars,
                unattached=tuple(unattached_by_crew.get(member.crew_id, ())),
            )
        )
    for crew_id, name in extra_crew.items():
        if crew_id in seen_crew:
            continue
        lanes.append(
            GanttLane(
                crew_id=crew_id,
                crew_name=name,
                bars=(),
                unattached=tuple(unattached_by_crew.get(crew_id, ())),
            )
        )

    starts: list[datetime] = []
    ends: list[datetime] = []
    for lane in lanes:
        for bar in lane.bars:
            starts.append(bar.start)
            ends.append(bar.end)
    if not starts:
        today = datetime.combine(date.today(), datetime.min.time())
        return GanttView(today, today + timedelta(days=1), tuple(lanes))
    range_start = min(starts).replace(hour=0, minute=0, second=0, microsecond=0)
    last = max(ends)
    range_end = datetime.combine(last.date() + timedelta(days=1), datetime.min.time())
    if range_end <= range_start:
        range_end = range_start + timedelta(days=1)
    return GanttView(range_start, range_end, tuple(lanes))


def build_gantt_view_from_result(roster: Roster, result: AnalysisResult) -> GanttView:
    return build_gantt_view(roster, result.findings)


def _bar(duty: DutyPeriod, pins: list[GanttPin]) -> GanttBar:
    start, end, date_only = _bar_span(duty)
    label = duty.flight_id or duty.duty_kind.value.replace("_", " ")
    return GanttBar(
        duty_id=duty.duty_id,
        crew_id=duty.crew_id,
        crew_name=duty.crew_name,
        start=start,
        end=end,
        label=label,
        is_positioning=duty.is_positioning,
        date_only=date_only,
        pins=tuple(pins),
    )


def _bar_span(duty: DutyPeriod) -> tuple[datetime, datetime, bool]:
    if duty.duty_start and duty.duty_end and duty.duty_end > duty.duty_start:
        return duty.duty_start, duty.duty_end, False
    day = datetime.combine(duty.duty_date, datetime.min.time())
    return day, day + timedelta(days=1), True


def _pin_from_finding(finding: Finding, duty: DutyPeriod | None) -> GanttPin:
    return GanttPin(
        finding_id=finding.finding_id,
        kind=finding.kind.value,
        severity=finding.severity.value,
        rule_id=finding.rule_id,
        rule_name=finding.rule_name,
        citation=finding.citation,
        explanation=finding.explanation,
        offset_ratio=_offset_ratio(finding, duty),
    )


def _offset_ratio(finding: Finding, duty: DutyPeriod | None) -> float:
    if duty is None:
        return 0.5
    start, end, _date_only = _bar_span(duty)
    span = (end - start).total_seconds()
    if span <= 0:
        return 0.5
    moment = finding.event_time
    if moment is None:
        return 1.0
    ratio = (moment - start).total_seconds() / span
    return max(0.0, min(1.0, ratio))


def _target_duty(
    finding: Finding,
    duties_by_id: dict[str, DutyPeriod],
    crew_duties: list[DutyPeriod] | tuple[DutyPeriod, ...],
) -> DutyPeriod | None:
    if finding.duty_id and finding.duty_id in duties_by_id:
        return duties_by_id[finding.duty_id]
    rows = list(crew_duties)
    if finding.flight_id:
        match = [d for d in rows if d.flight_id == finding.flight_id]
        if match:
            return match[0]
    if finding.event_time:
        containing = [
            d
            for d in rows
            if d.duty_start and d.duty_end and d.duty_start <= finding.event_time <= d.duty_end
        ]
        if containing:
            return containing[0]
        dated = [d for d in rows if d.duty_date == finding.event_time.date()]
        if dated:
            return dated[0]
        before = [d for d in rows if d.event_time() <= finding.event_time]
        if before:
            return max(before, key=lambda d: d.event_time())
        after = [d for d in rows if d.event_time() > finding.event_time]
        if after:
            return min(after, key=lambda d: d.event_time())
    return rows[0] if len(rows) == 1 else None


def render_gantt_html(view: GanttView) -> str:
    span = (view.range_end - view.range_start).total_seconds()
    if span <= 0:
        span = 86400.0
    days = max(int(round(span / 86400.0)), 1)
    ticks = []
    cursor = view.range_start
    while cursor < view.range_end:
        ticks.append(
            f'<span class="gantt-tick">{escape(cursor.strftime("%d %b"))}</span>'
        )
        cursor += timedelta(days=1)
    lanes_html = "".join(_lane_html(lane, view.range_start, span) for lane in view.lanes)
    return (
        f'<div class="gantt" style="--gantt-days:{days}">'
        '<div class="gantt-axis">'
        '<span class="gantt-axis-spacer"></span>'
        f'<div class="gantt-ticks">{"".join(ticks)}</div>'
        "</div>"
        f'<div class="gantt-body">{lanes_html}</div>'
        "</div>"
    )


def _lane_html(lane: GanttLane, range_start: datetime, span: float) -> str:
    bars = "".join(_bar_html(bar, range_start, span) for bar in lane.bars)
    unattached = ""
    if lane.unattached:
        chips = "".join(
            f'<span class="gantt-loose gantt-pin--{escape(pin.severity)}">{escape(pin.rule_id)}</span>'
            for pin in lane.unattached
        )
        unattached = f'<div class="gantt-unattached">{chips}</div>'
    return (
        '<div class="gantt-lane">'
        f'<div class="gantt-crew"><span>{escape(lane.crew_name)}</span>'
        f'<em>{escape(lane.crew_id)}</em>{unattached}</div>'
        f'<div class="gantt-track">{bars}</div>'
        "</div>"
    )


def _bar_html(bar: GanttBar, range_start: datetime, span: float) -> str:
    left = max(0.0, (bar.start - range_start).total_seconds() / span * 100.0)
    width = max(0.35, (bar.end - bar.start).total_seconds() / span * 100.0)
    kind = "positioning" if bar.is_positioning else "operating"
    if bar.date_only:
        kind += " date-only"
    pins = "".join(_pin_html(pin) for pin in bar.pins)
    title = f"{bar.label} · {bar.start.strftime('%H:%M')}–{bar.end.strftime('%H:%M')}"
    return (
        f'<div class="gantt-bar gantt-bar--{kind}" style="left:{left:.4f}%;width:{width:.4f}%" '
        f'title="{escape(title, quote=True)}">'
        f'<span class="gantt-bar-label">{escape(bar.label)}</span>'
        f"{pins}</div>"
    )


def _pin_html(pin: GanttPin) -> str:
    left = pin.offset_ratio * 100.0
    return (
        f'<details class="gantt-pin gantt-pin--{escape(pin.severity)} gantt-pin--{escape(pin.kind)}" '
        f'style="left:{left:.4f}%" data-finding-id="{escape(pin.finding_id, quote=True)}">'
        f'<summary aria-label="{escape(pin.rule_id, quote=True)}"></summary>'
        '<div class="gantt-pin-card">'
        f'<span class="gantt-pin-rule">{escape(pin.rule_id)}</span>'
        f'<p>{escape(pin.explanation)}</p>'
        f'<small>{escape(pin.citation)} · {escape(pin.severity)}</small>'
        "</div></details>"
    )

