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
- Time zone changes and WOCL reductions beyond the published daily FDP table cells are not modeled. Crew are treated as acclimatised unless the roster maps another state.
- Daily FDP screening uses the cited basic tables only. Extensions, split duty, in-flight rest, FAA Tables A/C, CASA Table 3.1, and CS-FTL.1 are out of scope.
- Flying for other certificate holders is not in a typical single-operator file (relevant to § 117.23(a)).
- The product is a screening review, not a legal determination.
