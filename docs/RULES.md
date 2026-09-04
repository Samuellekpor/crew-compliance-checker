# Implemented screening rules

Limits are taken from the cited provisions. A value **equal to** the published limit is treated as within the limit; only values **above** a maximum or **below** a minimum rest requirement are flagged as potential issues.

Operator overlays may replace a numeric parameter for a single run. The published default is unchanged unless an overlay is supplied.

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

## UK CAA (`uk-ftl-v1` 1.0.0)

Assimilated UK Air Ops Subpart FTL (same numeric ORO.FTL.210 / 235 screens as EASA, cited as UK CAA) plus Civil Aviation (Working Time) Regulations 2004 reg. 9.

| Rule ID | Citation | What is evaluated |
|---|---|---|
| UK-FTL-210-B1 | UK ORO.FTL.210(b)(1) | Operating flight time > 100 h in any 28 consecutive calendar days |
| UK-FTL-210-B2 | UK ORO.FTL.210(b)(2) | Operating flight time > 900 h in a calendar year |
| UK-FTL-210-B3 | UK ORO.FTL.210(b)(3) | Operating flight time > 1000 h in any 12 consecutive calendar months |
| UK-FTL-210-A1 | UK ORO.FTL.210(a)(1) | Duty hours > 60 h in any 7 consecutive calendar days |
| UK-FTL-210-A2 | UK ORO.FTL.210(a)(2) | Duty hours > 110 h in any 14 consecutive calendar days |
| UK-FTL-210-A3 | UK ORO.FTL.210(a)(3) | Duty hours > 190 h in any 28 consecutive calendar days |
| UK-FTL-235-MINREST | UK ORO.FTL.235(a)(1), (b) | Rest before next duty ≥ max(preceding duty, 12 h home / 10 h away) |
| UK-FTL-235-D-SCREEN | UK ORO.FTL.235(d) **partial** | 36 h rest with ≤ 168 h from end of one such rest to start of the next |
| UK-CAWTR-9-A | SI 2004/756 reg. 9(a) | Operating flight time > 900 h in any 12 consecutive calendar months (proxy for the statutory previous-month-end lookback) |
| UK-CAWTR-9-B | SI 2004/756 reg. 9(b) | Duty hours > 2000 h in any 12 consecutive calendar months (working-time proxy; standby 9A not applied) |

**Not implemented:** CAP 371 FTLS schemes, CS-FTL.1 tables, ANO 2016 art. 177 as a separate rule (100 h / 28 days is covered via UK-FTL-210-B1).

## Transport Canada (`tc-cars-700-v1` 1.0.0)

| Rule ID | Citation | What is evaluated |
|---|---|---|
| TC-700-27-A | CAR 700.27(1)(a) | Flight time > 112 h in any 28 consecutive days |
| TC-700-27-B | CAR 700.27(1)(b) | Flight time > 300 h in any 90 consecutive days |
| TC-700-27-C | CAR 700.27(1)(c) | Flight time > 1000 h in any 365 consecutive days |
| TC-700-29-B | CAR 700.29(1)(b) | Duty hours (hours-of-work proxy) > 192 h in any 28 consecutive days |
| TC-700-29-C | CAR 700.29(1)(c) | Duty hours > 60 h in any 7 consecutive days |
| TC-700-29-A | CAR 700.29(1)(a) | Duty hours > 2200 h in any 365 consecutive days |
| TC-700-40 | CAR 700.40(1) | Rest before next duty < 12 h home / 10 h away |

**Not implemented:** 700.28 FDP tables, 700.27(1)(d) single-pilot 8/24, 700.29(1)(d) 70 h option, 700.103 medevac, FRMS, reserve/standby counting.

## CASA (`casa-48-1-a2-v1` 1.0.0)

Applicability: CAO 48.1 Instrument 2019 **Appendix 2** (multi-pilot operations except flight training).

| Rule ID | Citation | What is evaluated |
|---|---|---|
| CASA-48-A2-11-1 | App. 2 cl 11.1 | Flight time > 100 h in any consecutive 28-day period |
| CASA-48-A2-11-2 | App. 2 cl 11.2 | Flight time > 1000 h in any consecutive 365-day period |
| CASA-48-A2-12-1 | App. 2 cl 12.1 | Duty hours > 60 h in any 168 consecutive hours |
| CASA-48-A2-12-2 | App. 2 cl 12.2 | Duty hours > 100 h in any 336 consecutive hours |
| CASA-48-A2-1 | App. 2 cl 1.1–1.2 | Off-duty before next duty < 12 h home / 10 h away (sleep-opportunity window proxy) |

**Not implemented:** Appendix 2 Tables 2.1/3.1, other appendices, FRMS, split duty, late-FDP counts, 8-hour sleep opportunity inside the off-duty window.

