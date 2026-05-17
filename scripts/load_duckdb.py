"""
load_duckdb.py — Load Gold tables into DuckDB
Reads the three Parquet files from data/gold/ and writes them as permanent
tables inside data/mental_health.duckdb.

Why DuckDB?
  - Runs entirely in-process — no server to start, no cloud needed
  - Reads Parquet natively and very fast (columnar engine)
  - Supports full SQL including window functions and CTEs
  - Power BI Desktop can connect to it via ODBC
"""

import logging
import os
from datetime import datetime

import duckdb

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "duckdb.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

GOLD_DIR   = os.path.join(os.path.dirname(__file__), "..", "data", "gold")
DB_PATH    = os.path.join(os.path.dirname(__file__), "..", "data", "mental_health.duckdb")

GOLD_TABLES = [
    ("dim_country",          "dim_country.parquet"),
    ("dim_year",             "dim_year.parquet"),
    ("dim_age",              "dim_age.parquet"),
    ("fact_mental_health",   "fact_mental_health.parquet"),
    ("fact_suicide_by_age",  "fact_suicide_by_age.parquet"),
]


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

ALLOWED_TABLES = {t for t, _ in GOLD_TABLES}


def load_table(con: duckdb.DuckDBPyConnection, table: str, filename: str) -> None:
    """
    Drops and recreates one table from its Parquet file.

    CREATE OR REPLACE TABLE reads the Parquet directly into DuckDB storage —
    the data is copied, so DuckDB works even if the Parquet file is deleted.
    Using an absolute path avoids issues with the working directory.
    """
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Unknown table name: {table}")

    parquet_path = os.path.abspath(os.path.join(GOLD_DIR, filename))

    if not os.path.exists(parquet_path):
        raise FileNotFoundError(f"Gold file not found: {parquet_path}")

    safe_path = parquet_path.replace("'", "''")
    con.execute(
        f"CREATE OR REPLACE TABLE {table} AS "
        f"SELECT * FROM read_parquet('{safe_path}')"
    )

    row_count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    log.info("  Loaded %-25s  %d rows", table, row_count)


def verify(con: duckdb.DuckDBPyConnection) -> None:
    """
    Runs a quick SQL sanity check after loading.
    Joins all three tables to confirm the foreign keys resolve correctly.
    """
    sql = """
        SELECT
            c.region,
            y.decade,
            COUNT(*)                              AS country_year_pairs,
            ROUND(AVG(f.gdp_per_capita), 0)       AS avg_gdp,
            ROUND(AVG(f.unemployment_rate), 1)    AS avg_unemployment,
            ROUND(AVG(f.suicide_rate_per_100k),1) AS avg_suicide_rate
        FROM fact_mental_health f
        JOIN dim_country c ON f.country_code = c.country_code
        JOIN dim_year    y ON f.year          = y.year
        WHERE f.gdp_per_capita IS NOT NULL
          AND f.suicide_rate_per_100k IS NOT NULL
        GROUP BY c.region, y.decade
        ORDER BY c.region, y.decade
        LIMIT 12
    """
    log.info("--- Verification query (region × decade) ---")
    rows = con.execute(sql).fetchall()
    log.info("%-35s  %6s  %6s  %10s  %10s  %12s",
             "region", "decade", "pairs", "avg_gdp", "avg_unemp", "avg_suicide")
    log.info("-" * 90)
    for r in rows:
        log.info("%-35s  %6d  %6d  %10.0f  %10.1f  %12.1f", *r)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run() -> None:
    log.info("=" * 60)
    log.info("DuckDB load started  %s",
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    log.info("=" * 60)

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    # duckdb.connect() creates the file if it doesn't exist
    with duckdb.connect(DB_PATH) as con:
        log.info("Connected to %s", DB_PATH)

        for table, filename in GOLD_TABLES:
            load_table(con, table, filename)

        verify(con)

    db_size_kb = os.path.getsize(DB_PATH) / 1024
    log.info("=" * 60)
    log.info("DuckDB file: %s  (%.1f KB)", DB_PATH, db_size_kb)
    log.info("Gold layer loaded into DuckDB.")


if __name__ == "__main__":
    run()
