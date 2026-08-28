# Crew Compliance Checker

Local Streamlit MVP that screens a crew roster for **potential** flight-time, duty-time, and rest issues under a selected regulatory framework.

**Upload a crew roster. Detect potential crew FTL compliance issues in seconds.**

This is a screening and review tool for small airlines, charter operators, aviation consultants, and crew planning teams. It is **not** an approved compliance-monitoring system, not a regulator, not legal advice, and not a guarantee that a roster is legally compliant.

## Problem

Crew planners need a fast way to see whether a spreadsheet roster *might* conflict with high-value FTL limits before a specialist review. Manual checks are slow; a generic “ask an LLM if this is legal” approach is not acceptable.

## Key features (V1)

- CSV and XLSX upload with column mapping
- Normalized internal roster model (rules never depend on spreadsheet headers)
- Deterministic compliance engine (no LLM deciding legality)
- EASA Subpart FTL screening rules (see below)
- FAA 14 CFR Part 117 screening rules (passenger-carrying Part 121 context)
- Structured findings with citations, evidence, assumptions, and limitations
- Filters and finding detail
- CSV and Excel report export

PDF export is deferred.

Pricing ($29/month or $290/year) is a product requirement only. Payment processing is not implemented.

## Architecture

```
Upload → validate → normalize → deterministic ruleset → structured findings → Streamlit UI / export
```

The engine lives in `src/crew_compliance/` and does not import Streamlit. The UI is `app/streamlit_app.py`.

V1 rules are developer-defined objects with frozen parameters registered in a ruleset. V2 can overlay user parameters onto the same `Rule` protocol without rewriting the engine.

## Technology

Python, Streamlit, pandas, openpyxl, pytest.

## Supported regulatory frameworks

| Framework | V1 status |
|---|---|
| EASA Air Ops Subpart FTL | Implemented (partial screening set) |
| FAA 14 CFR Part 117 | Implemented (partial screening set; passenger Part 121 applicability) |
| UK CAA | Not implemented |
| Transport Canada | Not implemented |
| CASA / CAO 48.1 | Not implemented |
| ICAO | Not an enforceable violation framework in this product |

## Currently implemented rules

See `docs/RULES.md`. Do not assume FDP tables, standby, reserve, augmented crews, or operator-specific schemes are checked.

## Known limitations

- Naive operator-local times (no timezone conversion)
- Incomplete roster lookback produces **insufficient data** notices, not a pass
- Duty span may be used as an FDP proxy when true FDP is not in the file
- Exceptions, reduced rest, commander’s discretion, and full CS-FTL.1 / Part 117 tables are not modeled
- One operator file cannot prove “all flying for any certificate holder” (14 CFR § 117.23(a))

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

- **V1:** this local screening MVP
- **V2:** user-configurable rules and additional jurisdictions
- **V3:** SaaS, accounts, subscriptions
- **V4:** APIs and scheduling-system integrations
