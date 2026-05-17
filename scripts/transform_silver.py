"""
transform_silver.py — Silver layer transformation
Reads raw CSVs from data/bronze/, cleans them, and joins them into two
unified Parquet files at data/silver/.

Output
------
  mental_health.parquet    country × year grain  (main fact)
  suicide_by_age.parquet   country × year × age_group × sex grain

What this script fixes
----------------------
1. World Bank rows without country_code are income-group aggregates — dropped.
2. WHO MH facility indicators have sex/age dims — aggregated to BTSX total.
3. SDGSUICIDE retains all sex × age combinations for the age-stratified table.
4. Column names standardised to snake_case across all sources.
5. All tables joined on (country_code + year) via left join anchored on GDP.
"""

import logging
import os
from datetime import datetime

import pandas as pd

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "silver.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

BRONZE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "bronze")
SILVER_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "silver")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_bronze(filename: str) -> pd.DataFrame:
    path = os.path.join(BRONZE_DIR, filename)
    df = pd.read_csv(path)
    log.info("Read  %-45s  %d rows", filename, len(df))
    return df


def drop_wb_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """World Bank includes regional/income-group rows with no ISO3 code — drop them."""
    before = len(df)
    df = df.dropna(subset=["country_code"])
    df = df[df["country_code"].str.len() == 3]
    log.info("  Dropped %d aggregate rows (no country_code)", before - len(df))
    return df


def _clean_wb_indicator(df: pd.DataFrame, col_name: str) -> pd.DataFrame:
    """Generic World Bank cleaner: drop aggregates, keep country_code + year + value."""
    df = drop_wb_aggregates(df)
    df = df[["country_code", "year", "value"]].copy()
    return df.rename(columns={"value": col_name})


def _clean_who_facility(df: pd.DataFrame, col_name: str) -> pd.DataFrame:
    """
    Generic WHO MH facility cleaner.
    Filters to BTSX (both-sex total) where available, otherwise takes mean.
    Drops rows without a valid 3-char country code.
    """
    df = df.dropna(subset=["country_code", "year", "value"])
    df = df[df["country_code"].str.len() == 3]
    btsx = df[df["sex"].isin(["BTSX"]) | df["sex"].isna()]
    if len(btsx) == 0:
        btsx = df
    btsx = btsx.groupby(["country_code", "year"], as_index=False)["value"].mean()
    return btsx.rename(columns={"value": col_name})


# ---------------------------------------------------------------------------
# World Bank cleaning functions
# ---------------------------------------------------------------------------

def clean_worldbank_gdp(df):          return _clean_wb_indicator(df, "gdp_per_capita")
def clean_worldbank_unemployment(df): return _clean_wb_indicator(df, "unemployment_rate")
def clean_worldbank_unemp_male(df):   return _clean_wb_indicator(df, "unemployment_male")
def clean_worldbank_unemp_female(df): return _clean_wb_indicator(df, "unemployment_female")
def clean_worldbank_youth_unemp(df):  return _clean_wb_indicator(df, "youth_unemployment_rate")
def clean_worldbank_gini(df):         return _clean_wb_indicator(df, "gini_index")
def clean_worldbank_urban(df):        return _clean_wb_indicator(df, "urban_population_pct")
def clean_worldbank_suicide(df):      return _clean_wb_indicator(df, "suicide_rate_per_100k")
def clean_worldbank_suicide_male(df): return _clean_wb_indicator(df, "suicide_rate_male")
def clean_worldbank_suicide_female(df): return _clean_wb_indicator(df, "suicide_rate_female")
def clean_worldbank_health_exp(df):   return _clean_wb_indicator(df, "health_expenditure_per_capita")
def clean_worldbank_health_exp_gdp(df): return _clean_wb_indicator(df, "health_expenditure_gdp_pct")
def clean_worldbank_life_exp(df):     return _clean_wb_indicator(df, "life_expectancy")


# ---------------------------------------------------------------------------
# World Bank GDP also carries the country name — extract it separately
# ---------------------------------------------------------------------------

def extract_country_name(df: pd.DataFrame) -> pd.DataFrame:
    df = drop_wb_aggregates(df)
    return df[["country_code", "country"]].drop_duplicates(subset="country_code")


# ---------------------------------------------------------------------------
# WHO GHO cleaning functions — facility indicators
# ---------------------------------------------------------------------------

def clean_who_outpatient(df):     return _clean_who_facility(df, "outpatient_facilities")
def clean_who_hospitals(df):      return _clean_who_facility(df, "mental_hospitals")
def clean_who_psych_beds(df):     return _clean_who_facility(df, "psychiatric_beds")
def clean_who_psychiatrists(df):  return _clean_who_facility(df, "psychiatrists_per_100k")
def clean_who_mh_nurses(df):      return _clean_who_facility(df, "mh_nurses_per_100k")
def clean_who_psychologists(df):  return _clean_who_facility(df, "psychologists_per_100k")
def clean_who_day_treatment(df):  return _clean_who_facility(df, "day_treatment_facilities")
def clean_who_mh_expenditure(df): return _clean_who_facility(df, "mh_expenditure_pct")


# ---------------------------------------------------------------------------
# WHO SDGSUICIDE — age + sex stratified (separate grain)
# ---------------------------------------------------------------------------

AGE_LABEL_MAP = {
    "AGEGROUP_YEARS10-19": "10-19", "AGEGROUP_YEARS15-19": "15-19",
    "AGEGROUP_YEARS15-29": "15-29", "AGEGROUP_YEARS20-29": "20-29",
    "AGEGROUP_YEARS30-39": "30-39", "AGEGROUP_YEARS30-49": "30-49",
    "AGEGROUP_YEARS40-49": "40-49", "AGEGROUP_YEARS50-59": "50-59",
    "AGEGROUP_YEARS50-69": "50-69", "AGEGROUP_YEARS60-69": "60-69",
    "AGEGROUP_YEARS70PLUS": "70+",  "AGEGROUP_YEARSALL":   "All Ages",
}

SEX_LABEL_MAP = {"SEX_BTSX": "Both", "SEX_MLE": "Male", "SEX_FMLE": "Female"}


def clean_who_suicide_by_age(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=["country_code", "year", "value"])
    df = df[df["country_code"].str.len() == 3]
    df = df[df["age_group"].notna() & df["sex"].notna()].copy()
    df["age_group"] = df["age_group"].map(AGE_LABEL_MAP).fillna(df["age_group"])
    df["sex"]       = df["sex"].map(SEX_LABEL_MAP).fillna(df["sex"])
    df = df[["country_code", "year", "age_group", "sex", "value"]].copy()
    df = df.rename(columns={"value": "suicide_rate_per_100k"})
    df["year"] = df["year"].astype(int)
    return df.drop_duplicates(subset=["country_code", "year", "age_group", "sex"])


# ---------------------------------------------------------------------------
# Join — main country × year silver table
# ---------------------------------------------------------------------------

def build_silver(gdp, country_names, unemp, unemp_male, unemp_female,
                 youth_unemp, gini, urban, suicide, suicide_male,
                 suicide_female, health_exp, health_exp_gdp, life_exp,
                 outpatient, hospitals, psych_beds, psychiatrists,
                 mh_nurses, psychologists, day_treatment,
                 mh_expenditure) -> pd.DataFrame:
    """
    Left-join all sources on (country_code + year) anchored on GDP.
    GDP has the broadest coverage — every country, every year.
    Sources with narrower coverage produce NaN outside their range.
    """
    df = gdp.merge(country_names, on="country_code", how="left")

    for right in [unemp, unemp_male, unemp_female, youth_unemp, gini, urban,
                  suicide, suicide_male, suicide_female, health_exp,
                  health_exp_gdp, life_exp, outpatient, hospitals,
                  psych_beds, psychiatrists, mh_nurses, psychologists,
                  day_treatment, mh_expenditure]:
        df = df.merge(right, on=["country_code", "year"], how="left")

    df = df[[
        "country_code", "country", "year",
        "gdp_per_capita", "unemployment_rate", "unemployment_male",
        "unemployment_female", "youth_unemployment_rate", "gini_index",
        "urban_population_pct", "suicide_rate_per_100k", "suicide_rate_male",
        "suicide_rate_female", "health_expenditure_per_capita",
        "health_expenditure_gdp_pct", "life_expectancy",
        "outpatient_facilities", "mental_hospitals", "psychiatric_beds",
        "psychiatrists_per_100k", "mh_nurses_per_100k", "psychologists_per_100k",
        "day_treatment_facilities", "mh_expenditure_pct",
    ]]

    return df.sort_values(["country_code", "year"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def save_silver(df: pd.DataFrame, filename: str) -> None:
    os.makedirs(SILVER_DIR, exist_ok=True)
    path = os.path.join(SILVER_DIR, filename)
    df.to_parquet(path, index=False)
    size_kb = os.path.getsize(path) / 1024
    log.info("Saved %-40s  %.1f KB  (%d rows, %d cols)",
             filename, size_kb, len(df), len(df.columns))


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

def log_summary(df: pd.DataFrame, label: str) -> None:
    log.info("-" * 60)
    log.info("%s summary", label)
    log.info("  Shape:     %d rows × %d columns", *df.shape)
    log.info("  Countries: %d unique", df["country_code"].nunique())
    log.info("  Years:     %d – %d", df["year"].min(), df["year"].max())
    log.info("  Null rates:")
    for col, n in df.isnull().sum().items():
        pct = n / len(df) * 100
        if pct > 0:
            log.info("    %-35s  %.1f%%", col, pct)
    log.info("-" * 60)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run() -> None:
    log.info("=" * 60)
    log.info("Silver transform started  %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    log.info("=" * 60)

    # --- Read bronze ---
    log.info("--- Reading bronze ---")
    gdp_raw        = read_bronze("worldbank_gdp.csv")
    unemp_raw      = read_bronze("worldbank_unemployment.csv")
    unemp_m_raw    = read_bronze("worldbank_unemployment_male.csv")
    unemp_f_raw    = read_bronze("worldbank_unemployment_female.csv")
    youth_raw      = read_bronze("worldbank_youth_unemployment.csv")
    gini_raw       = read_bronze("worldbank_gini.csv")
    urban_raw      = read_bronze("worldbank_urban.csv")
    suicide_raw    = read_bronze("worldbank_suicide.csv")
    suicide_m_raw  = read_bronze("worldbank_suicide_male.csv")
    suicide_f_raw  = read_bronze("worldbank_suicide_female.csv")
    health_raw     = read_bronze("worldbank_health_expenditure.csv")
    health_gdp_raw = read_bronze("worldbank_health_expenditure_gdp.csv")
    life_raw       = read_bronze("worldbank_life_expectancy.csv")
    outpatient_raw = read_bronze("who_outpatient_facilities.csv")
    hospitals_raw  = read_bronze("who_mental_hospitals.csv")
    psych_beds_raw = read_bronze("who_psychiatric_beds.csv")
    psychiatrists_raw  = read_bronze("who_psychiatrists.csv")
    mh_nurses_raw      = read_bronze("who_mh_nurses.csv")
    psychologists_raw  = read_bronze("who_psychologists.csv")
    day_treat_raw      = read_bronze("who_day_treatment.csv")
    mh_exp_raw         = read_bronze("who_mh_expenditure.csv")
    suicide_age_raw    = read_bronze("who_suicide_by_age.csv")

    # --- Clean ---
    log.info("--- Cleaning ---")
    country_names  = extract_country_name(gdp_raw)
    gdp            = clean_worldbank_gdp(gdp_raw)
    unemp          = clean_worldbank_unemployment(unemp_raw)
    unemp_male     = clean_worldbank_unemp_male(unemp_m_raw)
    unemp_female   = clean_worldbank_unemp_female(unemp_f_raw)
    youth_unemp    = clean_worldbank_youth_unemp(youth_raw)
    gini           = clean_worldbank_gini(gini_raw)
    urban          = clean_worldbank_urban(urban_raw)
    suicide        = clean_worldbank_suicide(suicide_raw)
    suicide_male   = clean_worldbank_suicide_male(suicide_m_raw)
    suicide_female = clean_worldbank_suicide_female(suicide_f_raw)
    health_exp     = clean_worldbank_health_exp(health_raw)
    health_exp_gdp = clean_worldbank_health_exp_gdp(health_gdp_raw)
    life_exp       = clean_worldbank_life_exp(life_raw)
    outpatient     = clean_who_outpatient(outpatient_raw)
    hospitals      = clean_who_hospitals(hospitals_raw)
    psych_beds     = clean_who_psych_beds(psych_beds_raw)
    psychiatrists  = clean_who_psychiatrists(psychiatrists_raw)
    mh_nurses      = clean_who_mh_nurses(mh_nurses_raw)
    psychologists  = clean_who_psychologists(psychologists_raw)
    day_treatment  = clean_who_day_treatment(day_treat_raw)
    mh_expenditure = clean_who_mh_expenditure(mh_exp_raw)
    suicide_by_age = clean_who_suicide_by_age(suicide_age_raw)

    # --- Build and save ---
    log.info("--- Building silver tables ---")

    silver = build_silver(
        gdp, country_names, unemp, unemp_male, unemp_female, youth_unemp,
        gini, urban, suicide, suicide_male, suicide_female, health_exp,
        health_exp_gdp, life_exp, outpatient, hospitals, psych_beds,
        psychiatrists, mh_nurses, psychologists, day_treatment, mh_expenditure,
    )

    log.info("--- Saving ---")
    save_silver(silver, "mental_health.parquet")
    save_silver(suicide_by_age, "suicide_by_age.parquet")

    log_summary(silver, "mental_health")
    log.info("  suicide_by_age: %d rows", len(suicide_by_age))
    log.info("Silver layer ready.")


if __name__ == "__main__":
    run()
