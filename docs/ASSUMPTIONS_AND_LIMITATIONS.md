# Assumptions and limitations (V2)

## Assumptions

- Roster datetimes are naive operator-local values. Overnight duties that end earlier on the clock than they start are wrapped by one calendar day.
- “Consecutive days” for EASA ORO.FTL.210 means calendar dates.
- Operating flight time is taken from `flight_hours` or flight start/end. Positioning is duty, not flight time.
- Home vs away rest floors use `home_base` vs `start_location`. If either is missing, the 10 h / 12 h floor is not guessed.
- Opening-balance rows, when uploaded, are added only to incomplete rolling windows. A missing crew/window row is never treated as zero.
- Operator parameter overlays apply only to the current analysis run and are recorded in finding evidence.

## Limitations

- Incomplete lookback is never treated as a pass.
- Time zone changes, acclimatisation, and WOCL are not modeled.
- Full EASA FTSS, full Part 117 tables, CAR 700.28 FDP tables, and CAO 48.1 Appendix 2 FDP tables are out of scope.
- Flying for other certificate holders is not in a typical single-operator file (relevant to § 117.23(a)).
- The product is a screening review, not a legal determination.
