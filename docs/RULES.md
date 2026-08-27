# Implemented V1 rules

Limits are taken from the cited provisions. A value **equal to** the published limit is treated as within the limit; only values **above** a maximum or **below** a minimum rest requirement are flagged as potential issues.

## EASA (`easa-ftl-v1` 1.0.0)

| Rule ID | Citation | What is evaluated |
|---|---|---|
| EASA-FTL-210-B1 | ORO.FTL.210(b)(1) | Operating flight time > 100 h in any 28 consecutive calendar days |
| EASA-FTL-210-B2 | ORO.FTL.210(b)(2) | Operating flight time > 900 h in a calendar year |
| EASA-FTL-210-B3 | ORO.FTL.210(b)(3) | Operating flight time > 1000 h in any 12 consecutive calendar months |
| EASA-FTL-210-A1 | ORO.FTL.210(a)(1) | Duty hours > 60 h in any 7 consecutive calendar days |
| EASA-FTL-210-A2 | ORO.FTL.210(a)(2) | Duty hours > 110 h in any 14 consecutive calendar days |
| EASA-FTL-210-A3 | ORO.FTL.210(a)(3) | Duty hours > 190 h in any 28 consecutive calendar days |
| EASA-FTL-235-MINREST | ORO.FTL.235(a)(1), (b) | Rest before next duty ≥ max(preceding duty, 12 h home / 10 h away) |
| EASA-FTL-235-D-SCREEN | ORO.FTL.235(d) **partial** | 36 h rest with ≤ 168 h from end of one such rest to start of the next |

**Not implemented:** ORO.FTL.205 / CS-FTL.1 FDP tables, WOCL, sector counts, augmented FDP, split duty, standby, reserve, reduced rest, commander’s discretion, 2 local nights inside RERRP, operator-specific FTSS.

## FAA (`faa-117-v1` 1.0.0)

Applicability: 14 CFR § 117.1 (Part 121 passenger-carrying, and specified 91 flying on behalf of that holder). Not Part 135. Not all-cargo 121 Subparts Q/R/S.

| Rule ID | Citation | What is evaluated |
|---|---|---|
| FAA-117-23-B1 | § 117.23(b)(1) | Flight time > 100 h in any 672 consecutive hours |
| FAA-117-23-B2 | § 117.23(b)(2) | Flight time > 1000 h in any 365 consecutive calendar days |
| FAA-117-23-C1 | § 117.23(c)(1) | Duty-span FDP proxy > 60 h in any 168 consecutive hours |
| FAA-117-23-C2 | § 117.23(c)(2) | Duty-span FDP proxy > 190 h in any 672 consecutive hours |
| FAA-117-25-E | § 117.25(e) | < 10 consecutive hours free of duty immediately before duty start |
| FAA-117-25-B | § 117.25(b) | No 30 consecutive hours free of duty in the 168 hours before duty start |

**Not implemented:** Tables A/B/C, § 117.11, § 117.13/17, split duty, reserve, extensions, § 117.25(c)(d)(f)(g), § 117.27, 8-hour sleep opportunity.
