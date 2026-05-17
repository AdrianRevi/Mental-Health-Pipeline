"""
transform_gold.py — Gold layer transformation
Builds three analysis-ready tables for the Power BI star schema.

Input
-----
  data/bronze/worldbank_countries.csv   country metadata
  data/silver/mental_health.parquet     cleaned, unified metrics

Output — data/gold/
-----
  dim_country.parquet       one row per country  (261 rows)
  dim_year.parquet          one row per year     (25 rows, 2000-2024)
  fact_mental_health.parquet one row per country × year (6525 rows)

Star schema
-----------
  dim_country ──┐
                ├── fact_mental_health
  dim_year    ──┘
"""

import logging
import os
from datetime import datetime

import pandas as pd
from datetime import datetime

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
    """
    Reads worldbank_countries.csv from bronze and filters it to real countries.

    The World Bank API returns 296 entries: ~261 countries + 35 regional/
    income-group aggregates.  Aggregates have no region assigned
    ("Aggregates" as region value) — we drop them to keep only sovereign
    countries and territories.
    """
    path = os.path.join(BRONZE_DIR, "worldbank_countries.csv")
    df = pd.read_csv(path)
    log.info("Read worldbank_countries.csv: %d rows", len(df))

    # Drop income-group and regional aggregates
    before = len(df)
    df = df[df["region"] != "Aggregates"].copy()
    log.info("  Dropped %d aggregate rows", before - len(df))

    df = df.rename(columns={"country_name": "country"})

    # Convert lat/lon from string to float (empty strings → NaN)
    df["latitude"]  = pd.to_numeric(df["latitude"],  errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    # Keep only the columns Power BI needs
    df = df[
        ["country_code", "country", "region", "income_level", "capital_city",
         "latitude", "longitude"]
    ].reset_index(drop=True)

    log.info("dim_country: %d countries", len(df))
    return df


# ---------------------------------------------------------------------------
# dim_year
# ---------------------------------------------------------------------------

def build_dim_year(year_min: int = 2000, year_max: int = None) -> pd.DataFrame:
    """
    Generates one row per year with decade and period label.

    No source file needed — this dimension is derived entirely from the
    date range of the pipeline.  In Power BI you would typically connect
    a full Date table, but for yearly data this simpler version is enough.
    """
    if year_max is None:
        year_max = datetime.now().year
    years = list(range(year_min, year_max + 1))
    df = pd.DataFrame({"year": years})

    # Decade: 2000 → 2000, 2013 → 2010, 2024 → 2020
    df["decade"] = (df["year"] // 10) * 10

    # Human-readable period label for slicers in Power BI
    df["period_label"] = df["decade"].astype(str) + "s"

    # Date column (Jan 1 of each year) so Power BI can mark this as a
    # Date Table and enable time intelligence (YTD, year-over-year, etc.)
    df["date"] = pd.to_datetime(df["year"].astype(str) + "-01-01")

    log.info("dim_year: %d years (%d – %d)", len(df), year_min, year_max)
    return df


# ---------------------------------------------------------------------------
# fact_mental_health
# ---------------------------------------------------------------------------

def build_fact(silver: pd.DataFrame) -> pd.DataFrame:
    """
    Extracts the fact table from the Silver unified dataset.

    The fact table contains only foreign keys and measures — no descriptive
    attributes (those live in the dimensions).  Removing the `country` name
    column here avoids data duplication: Power BI will join it from
    dim_country via country_code.
    """
    fact = silver[
        [
            "country_code",          # FK → dim_country
            "year",                  # FK → dim_year
            "gdp_per_capita",
            "unemployment_rate",
            "suicide_rate_per_100k",
            "outpatient_facilities",
        ]
    ].copy()

    log.info("fact_mental_health: %d rows × %d cols", *fact.shape)
    return fact


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def save_gold(df: pd.DataFrame, filename: str) -> None:
    os.makedirs(GOLD_DIR, exist_ok=True)
    path = os.path.join(GOLD_DIR, filename)
    df.to_parquet(path, index=False)
    size_kb = os.path.getsize(path) / 1024
    log.info("Saved %-35s  %.1f KB  (%d rows)", filename, size_kb, len(df))


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run() -> None:
    log.info("=" * 60)
    log.info("Gold transform started  %s",
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    log.info("=" * 60)

    silver_path = os.path.join(SILVER_DIR, "mental_health.parquet")
    if not os.path.exists(silver_path):
        log.error("Silver file not found — run transform_silver.py first")
        raise SystemExit(1)

    silver = pd.read_parquet(silver_path)
    log.info("Read silver: %d rows", len(silver))

    log.info("--- Building dimensions ---")
    dim_country = build_dim_country()
    dim_year    = build_dim_year()

    log.info("--- Building fact table ---")
    fact = build_fact(silver)

    log.info("--- Saving ---")
    save_gold(dim_country, "dim_country.parquet")
    save_gold(dim_year,    "dim_year.parquet")
    save_gold(fact,        "fact_mental_health.parquet")

    log.info("=" * 60)
    log.info("Gold layer ready.")


if __name__ == "__main__":
    run()
