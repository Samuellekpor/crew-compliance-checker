from __future__ import annotations

from datetime import time


def _hm(hours: int, minutes: int = 0) -> float:
    return hours + minutes / 60.0


def _minutes_of_day(clock: time) -> int:
    return clock.hour * 60 + clock.minute


def _in_band(minute: int, start_hhmm: int, end_hhmm: int) -> bool:
    start = (start_hhmm // 100) * 60 + (start_hhmm % 100)
    end = (end_hhmm // 100) * 60 + (end_hhmm % 100)
    if start <= end:
        return start <= minute <= end
    return minute >= start or minute <= end


def lookup_easa_table2(start: time, sectors: int) -> tuple[float, str]:
    """ORO.FTL.205(b)(1) Table 2 — acclimatised, no extension. Values are hours."""
    cols = _easa_t2_row(start)
    index = _easa_sector_index(sectors)
    return cols[index], "ORO.FTL.205(b)(1) Table 2"


def lookup_easa_table3(sectors: int) -> tuple[float, str]:
    """ORO.FTL.205(b)(2) Table 3 — unknown acclimatisation."""
    values = (11.0, 10.5, 10.0, 9.5, 9.0, 9.0, 9.0)
    n = min(max(sectors, 1), 8)
    col = 0 if n <= 2 else min(n, 8) - 2
    return values[col], "ORO.FTL.205(b)(2) Table 3"


def lookup_faa_table_b(start: time, segments: int) -> tuple[float, str]:
    """14 CFR Part 117 Table B — unaugmented, acclimated."""
    row = _faa_b_row(start)
    index = min(max(segments, 1), 7) - 1
    return row[index], "14 CFR Part 117 Table B"


def lookup_casa_app2_table21(start: time, sectors: int) -> tuple[float, str]:
    """CAO 48.1 Appendix 2 Table 2.1 — acclimatised FCM."""
    row = _casa_21_row(start)
    if sectors <= 3:
        col = 0
    elif sectors >= 8:
        col = 5
    else:
        col = sectors - 3
    return row[col], "CAO 48.1 Appendix 2 Table 2.1"


def lookup_tc_700_28(start: time, flights: int, avg_flight_hours: float) -> tuple[float, str]:
    """CAR 700.28(2)–(4). Same start-time grid; column set depends on average flight duration."""
    row = _tc_fdp_row(start)
    if avg_flight_hours < 0.5:
        citation = "CAR 700.28(2)"
        if flights <= 11:
            col = 0
        elif flights <= 17:
            col = 1
        else:
            col = 2
    elif avg_flight_hours < 50 / 60:
        citation = "CAR 700.28(3)"
        if flights <= 7:
            col = 0
        elif flights <= 11:
            col = 1
        else:
            col = 2
    else:
        citation = "CAR 700.28(4)"
        if flights <= 4:
            col = 0
        elif flights <= 6:
            col = 1
        else:
            col = 2
    return row[col], citation


def _easa_sector_index(sectors: int) -> int:
    n = min(max(sectors, 1), 10)
    if n <= 2:
        return 0
    return n - 2


def _easa_t2_row(start: time) -> tuple[float, ...]:
    minute = _minutes_of_day(start)
    table: tuple[tuple[int, int, tuple[float, ...]], ...] = (
        (600, 1329, (_hm(13), _hm(12, 30), _hm(12), _hm(11, 30), _hm(11), _hm(10, 30), _hm(10), _hm(9, 30), _hm(9))),
        (1330, 1359, (_hm(12, 45), _hm(12, 15), _hm(11, 45), _hm(11, 15), _hm(10, 45), _hm(10, 15), _hm(9, 45), _hm(9, 15), _hm(9))),
        (1400, 1429, (_hm(12, 30), _hm(12), _hm(11, 30), _hm(11), _hm(10, 30), _hm(10), _hm(9, 30), _hm(9), _hm(9))),
        (1430, 1459, (_hm(12, 15), _hm(11, 45), _hm(11, 15), _hm(10, 45), _hm(10, 15), _hm(9, 45), _hm(9, 15), _hm(9), _hm(9))),
        (1500, 1529, (_hm(12), _hm(11, 30), _hm(11), _hm(10, 30), _hm(10), _hm(9, 30), _hm(9), _hm(9), _hm(9))),
        (1530, 1559, (_hm(11, 45), _hm(11, 15), _hm(10, 45), _hm(10, 15), _hm(9, 45), _hm(9, 15), _hm(9), _hm(9), _hm(9))),
        (1600, 1629, (_hm(11, 30), _hm(11), _hm(10, 30), _hm(10), _hm(9, 30), _hm(9), _hm(9), _hm(9), _hm(9))),
        (1630, 1659, (_hm(11, 15), _hm(10, 45), _hm(10, 15), _hm(9, 45), _hm(9, 15), _hm(9), _hm(9), _hm(9), _hm(9))),
        (1700, 459, (_hm(11), _hm(10, 30), _hm(10), _hm(9, 30), _hm(9), _hm(9), _hm(9), _hm(9), _hm(9))),
        (500, 514, (_hm(12), _hm(11, 30), _hm(11), _hm(10, 30), _hm(10), _hm(9, 30), _hm(9), _hm(9), _hm(9))),
        (515, 529, (_hm(12, 15), _hm(11, 45), _hm(11, 15), _hm(10, 45), _hm(10, 15), _hm(9, 45), _hm(9, 15), _hm(9), _hm(9))),
        (530, 544, (_hm(12, 30), _hm(12), _hm(11, 30), _hm(11), _hm(10, 30), _hm(10), _hm(9, 30), _hm(9), _hm(9))),
        (545, 559, (_hm(12, 45), _hm(12, 15), _hm(11, 45), _hm(11, 15), _hm(10, 45), _hm(10, 15), _hm(9, 45), _hm(9, 15), _hm(9))),
    )
    for start_hhmm, end_hhmm, row in table:
        if _in_band(minute, start_hhmm, end_hhmm):
            return row
    return table[8][2]


def _faa_b_row(start: time) -> tuple[float, ...]:
    minute = _minutes_of_day(start)
    table: tuple[tuple[int, int, tuple[float, ...]], ...] = (
        (0, 359, (9, 9, 9, 9, 9, 9, 9)),
        (400, 459, (10, 10, 10, 10, 9, 9, 9)),
        (500, 559, (12, 12, 12, 12, 11.5, 11, 10.5)),
        (600, 659, (13, 13, 12, 12, 11.5, 11, 10.5)),
        (700, 1159, (14, 14, 13, 13, 12.5, 12, 11.5)),
        (1200, 1259, (13, 13, 13, 13, 12.5, 12, 11.5)),
        (1300, 1659, (12, 12, 12, 12, 11.5, 11, 10.5)),
        (1700, 2159, (12, 12, 11, 11, 10, 9, 9)),
        (2200, 2259, (11, 11, 10, 10, 9, 9, 9)),
        (2300, 2359, (10, 10, 10, 9, 9, 9, 9)),
    )
    for start_hhmm, end_hhmm, row in table:
        if _in_band(minute, start_hhmm, end_hhmm):
            return row
    return table[0][2]


def _casa_21_row(start: time) -> tuple[float, ...]:
    minute = _minutes_of_day(start)
    table: tuple[tuple[int, int, tuple[float, ...]], ...] = (
        (0, 459, (10, 9.5, 9, 8.5, 8, 7.5)),
        (500, 559, (11, 10.5, 10, 9.5, 9, 8.5)),
        (600, 659, (12, 11.5, 11, 10.5, 10, 9.5)),
        (700, 1259, (13, 12.5, 12, 11.5, 11, 10.5)),
        (1300, 1359, (12, 11.5, 11, 10.5, 10, 9.5)),
        (1400, 1459, (11, 10.5, 10, 9.5, 9, 8.5)),
        (1500, 2359, (10, 9.5, 9, 8.5, 8, 7.5)),
    )
    for start_hhmm, end_hhmm, row in table:
        if _in_band(minute, start_hhmm, end_hhmm):
            return row
    return table[0][2]


def _tc_fdp_row(start: time) -> tuple[float, ...]:
    minute = _minutes_of_day(start)
    table: tuple[tuple[int, int, tuple[float, ...]], ...] = (
        (0, 359, (9, 9, 9)),
        (400, 459, (10, 9, 9)),
        (500, 559, (11, 10, 9)),
        (600, 659, (12, 11, 10)),
        (700, 1259, (13, 12, 11)),
        (1300, 1659, (12.5, 11.5, 10.5)),
        (1700, 2159, (12, 11, 10)),
        (2200, 2259, (11, 10, 9)),
        (2300, 2359, (10, 9, 9)),
    )
    for start_hhmm, end_hhmm, row in table:
        if _in_band(minute, start_hhmm, end_hhmm):
            return row
    return (9.0, 9.0, 9.0)
