# Crew Compliance Checker

Simple Streamlit app that totals crew hours over a 28-day window and flags Captains and First Officers over 100 hours as an EASA violation.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Upload a CSV with columns `Date`, `Flight`, `Captain`, and `Hours`. A `First Officer` column is optional.

Use `sample_flights.csv` for a demo: Jane Hale (Captain) and Tom Chen (First Officer) exceed 100 hours in the latest 28 days; Mark Ortiz and Priya Shah do not.
