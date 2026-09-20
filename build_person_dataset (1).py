"""
India Time Use Survey 1998-99 (NSSO Schedule TUS 1.0)
Build a person-level dataset.

Takes the raw survey zips and produces one row per household member,
combining that person's own demographics (Block 2) with the
characteristics of the household they live in (Blocks 0 and 1).

Input : TUS_1998_CSV.zip  (expected in the folder given by DATA_DIR)
Output: person_level_TUS_1998.csv
"""

import zipfile
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------
# Where things live. Change DATA_DIR if your zip sits somewhere else.
# ---------------------------------------------------------------------
DATA_DIR = Path("data")
OUT_DIR = Path("output")
ZIP_PATH = DATA_DIR / "TUS_1998_CSV.zip"

HH_FILE = "TUS_1998_CSV/Block-0-1-Identification-Household-Characteristics-records.csv"
MEMBER_FILE = "TUS_1998_CSV/Block-2-Particulars-Household-members-records.csv"

# ---------------------------------------------------------------------
# Code books.
#
# The raw files store everything as numbers. These dictionaries are the
# official NSSO code lists, lifted from the value labels embedded in the
# SPSS version of the same data, so that "3" becomes "Christianity".
# ---------------------------------------------------------------------
STATE = {
    "1": "Haryana",
    "2": "Madhya Pradesh",
    "3": "Gujarat",
    "4": "Orissa",
    "5": "Tamil Nadu",
    "6": "Meghalaya",
}

SECTOR = {"1": "Rural", "2": "Urban"}

SEX = {"1": "Male", "2": "Female"}

RELATION = {
    "1": "Self (head)",
    "2": "Spouse of head",
    "3": "Married child",
    "4": "Spouse of married child",
    "5": "Unmarried child",
    "6": "Grandchild",
    "7": "Parent / parent-in-law",
    "8": "Sibling / other relative",
    "9": "Servant / employee / non-relative",
}

MARITAL = {
    "1": "Never married",
    "2": "Currently married",
    "3": "Widowed",
    "4": "Divorced / separated",
}

YES_NO = {"1": "Yes", "2": "No"}

EDUCATION = {
    "01": "Not literate",
    "02": "Literate through NFEC/AEC",
    "03": "Literate through TLC",
    "04": "Literate: other",
    "05": "Literate but below primary",
    "06": "Primary",
    "07": "Middle",
    "08": "Secondary",
    "09": "Higher secondary",
    "10": "Graduate and above: agriculture",
    "11": "Graduate and above: engineering/technology",
    "12": "Graduate and above: medicine",
    "13": "Graduate and above: other subjects",
}

PRINCIPAL_ACTIVITY = {
    "11": "Self-employed: own account worker",
    "12": "Employer",
    "21": "Unpaid family worker in household enterprise",
    "22": "Home-based worker",
    "32": "Regular salaried/wage, permanent",
    "33": "Regular salaried/wage, non-permanent",
    "41": "Casual/contractual wage labour: public works",
    "51": "Casual/contractual wage labour: other works",
    "52": "Trainee/intern (paid)",
    "53": "Exchange labour",
    "81": "Not working but seeking/available for work",
    "91": "Attended educational institution",
    "92": "Attended domestic duties only",
    "93": "Domestic duties plus free collection, sewing etc.",
    "94": "Rentier / pensioner / remittance receiver",
    "95": "Unable to work due to disability",
    "96": "Beggars, prostitutes",
    "97": "Others",
}

HOUSEHOLD_TYPE = {
    "11": "Rural: self-employed professional, non-agricultural",
    "12": "Rural: self-employed non-professional, non-agricultural",
    "13": "Rural: agricultural labour",
    "14": "Rural: other labour",
    "15": "Rural: self-employed in agriculture",
    "19": "Rural: others",
    "21": "Urban: self-employed professional",
    "22": "Urban: self-employed non-professional",
    "23": "Urban: regular wage/salary earner",
    "24": "Urban: casual labour",
    "29": "Urban: others",
}

RELIGION = {
    "1": "Hinduism",
    "2": "Islam",
    "3": "Christianity",
    "4": "Sikhism",
    "5": "Buddhism",
    "6": "Zoroastrianism",
    "7": "Jainism",
    "9": "Others",
}

SOCIAL_GROUP = {"1": "Scheduled tribe", "2": "Scheduled caste", "9": "Others"}

STRUCTURE = {"1": "Kutcha", "2": "Semi-pucca", "3": "Pucca"}


def load(zip_path: Path, inner_name: str) -> pd.DataFrame:
    """Read one CSV out of the zip without unpacking the whole archive.

    Everything is read as text on purpose. Survey codes like district
    "02" or education "06" lose their leading zero if pandas guesses
    they are numbers, and then they stop matching the code books above.
    """
    with zipfile.ZipFile(zip_path) as z:
        with z.open(inner_name) as f:
            return pd.read_csv(f, dtype=str)


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)

    hh = load(ZIP_PATH, HH_FILE)
    mem = load(ZIP_PATH, MEMBER_FILE)
    print(f"households read : {len(hh):,}")
    print(f"members read    : {len(mem):,}")

    # -----------------------------------------------------------------
    # Household side: keep the identifiers and the Block 1 characteristics.
    # -----------------------------------------------------------------
    hh_keep = hh[
        [
            "Hhold_key", "State", "District", "district_class", "sector",
            "Tehsil_Town", "stratum", "Vill_Blk", "sub_blk",
            "B1_q1", "B1_q2", "B1_q3", "B1_q4", "B1_q5", "B1_q6",
            "B1_q7", "B1_q8", "B1_q9", "B1_q10", "B1_q11", "B1_q12",
            "wgt_combined_st", "wgt_combined_dt",
        ]
    ].rename(
        columns={
            "Hhold_key": "household_id",
            "District": "district_code",
            "district_class": "district_class",
            "Tehsil_Town": "tehsil_town_code",
            "stratum": "stratum_code",
            "Vill_Blk": "village_block_code",
            "sub_blk": "sub_block_code",
            "B1_q1": "household_size",
            "B1_q2": "hh_industry_occupation_code",
            "B1_q3": "household_type_code",
            "B1_q4": "religion_code",
            "B1_q5": "social_group_code",
            "B1_q6": "homestead_code",
            "B1_q7": "land_owned_acres",
            "B1_q8": "land_possessed_acres",
            "B1_q9": "monthly_hh_expenditure_rs",
            "B1_q10": "monthly_percapita_expenditure_rs",
            "B1_q11": "structure_code",
            "B1_q12": "disabled_persons_in_hh",
            "wgt_combined_st": "weight_state",
            "wgt_combined_dt": "weight_district",
        }
    )

    # -----------------------------------------------------------------
    # Person side: identifiers plus the Block 2 demographics.
    # -----------------------------------------------------------------
    mem_keep = mem[
        [
            "Key_Membno", "Key_hhold", "memb_no",
            "B2_c3", "B2_c4", "B2_c5", "B2_c6", "B2_c7", "B2_c8", "B2_c9",
            "B2_c15",
        ]
    ].rename(
        columns={
            "Key_Membno": "person_id",
            "Key_hhold": "household_id",
            "memb_no": "member_no",
            "B2_c3": "relation_code",
            "B2_c4": "sex_code",
            "B2_c5": "age",
            "B2_c6": "marital_code",
            "B2_c7": "disabled_code",
            "B2_c8": "education_code",
            "B2_c9": "principal_activity_code",
            "B2_c15": "decision_making_code",
        }
    )

    # -----------------------------------------------------------------
    # Join: every member gets their household's characteristics attached.
    # "left" means keep all members even if a household record is missing.
    # -----------------------------------------------------------------
    df = mem_keep.merge(hh_keep, on="household_id", how="left", validate="m:1")

    unmatched = df["household_size"].isna().sum()
    print(f"members with no household record: {unmatched:,}")

    # -----------------------------------------------------------------
    # Turn codes into readable labels.
    # -----------------------------------------------------------------
    df["state"] = df["State"].map(STATE)

    # District codes repeat across states (Tamil Nadu 12 is not Gujarat 12),
    # so build a unique district identifier as well.
    df["state_district"] = df["state"] + " / district " + df["district_code"]
    df["sector"] = df["sector"].map(SECTOR)
    df["sex"] = df["sex_code"].map(SEX)
    df["relation_to_head"] = df["relation_code"].map(RELATION)
    df["marital_status"] = df["marital_code"].map(MARITAL)
    df["disabled"] = df["disabled_code"].map(YES_NO)
    df["education"] = df["education_code"].map(EDUCATION)
    df["principal_activity"] = df["principal_activity_code"].map(PRINCIPAL_ACTIVITY)
    df["household_type"] = df["household_type_code"].map(HOUSEHOLD_TYPE)
    df["religion"] = df["religion_code"].map(RELIGION)
    df["social_group"] = df["social_group_code"].map(SOCIAL_GROUP)
    df["homestead"] = df["homestead_code"].map(YES_NO)
    df["structure_type"] = df["structure_code"].map(STRUCTURE)
    df["participates_in_decisions"] = df["decision_making_code"].map(YES_NO)

    # -----------------------------------------------------------------
    # Numbers back to numbers now that the leading zeros have done their job.
    # -----------------------------------------------------------------
    numeric = [
        "age", "household_size", "land_owned_acres", "land_possessed_acres",
        "monthly_hh_expenditure_rs", "monthly_percapita_expenditure_rs",
        "disabled_persons_in_hh", "weight_state", "weight_district",
    ]
    for col in numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # -----------------------------------------------------------------
    # Final column order.
    # -----------------------------------------------------------------
    cols = [
        "person_id", "household_id", "member_no",
        "state", "district_code", "state_district", "district_class",
        "tehsil_town_code", "stratum_code", "village_block_code",
        "sub_block_code", "sector",
        "sex", "age", "relation_to_head", "marital_status",
        "education", "principal_activity", "disabled",
        "participates_in_decisions",
        "household_size", "household_type", "hh_industry_occupation_code",
        "religion", "social_group", "homestead",
        "land_owned_acres", "land_possessed_acres",
        "monthly_hh_expenditure_rs", "monthly_percapita_expenditure_rs",
        "structure_type", "disabled_persons_in_hh",
        "weight_state", "weight_district",
    ]
    out = df[cols]

    out_path = OUT_DIR / "person_level_TUS_1998.csv"
    out.to_csv(out_path, index=False)
    print(f"\nwrote {len(out):,} rows to {out_path}")

    # -----------------------------------------------------------------
    # Quick sanity checks, printed so you can eyeball them.
    # -----------------------------------------------------------------
    print("\nSex breakdown (unweighted):")
    print(out["sex"].value_counts(dropna=False))

    print("\nSex by sector (unweighted):")
    print(pd.crosstab(out["sector"], out["sex"]))

    print("\nNumber of distinct districts covered:")
    print(out["state_district"].nunique())

    print("\nPeople per state:")
    print(out["state"].value_counts())

    print("\nAge: ")
    print(out["age"].describe())

    dupes = out["person_id"].duplicated().sum()
    print(f"\nduplicate person ids: {dupes}")


if __name__ == "__main__":
    main()
