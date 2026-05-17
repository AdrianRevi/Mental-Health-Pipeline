"""
transform_gold.py — Gold layer transformation
Builds analysis-ready tables for the Power BI star schema.

Input
-----
  data/bronze/worldbank_countries.csv   country metadata (with lat/lon)
  data/silver/mental_health.parquet     cleaned country × year metrics
  data/silver/suicide_by_age.parquet    cleaned country × year × age × sex

Output — data/gold/
-----
  dim_country.parquet         one row per country
  dim_year.parquet            one row per year
  dim_age.parquet             one row per age group
  fact_mental_health.parquet  country × year measures
  fact_suicide_by_age.parquet country × year × age_group × sex measures

Star schema
-----------
  dim_country ──┐
  dim_year    ──┼── fact_mental_health
                │
  dim_country ──┤
  dim_year    ──┼── fact_suicide_by_age
  dim_age     ──┘
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
        logging.FileHandler(os.path.join(LOG_DIR, "gold.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

BRONZE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "bronze")
SILVER_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "silver")
GOLD_DIR   = os.path.join(os.path.dirname(__file__), "..", "data", "gold")


# ---------------------------------------------------------------------------
# dim_country
# ---------------------------------------------------------------------------

def build_dim_country() -> pd.DataFrame:
    path = os.path.join(BRONZE_DIR, "worldbank_countries.csv")
    df = pd.read_csv(path)
    log.info("Read worldbank_countries.csv: %d rows", len(df))

    df = df[df["region"] != "Aggregates"].copy()
    df = df.rename(columns={"country_name": "country"})

    df["latitude"]  = pd.to_numeric(df["latitude"],  errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    df = df[
        ["country_code", "country", "region", "income_level",
         "capital_city", "latitude", "longitude"]
    ].reset_index(drop=True)

    log.info("dim_country: %d countries", len(df))
    return df


# ---------------------------------------------------------------------------
# dim_year
# ---------------------------------------------------------------------------

def build_dim_year(year_min: int = 2000, year_max: int = None) -> pd.DataFrame:
    if year_max is None:
        year_max = datetime.now().year
    years = list(range(year_min, year_max + 1))
    df = pd.DataFrame({"year": years})
    df["decade"]       = (df["year"] // 10) * 10
    df["period_label"] = df["decade"].astype(str) + "s"
    df["date"]         = pd.to_datetime(df["year"].astype(str) + "-01-01")
    log.info("dim_year: %d years (%d – %d)", len(df), year_min, year_max)
    return df


# ---------------------------------------------------------------------------
# dim_age
# ---------------------------------------------------------------------------

AGE_ORDER = [
    "10-14", "15-19", "20-24", "25-29", "30-34", "35-39",
    "40-44", "45-49", "50-54", "55-59", "60-64", "65-69",
    "70-74", "75-79", "80+",
]

AGE_LABEL = {
    "10-14": "Children & Early Adolescents (10-14)",
    "15-19": "Late Adolescents (15-19)",
    "20-24": "Young Adults (20-24)",
    "25-29": "Young Adults (25-29)",
    "30-34": "Adults (30-34)",
    "35-39": "Adults (35-39)",
    "40-44": "Adults (40-44)",
    "45-49": "Adults (45-49)",
    "50-54": "Middle Age (50-54)",
    "55-59": "Middle Age (55-59)",
    "60-64": "Older Adults (60-64)",
    "65-69": "Older Adults (65-69)",
    "70-74": "Elderly (70-74)",
    "75-79": "Elderly (75-79)",
    "80+":   "Elderly 80+",
}


def build_dim_age(suicide_age: pd.DataFrame) -> pd.DataFrame:
    groups = suicide_age["age_group"].dropna().unique().tolist()
    known  = [g for g in AGE_ORDER if g in groups]
    other  = sorted([g for g in groups if g not in AGE_ORDER])
    all_groups = known + other

    df = pd.DataFrame({"age_group": all_groups})
    df["age_order"] = range(len(df))
    df["age_label"] = df["age_group"].map(AGE_LABEL).fillna(df["age_group"])
    log.info("dim_age: %d age groups", len(df))
    return df


# ---------------------------------------------------------------------------
# fact_mental_health
# ---------------------------------------------------------------------------

def build_fact(silver: pd.DataFrame) -> pd.DataFrame:
    fact = silver[[
        "country_code", "year",
        "gdp_per_capita", "unemployment_rate", "unemployment_male",
        "unemployment_female", "youth_unemployment_rate", "gini_index",
        "urban_population_pct", "suicide_rate_per_100k", "suicide_rate_male",
        "suicide_rate_female", "health_expenditure_per_capita",
        "health_expenditure_gdp_pct", "life_expectancy",
        "outpatient_facilities", "mental_hospitals", "psychiatric_beds",
        "psychiatrists_per_100k", "mh_nurses_per_100k", "psychologists_per_100k",
        "day_treatment_facilities", "mh_expenditure_pct",
    ]].copy()
    log.info("fact_mental_health: %d rows × %d cols", *fact.shape)
    return fact


# ---------------------------------------------------------------------------
# fact_suicide_by_age
# ---------------------------------------------------------------------------

def build_fact_suicide_by_age(suicide_age: pd.DataFrame) -> pd.DataFrame:
    fact = suicide_age[[
        "country_code", "year", "age_group", "sex", "suicide_rate_per_100k"
    ]].copy()
    log.info("fact_suicide_by_age: %d rows × %d cols", *fact.shape)
    return fact


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def save_gold(df: pd.DataFrame, filename: str) -> None:
    os.makedirs(GOLD_DIR, exist_ok=True)
    path = os.path.join(GOLD_DIR, filename)
    df.to_parquet(path, index=False)
    size_kb = os.path.getsize(path) / 1024
    log.info("Saved %-40s  %.1f KB  (%d rows)", filename, size_kb, len(df))


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run() -> None:
    log.info("=" * 60)
    log.info("Gold transform started  %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    log.info("=" * 60)

    silver_path = os.path.join(SILVER_DIR, "mental_health.parquet")
    age_path    = os.path.join(SILVER_DIR, "suicide_by_age.parquet")

    for p in [silver_path, age_path]:
        if not os.path.exists(p):
            log.error("Silver file not found: %s — run transform_silver.py first", p)
            raise SystemExit(1)

    silver      = pd.read_parquet(silver_path)
    suicide_age = pd.read_parquet(age_path)
    log.info("Read silver: %d rows | suicide_by_age: %d rows", len(silver), len(suicide_age))

    log.info("--- Building dimensions ---")
    dim_country = build_dim_country()
    dim_year    = build_dim_year()
    dim_age     = build_dim_age(suicide_age)

    log.info("--- Building fact tables ---")
    fact_main = build_fact(silver)
    fact_age  = build_fact_suicide_by_age(suicide_age)

    log.info("--- Saving ---")
    save_gold(dim_country, "dim_country.parquet")
    save_gold(dim_year,    "dim_year.parquet")
    save_gold(dim_age,     "dim_age.parquet")
    save_gold(fact_main,   "fact_mental_health.parquet")
    save_gold(fact_age,    "fact_suicide_by_age.parquet")

    log.info("=" * 60)
    log.info("Gold layer ready.")


if __name__ == "__main__":
    run()
