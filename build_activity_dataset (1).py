"""
India Time Use Survey 1998-99 (NSSO Schedule TUS 1.0)
Add the time diary to the person-level dataset.

Run build_person_dataset.py first: this script uses its output.

Produces two files:

  1. activity_episodes_TUS_1998.csv.gz
     The most granular view possible. One row per activity episode,
     3.17 million of them, with the diary fields decoded and a few key
     person attributes attached. Join on person_id for the rest.

  2. person_activity_summary_TUS_1998.csv
     One row per person, minutes spent in each of the nine activity
     divisions on their normal day, with full demographics attached.

The episode file is read in chunks so that it never has to fit in
memory all at once.
"""

import zipfile
from pathlib import Path

import pandas as pd

DATA_DIR = Path("data")
OUT_DIR = Path("output")
ZIP_PATH = DATA_DIR / "TUS_1998_CSV.zip"

ACTIVITY_FILE = (
    "TUS_1998_CSV/Block-3-Item-5-Particulars-activity-selected-days-records.csv"
)
PERSON_FILE = OUT_DIR / "person_level_TUS_1998.csv"

EPISODE_OUT = OUT_DIR / "activity_episodes_TUS_1998.csv.gz"
SUMMARY_OUT = OUT_DIR / "person_activity_summary_TUS_1998.csv"

CHUNK = 250_000

# ---------------------------------------------------------------------
# Code books for the diary, taken from the value labels in the SPSS
# version of this same block.
# ---------------------------------------------------------------------
DAY_TYPE = {"1": "Normal", "2": "Weekly variant", "3": "Abnormal"}

# The diary day runs 4 am to 4 am, not midnight to midnight.
HOUR_SLOT = {
    "01": "04-05", "02": "05-06", "03": "06-07", "04": "07-08",
    "05": "08-09", "06": "09-10", "07": "10-11", "08": "11-12",
    "09": "12-13", "10": "13-14", "11": "14-15", "12": "15-16",
    "13": "16-17", "14": "17-18", "15": "18-19", "16": "19-20",
    "17": "20-21", "18": "21-22", "19": "22-23", "20": "23-24",
    "21": "00-01", "22": "01-02", "23": "02-03", "24": "03-04",
}

SIMULTANEOUS = {"0": "Not recorded", "1": "Yes", "2": "No"}

WITHIN_OUTSIDE = {"1": "Within household", "2": "Outside household"}

PAYMENT = {
    "1": "Paid or payable in cash",
    "2": "Paid or payable in kind",
    "3": "Unpaid",
    "9": "Others",
}

# ---------------------------------------------------------------------
# Activity classification.
#
# The survey used a three-digit code. The files contain the codes but
# not their descriptions, so only the nine major divisions (the first
# digit) are labelled here, following the classification used for the
# Indian TUS. The full three-digit code is kept untouched in
# activity_code so it can be matched against the survey manual later.
# ---------------------------------------------------------------------
DIVISION = {
    "1": "1 Primary production",
    "2": "2 Secondary production",
    "3": "3 Trade, business and services",
    "4": "4 Household maintenance, management and shopping",
    "5": "5 Care of children, sick, elderly and disabled",
    "6": "6 Community services and help to other households",
    "7": "7 Learning",
    "8": "8 Social, cultural and recreational activity",
    "9": "9 Personal care and self-maintenance",
}

# Divisions 1-3 are inside the System of National Accounts production
# boundary, 4-6 are unpaid work outside it, 7-9 are not production.
SNA_GROUP = {
    "1": "SNA production",
    "2": "SNA production",
    "3": "SNA production",
    "4": "Extended SNA (unpaid work)",
    "5": "Extended SNA (unpaid work)",
    "6": "Extended SNA (unpaid work)",
    "7": "Non-SNA (personal)",
    "8": "Non-SNA (personal)",
    "9": "Non-SNA (personal)",
}

USE_COLS = [
    "Key_membno", "Key_hhold", "membno", "age",
    "B3_c0a", "B3_c0b", "B3_c0c",
    "B3_q5_c1", "B3_q5_c2", "B3_q5_c3", "B3_q5_c5",
    "B3_q5_c6", "B3_q5_c7", "B3_q5_c8",
    "wgt_combined_st", "wgt_combined_dt",
]

RENAME = {
    "Key_membno": "person_id",
    "Key_hhold": "household_id",
    "membno": "member_no",
    "B3_c0a": "day_type_code",
    "B3_c0b": "hour_slot_code",
    "B3_c0c": "activity_serial",
    "B3_q5_c1": "hour_from",
    "B3_q5_c2": "hour_to",
    "B3_q5_c3": "simultaneous_code",
    "B3_q5_c5": "minutes",
    "B3_q5_c6": "location_code",
    "B3_q5_c7": "activity_code",
    "B3_q5_c8": "payment_code",
    "wgt_combined_st": "weight_state",
    "wgt_combined_dt": "weight_district",
}


def decode(chunk: pd.DataFrame, people: pd.DataFrame) -> pd.DataFrame:
    """Rename, decode and attach person attributes to one chunk."""
    df = chunk[USE_COLS].rename(columns=RENAME)

    df["day_type"] = df["day_type_code"].map(DAY_TYPE)
    df["hour_slot"] = df["hour_slot_code"].map(HOUR_SLOT)
    df["simultaneous_activity"] = df["simultaneous_code"].map(SIMULTANEOUS)
    df["location"] = df["location_code"].map(WITHIN_OUTSIDE)
    df["payment"] = df["payment_code"].map(PAYMENT)

    first_digit = df["activity_code"].str[0]
    df["activity_division"] = first_digit.map(DIVISION)
    df["sna_group"] = first_digit.map(SNA_GROUP)

    df["minutes"] = pd.to_numeric(df["minutes"], errors="coerce")
    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    for col in ("weight_state", "weight_district"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # A few person attributes travel with each episode so the file is
    # usable on its own. Everything else stays one join away.
    df = df.merge(people, on="person_id", how="left")

    return df[
        [
            "person_id", "household_id", "member_no",
            "sex", "age", "state", "district_code", "sector",
            "day_type", "hour_slot", "activity_serial",
            "hour_from", "hour_to", "minutes",
            "activity_code", "activity_division", "sna_group",
            "simultaneous_activity", "location", "payment",
            "weight_state", "weight_district",
        ]
    ]


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)

    people = pd.read_csv(
        PERSON_FILE,
        dtype=str,
        usecols=["person_id", "sex", "state", "district_code", "sector"],
    ).drop_duplicates("person_id")
    print(f"person records loaded: {len(people):,}")

    if EPISODE_OUT.exists():
        EPISODE_OUT.unlink()

    summaries = []
    total_rows = 0
    first = True

    with zipfile.ZipFile(ZIP_PATH) as z:
        with z.open(ACTIVITY_FILE) as f:
            reader = pd.read_csv(f, dtype=str, chunksize=CHUNK)
            for i, chunk in enumerate(reader, start=1):
                df = decode(chunk, people)

                df.to_csv(
                    EPISODE_OUT,
                    mode="w" if first else "a",
                    header=first,
                    index=False,
                    compression="gzip",
                )
                first = False
                total_rows += len(df)

                # Running total of minutes by person, day type and division.
                summaries.append(
                    df.groupby(
                        ["person_id", "day_type", "activity_division"],
                        observed=True,
                    )["minutes"]
                    .sum()
                    .reset_index()
                )

                print(f"  chunk {i:>3}: {total_rows:>10,} episodes written")

    print(f"\nepisodes written: {total_rows:,} -> {EPISODE_OUT}")

    # -----------------------------------------------------------------
    # Collapse the running totals into one row per person, day type and
    # division, then reshape so each division is a column.
    # -----------------------------------------------------------------
    long = (
        pd.concat(summaries, ignore_index=True)
        .groupby(["person_id", "day_type", "activity_division"], observed=True)[
            "minutes"
        ]
        .sum()
        .reset_index()
    )

    long_out = OUT_DIR / "person_day_division_minutes.csv"
    long.to_csv(long_out, index=False)
    print(f"long summary: {len(long):,} rows -> {long_out}")

    normal = long[long["day_type"] == "Normal"]
    wide = (
        normal.pivot(
            index="person_id", columns="activity_division", values="minutes"
        )
        .fillna(0)
        .reset_index()
    )
    wide.columns.name = None
    wide["total_minutes_recorded"] = wide.drop(columns="person_id").sum(axis=1)

    full = pd.read_csv(PERSON_FILE, dtype=str)
    numeric = [
        "age", "household_size", "land_owned_acres", "land_possessed_acres",
        "monthly_hh_expenditure_rs", "monthly_percapita_expenditure_rs",
        "disabled_persons_in_hh", "weight_state", "weight_district",
    ]
    for col in numeric:
        full[col] = pd.to_numeric(full[col], errors="coerce")

    summary = full.merge(wide, on="person_id", how="inner")
    summary.to_csv(SUMMARY_OUT, index=False)
    print(f"person summary: {len(summary):,} rows -> {SUMMARY_OUT}")

    # -----------------------------------------------------------------
    # Sanity checks.
    # -----------------------------------------------------------------
    print("\nMinutes recorded on a normal day (should sit near 1440):")
    print(summary["total_minutes_recorded"].describe())

    div_cols = [c for c in summary.columns if c[0].isdigit()]
    print("\nAverage minutes per normal day by sex (unweighted):")
    print(summary.groupby("sex")[div_cols].mean().round(1).T)


if __name__ == "__main__":
    main()
