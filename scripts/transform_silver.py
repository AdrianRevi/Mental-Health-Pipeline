"""
transform_silver.py — Silver layer transformation
Reads raw CSVs from data/bronze/, cleans them, and joins them into one
unified Parquet file at data/silver/mental_health.parquet.

What this script fixes
----------------------
1. World Bank rows without a country_code are income-group aggregates
   ("High income", "Low income", …) — filtered out, keeping real countries only.
2. WHO MH_6 has a `sex` column that is 100% null — dropped.
3. Column names differ between sources — standardised to snake_case.
4. All four tables are joined on (country_code + year) using a left join
   anchored on World Bank GDP so we don't lose country/year combinations
   that exist in WB but not in WHO.

Output schema
-------------
country_code              str   ISO3 code, e.g. "ESP"
country                   str   Full name, e.g. "Spain"
year                      int
gdp_per_capita            float GDP per capita, current US$
unemployment_rate         float % of labour force
suicide_rate_per_100k     float deaths per 100,000 population
outpatient_facilities     float mental health outpatient facilities per 100k
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
    log.info("Read  %-40s  %d rows", filename, len(df))
    return df


def drop_wb_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """
    The World Bank API includes regional/income-group rows alongside real
    countries.  These rows have no ISO3 code (country_code is NaN).
    We only want actual countries, so we drop the others.
    """
    before = len(df)
    df = df.dropna(subset=["country_code"])
    dropped = before - len(df)
    log.info("  Dropped %d aggregate rows (no country_code)", dropped)
    return df


# ---------------------------------------------------------------------------
# Per-source cleaning functions
# ---------------------------------------------------------------------------

def clean_worldbank_gdp(df: pd.DataFrame) -> pd.DataFrame:
    df = drop_wb_aggregates(df)
    df = df[["country_code", "country", "year", "value"]].copy()
    df = df.rename(columns={"value": "gdp_per_capita"})
    return df


def clean_worldbank_unemployment(df: pd.DataFrame) -> pd.DataFrame:
    df = drop_wb_aggregates(df)
    df = df[["country_code", "year", "value"]].copy()
    df = df.rename(columns={"value": "unemployment_rate"})
    return df


def clean_worldbank_suicide(df: pd.DataFrame) -> pd.DataFrame:
    df = drop_wb_aggregates(df)
    df = df[["country_code", "year", "value"]].copy()
    df = df.rename(columns={"value": "suicide_rate_per_100k"})
    return df


def clean_who_mental_health(df: pd.DataFrame) -> pd.DataFrame:
    # `sex` is 100% null for this indicator — drop it
    df = df[["country_code", "year", "value"]].copy()
    df = df.rename(columns={"value": "outpatient_facilities"})
    return df


# ---------------------------------------------------------------------------
# Join
# ---------------------------------------------------------------------------

def build_silver(gdp, unemployment, suicide, who) -> pd.DataFrame:
    """
    Joins all four cleaned tables on (country_code + year).

    We use a LEFT join anchored on GDP because it has the broadest coverage
    (all countries, all years 2000-2024).  Columns from sources with narrower
    coverage (WHO: 2013-2017 only) will be NaN outside their range — that is
    expected and correct behaviour, not an error.

    Join order:
      gdp (base)
        LEFT JOIN unemployment  on country_code + year
        LEFT JOIN suicide       on country_code + year
        LEFT JOIN who           on country_code + year
    """
    df = gdp.merge(unemployment, on=["country_code", "year"], how="left")
    df = df.merge(suicide,       on=["country_code", "year"], how="left")
    df = df.merge(who,           on=["country_code", "year"], how="left")

    # Canonical column order
    df = df[
        [
            "country_code",
            "country",
            "year",
            "gdp_per_capita",
            "unemployment_rate",
            "suicide_rate_per_100k",
            "outpatient_facilities",
        ]
    ]

    # Sort for readability and deterministic output
    df = df.sort_values(["country_code", "year"]).reset_index(drop=True)

    return df


# ---------------------------------------------------------------------------
# Save to silver
# ---------------------------------------------------------------------------

def save_silver(df: pd.DataFrame, filename: str) -> None:
    """
    Saves the unified DataFrame as Parquet.

    Why Parquet instead of CSV?
    - Columnar format: reading one column doesn't load the others — much
      faster for analytical queries that touch a few columns at a time.
    - Stores data types natively (int stays int, float stays float) — no
      more silent type coercion when re-reading a CSV.
    - Compressed by default: ~5-10× smaller than equivalent CSV on typical
      pipeline data.
    """
    os.makedirs(SILVER_DIR, exist_ok=True)
    path = os.path.join(SILVER_DIR, filename)
    df.to_parquet(path, index=False)
    size_kb = os.path.getsize(path) / 1024
    log.info("Saved %-40s  %.1f KB  (%d rows, %d cols)",
             filename, size_kb, len(df), len(df.columns))


# ---------------------------------------------------------------------------
# Diagnostics — logged after saving
# ---------------------------------------------------------------------------

def log_summary(df: pd.DataFrame) -> None:
    log.info("-" * 60)
    log.info("Silver table summary")
    log.info("  Shape:     %d rows × %d columns", *df.shape)
    log.info("  Countries: %d unique ISO3 codes", df["country_code"].nunique())
    log.info("  Years:     %d – %d", df["year"].min(), df["year"].max())
    log.info("  Null counts per column:")
    for col, n in df.isnull().sum().items():
        pct = n / len(df) * 100
        log.info("    %-28s  %5d  (%.1f%%)", col, n, pct)
    log.info("-" * 60)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run() -> None:
    log.info("=" * 60)
    log.info("Silver transform started  %s",
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    log.info("=" * 60)

    # Read bronze
    gdp          = read_bronze("worldbank_gdp.csv")
    unemployment = read_bronze("worldbank_unemployment.csv")
    suicide      = read_bronze("worldbank_suicide.csv")
    who          = read_bronze("who_mental_health.csv")

    # Clean each source
    log.info("--- Cleaning ---")
    gdp          = clean_worldbank_gdp(gdp)
    unemployment = clean_worldbank_unemployment(unemployment)
    suicide      = clean_worldbank_suicide(suicide)
    who          = clean_who_mental_health(who)

    log.info("After cleaning:")
    log.info("  gdp:          %d rows", len(gdp))
    log.info("  unemployment: %d rows", len(unemployment))
    log.info("  suicide:      %d rows", len(suicide))
    log.info("  who:          %d rows", len(who))

    # Join
    log.info("--- Joining ---")
    silver = build_silver(gdp, unemployment, suicide, who)

    # Save
    log.info("--- Saving ---")
    save_silver(silver, "mental_health.parquet")

    # Diagnostics
    log_summary(silver)

    log.info("Silver layer ready.")


if __name__ == "__main__":
    run()
