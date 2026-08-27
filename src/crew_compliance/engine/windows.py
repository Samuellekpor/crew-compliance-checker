from __future__ import annotations

from datetime import datetime, timedelta


def overlap_hours(
    start: datetime,
    end: datetime,
    window_start: datetime,
    window_end: datetime,
) -> float:
    latest_start = max(start, window_start)
    earliest_end = min(end, window_end)
    if earliest_end <= latest_start:
        return 0.0
    return (earliest_end - latest_start).total_seconds() / 3600.0


def merge_intervals(intervals: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    if not intervals:
        return []
    ordered = sorted(intervals)
    merged = [ordered[0]]
    for start, end in ordered[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def longest_free_hours(
    duties: list[tuple[datetime, datetime]],
    window_start: datetime,
    window_end: datetime,
) -> float:
    clipped: list[tuple[datetime, datetime]] = []
    for start, end in duties:
        if end <= window_start or start >= window_end:
            continue
        clipped.append((max(start, window_start), min(end, window_end)))
    merged = merge_intervals(clipped)
    cursor = window_start
    longest = 0.0
    for start, end in merged:
        longest = max(longest, (start - cursor).total_seconds() / 3600.0)
        cursor = end
    longest = max(longest, (window_end - cursor).total_seconds() / 3600.0)
    return longest


def add_hours(moment: datetime, hours: float) -> datetime:
    return moment + timedelta(hours=hours)