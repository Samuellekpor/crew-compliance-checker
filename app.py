from __future__ import annotations

from datetime import timedelta

import pandas as pd
import streamlit as st

WINDOW_DAYS = 28
HOUR_LIMIT = 100.0
REQUIRED_COLUMNS = ("Date", "Flight", "Captain", "Hours")
FO_COLUMN_ALIASES = (
    "First Officer",
    "First officer",
    "FirstOfficer",
    "FO",
    "F/O",
)


def find_fo_column(columns: pd.Index) -> str | None:
    lookup = {str(col).strip().lower(): col for col in columns}
    for alias in FO_COLUMN_ALIASES:
        match = lookup.get(alias.lower())
        if match is not None:
            return match
    return None


def load_flights(csv_file) -> pd.DataFrame:
    df = pd.read_csv(csv_file)
    df.columns = [str(col).strip() for col in df.columns]
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(missing)}")

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=False)
    df["Hours"] = pd.to_numeric(df["Hours"], errors="coerce")
    df["Captain"] = df["Captain"].astype(str).str.strip()
    df["Flight"] = df["Flight"].astype(str).str.strip()

    fo_col = find_fo_column(df.columns)
    if fo_col:
        df["First Officer"] = df[fo_col].astype(str).str.strip()
        df.loc[df["First Officer"].isin(["", "nan", "None"]), "First Officer"] = pd.NA

    return df


def invalid_row_mask(df: pd.DataFrame) -> pd.Series:
    return df["Date"].isna() | df["Hours"].isna() | (df["Hours"] < 0) | (df["Captain"] == "")


def recent_window_bounds(dates: pd.Series) -> tuple[pd.Timestamp, pd.Timestamp]:
    end = dates.max().normalize()
    start = end - timedelta(days=WINDOW_DAYS - 1)
    return start, end


def crew_duty_rows(flights: pd.DataFrame) -> pd.DataFrame:
    captains = flights.assign(
        Name=flights["Captain"],
        Role="Captain",
    )[["Date", "Flight", "Hours", "Name", "Role"]]

    if "First Officer" not in flights.columns:
        return captains

    officers = flights.dropna(subset=["First Officer"]).assign(
        Name=lambda x: x["First Officer"],
        Role="First Officer",
    )[["Date", "Flight", "Hours", "Name", "Role"]]
    return pd.concat([captains, officers], ignore_index=True)


def summarize_crew(duties: pd.DataFrame, window_start: pd.Timestamp, window_end: pd.Timestamp) -> pd.DataFrame:
    in_window = duties[(duties["Date"] >= window_start) & (duties["Date"] <= window_end)]
    summary = (
        in_window.groupby(["Name", "Role"], dropna=False)["Hours"]
        .sum()
        .reset_index(name="Hours (28 days)")
    )
    summary["Hours (28 days)"] = summary["Hours (28 days)"].round(1)
    summary["Status"] = summary.apply(violation_status, axis=1)
    return summary.sort_values(
        by=["Status", "Hours (28 days)", "Name"],
        ascending=[False, False, True],
    ).reset_index(drop=True)


def violation_status(row: pd.Series) -> str:
    if row["Hours (28 days)"] > HOUR_LIMIT:
        return "EASA VIOLATION"
    return "OK"


def style_results(df: pd.DataFrame):
    def highlight(row: pd.Series) -> list[str]:
        if row["Status"] == "EASA VIOLATION":
            return ["color: red; font-weight: 600"] * len(row)
        return [""] * len(row)

    return df.style.apply(highlight, axis=1).format({"Hours (28 days)": "{:.1f}"})


st.set_page_config(page_title="Crew Compliance Checker", layout="wide")
st.title("Crew Compliance Checker")
st.write(
    "Upload a CSV with columns **Date**, **Flight**, **Captain**, and **Hours**. "
    "An optional **First Officer** column is included when present. "
    "The app totals hours in the most recent 28-day window (inclusive of the latest date in the file) "
    f"and flags any Captain or First Officer over **{int(HOUR_LIMIT)} hours** as **EASA VIOLATION**."
)

uploaded = st.file_uploader("Upload crew flight CSV", type=["csv"])

if uploaded is None:
    st.info("No file uploaded yet. You can try `sample_flights.csv` in this project.")
    st.stop()

try:
    flights = load_flights(uploaded)
except ValueError as exc:
    st.error(str(exc))
    st.stop()
except Exception:
    st.error("Could not read that CSV. Check the file encoding and column names.")
    st.stop()

bad_rows = flights[invalid_row_mask(flights)]
valid = flights[~invalid_row_mask(flights)].copy()

if not bad_rows.empty:
    st.warning(f"Skipped {len(bad_rows)} row(s) with missing/invalid Date, Hours, or Captain.")
    with st.expander("Skipped rows"):
        st.dataframe(bad_rows, use_container_width=True)

if valid.empty:
    st.error("No valid flight rows to check.")
    st.stop()

window_start, window_end = recent_window_bounds(valid["Date"])
duties = crew_duty_rows(valid)
results = summarize_crew(duties, window_start, window_end)

st.subheader("28-day hours")
st.caption(
    f"Window: {window_start.date().isoformat()} to {window_end.date().isoformat()} "
    f"({WINDOW_DAYS} days, inclusive)."
)
st.dataframe(style_results(results), use_container_width=True, hide_index=True)

csv_bytes = results.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download results CSV",
    data=csv_bytes,
    file_name="crew_compliance_results.csv",
    mime="text/csv",
)
