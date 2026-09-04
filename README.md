# Crew Compliance Checker

Local Streamlit app that screens a crew roster for **potential** flight-time, duty-time, rest, and credential issues under a selected regulatory framework.

**Upload a crew roster. Detect potential crew FTL compliance issues in seconds.**

This is a screening and review tool for small airlines, charter operators, aviation consultants, and crew planning teams. It is **not** an approved compliance-monitoring system, not a regulator, not legal advice, and not a guarantee that a roster is legally compliant.

## Problem

Crew planners need a fast way to see whether a spreadsheet roster *might* conflict with high-value FTL limits before a specialist review. Manual checks are slow; a generic “ask an LLM if this is legal” approach is not acceptable.

## Key features (V2)

- CSV and XLSX roster upload with flexible column mapping (headers are never hardcoded)
- Optional opening-balances file so rolling-window checks can include hours accrued before the roster starts — missing rows are **insufficient data**, never assumed zero
- Optional license / medical / qualification expiry file, screened in the same findings list (30 / 60 / 90-day look-ahead; higher severity if the crew member is rostered to fly)
- Downloadable Excel templates for opening balances and credentials
- Normalized internal roster model (rules never depend on spreadsheet headers)
- Deterministic compliance engine (no LLM deciding legality)
- EASA, FAA Part 117, UK CAA, Transport Canada, and CASA CAO 48.1 Appendix 2 screening sets (partial — see `docs/RULES.md`)
- Operator overlay of published numeric limits for this run only (defaults remain the cited values; overlays are recorded in evidence and exports)
- Structured findings with citations, evidence, assumptions, and limitations
- Filters and finding detail
- CSV, Excel, and branded PDF report export

Pricing ($29/month or $290/year) is a product requirement only. Payment processing is not implemented (see V3).

## Architecture

```
Upload → validate → normalize → deterministic ruleset (optional parameter overlay) → structured findings → Streamlit UI / export
```

The engine lives in `src/crew_compliance/` and does not import Streamlit. The UI is `app/streamlit_app.py`.

Rules are developer-defined objects with frozen published parameters. V2 overlays operator-entered numeric values onto the same `Rule` protocol without rewriting the engine. Published EASA/FAA calculations are unchanged unless the operator overlays a limit.

## Technology

Python, Streamlit, pandas, openpyxl, reportlab, pytest.

## Supported regulatory frameworks

| Framework | V2 status |
|---|---|
| EASA Air Ops Subpart FTL | Implemented (partial screening set) |
| FAA 14 CFR Part 117 | Implemented (partial screening set; passenger Part 121 applicability) |
| UK CAA assimilated Air Ops FTL + CAWTR reg. 9 | Implemented (partial screening set) |
| Transport Canada CARs Subpart 700 | Implemented (partial screening set) |
| CASA / CAO 48.1 Appendix 2 | Implemented (partial screening set; multi-pilot except flight training) |
| ICAO | Not an enforceable violation framework in this product |

## Currently implemented rules

See `docs/RULES.md`. Do not assume FDP tables, standby, reserve, augmented crews, or operator-specific schemes are checked.

## Known limitations

- Naive operator-local times (no timezone conversion)
- Incomplete roster lookback produces **insufficient data** notices, not a pass — unless a matching opening-balance row is supplied
- Duty span may be used as an FDP or hours-of-work proxy when true FDP / working time is not in the file
- Exceptions, reduced rest, commander’s discretion, and full CS-FTL.1 / Part 117 / CAO 48.1 / CAR 700.28 tables are not modeled
- One operator file cannot prove “all flying for any certificate holder” (14 CFR § 117.23(a) and similar extra-operator accumulation rules)

## Local setup

Python 3.12 recommended (3.9+ locally). Community Cloud should use **3.12**, not 3.14.

```bash
cd crew-compliance-checker
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"
```

## Run the Streamlit application

```bash
streamlit run app/streamlit_app.py
```

## Deploy on Streamlit Community Cloud

The GitHub repository is **private**. Community Cloud can deploy it only after you connect GitHub and grant Streamlit access to private repositories.

1. Open [Deploy on Community Cloud](https://share.streamlit.io/deploy?repository=Samuellekpor/crew-compliance-checker&branch=main&mainModule=streamlit_app.py) and sign in with GitHub.
2. If the repo does not appear, open **Settings → Linked accounts** in Community Cloud and authorize private-repo access.
3. Confirm:
   - Repository: `Samuellekpor/crew-compliance-checker`
   - Branch: `main`
   - Main file path: `streamlit_app.py`
   - **Advanced → Python version: 3.12** (do not leave the default if it is 3.13/3.14)
4. Deploy. The public URL will look like `https://<name>.streamlit.app`.

If an existing app is stuck installing packages, reboot or recreate it after this Python 3.12 setting. `.python-version` and `runtime.txt` in the repo request 3.12; Community Cloud still requires the Advanced setting to match.

**Operational caution:** Community Cloud apps are reachable on the public internet. Roster files are processed on Streamlit’s infrastructure. Do not upload confidential airline rosters to the hosted app. Keep sensitive screening on a local `streamlit run`.

Use `samples/sample_roster.csv` for a synthetic demo. Do not upload confidential airline rosters to shared machines or logs.

## Run tests

```bash
pytest
```

## Regulatory disclaimer

Findings are labeled as potential compliance issues or insufficient-data notices that **require review**. The software does not determine legality and must not be used as the sole basis for releasing a roster.

## Roadmap

- **V1:** local EASA/FAA screening MVP
- **V2:** this release — additional jurisdictions, operator parameter overlay, opening balances, credential expiry, PDF export
- **V3:** SaaS, accounts, subscriptions
- **V4:** APIs and scheduling-system integrations
