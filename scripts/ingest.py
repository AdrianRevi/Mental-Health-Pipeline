"""
ingest.py — Bronze layer ingestion
Downloads raw data from public APIs and saves CSVs to data/bronze/.

Sources
-------
- World Bank API v2  (no account/key required)
    • GDP per capita          NY.GDP.PCAP.CD
    • Unemployment rate       SL.UEM.TOTL.ZS
    • Suicide mortality rate  SH.STA.SUIC.P5  (mental-health proxy)
- WHO Global Health Observatory (GHO) OData API  (no account/key required)
    • Mental health outpatient facilities per 100k population  MH_6
"""

import logging
import os
import time
from datetime import datetime

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Logging — writes to logs/ingest.log AND the console
# ---------------------------------------------------------------------------
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "ingest.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

BRONZE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "bronze")

# ---------------------------------------------------------------------------
# Source definitions
# ---------------------------------------------------------------------------

# World Bank: list of (indicator_code, description, output_filename)
WB_INDICATORS = [
    # Core economic indicators
    ("NY.GDP.PCAP.CD",    "GDP per capita (current US$)",              "worldbank_gdp.csv"),
    ("SL.UEM.TOTL.ZS",   "Unemployment, total (% of labor force)",    "worldbank_unemployment.csv"),
    ("SL.UEM.TOTL.MA.ZS","Unemployment, male (% of labor force)",     "worldbank_unemployment_male.csv"),
    ("SL.UEM.TOTL.FE.ZS","Unemployment, female (% of labor force)",   "worldbank_unemployment_female.csv"),
    ("SL.UEM.1524.ZS",   "Unemployment, youth 15-24 (%)",             "worldbank_youth_unemployment.csv"),
    ("SI.POV.GINI",       "GINI index (income inequality)",            "worldbank_gini.csv"),
    ("SP.URB.TOTL.IN.ZS", "Urban population (% of total)",            "worldbank_urban.csv"),
    # Health indicators
    ("SH.STA.SUIC.P5",   "Suicide mortality rate (per 100k pop.)",    "worldbank_suicide.csv"),
    ("SH.STA.SUIC.MA.P5","Suicide mortality rate, male (per 100k)",   "worldbank_suicide_male.csv"),
    ("SH.STA.SUIC.FE.P5","Suicide mortality rate, female (per 100k)", "worldbank_suicide_female.csv"),
    ("SH.XPD.CHEX.PC.CD","Health expenditure per capita (US$)",       "worldbank_health_expenditure.csv"),
    ("SH.XPD.CHEX.GD.ZS","Health expenditure (% of GDP)",             "worldbank_health_expenditure_gdp.csv"),
    ("SP.DYN.LE00.IN",   "Life expectancy at birth (years)",          "worldbank_life_expectancy.csv"),
]

# World Bank country metadata — region, income level, capital city
WB_COUNTRIES_FILE = "worldbank_countries.csv"

# WHO GHO: list of (output_filename, indicator_code, description)
# The GHO OData API returns JSON with a "value" array.
WHO_INDICATORS = [
    ("who_outpatient_facilities.csv", "MH_6",       "Mental health outpatient facilities per 100k"),
    ("who_mental_hospitals.csv",      "MH_1",       "Mental hospitals per 100k"),
    ("who_psychiatric_beds.csv",      "MH_2",       "Psychiatric beds per 100k"),
    ("who_psychiatrists.csv",         "MH_3",       "Psychiatrists working in mental health per 100k"),
    ("who_mh_nurses.csv",             "MH_4",       "Mental health nurses per 100k"),
    ("who_psychologists.csv",         "MH_5",       "Psychologists working in mental health per 100k"),
    ("who_day_treatment.csv",         "MH_7",       "Day treatment facilities per 100k"),
    ("who_mh_expenditure.csv",        "MH_12",      "Mental health expenditure as % of health budget"),
    ("who_suicide_by_age.csv",        "SDGSUICIDE", "Suicide mortality rate by age and sex (WHO SDG)"),
]

# Polite User-Agent so servers can identify automated requests
HEADERS = {
    "User-Agent": "MentalHealthPipeline/1.0"
}


# ---------------------------------------------------------------------------
# World Bank downloader
# ---------------------------------------------------------------------------
def fetch_worldbank(code: str, description: str) -> pd.DataFrame:
    """
    Fetches all countries × years 2000-{current year} for one World Bank indicator.

    The API is paginated (max 1 000 rows per page), so we loop until we
    have collected every page.  Each row is flattened into a plain dict
    before being turned into a DataFrame.
    """
    WB_BASE = "https://api.worldbank.org/v2"
    end_year = datetime.now().year
    records = []
    page = 1
    total_pages = None  # we don't know this until the first response

    while total_pages is None or page <= total_pages:
        url = (
            f"{WB_BASE}/country/all/indicator/{code}"
            f"?format=json&date=2000:{end_year}&per_page=1000&page={page}"
        )
        log.info("  WB GET  %s  (page %d/%s)", code, page, total_pages or "?")

        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()  # raises HTTPError for 4xx/5xx

        payload = resp.json()
        # World Bank always returns a 2-element list:
        #   payload[0] = pagination metadata
        #   payload[1] = list of data rows (may be None if no data)
        meta = payload[0]
        rows = payload[1] or []

        if total_pages is None:
            total_pages = meta["pages"]

        for row in rows:
            records.append(
                {
                    "country":        row["country"]["value"],
                    "country_code":   row["countryiso3code"],
                    "year":           int(row["date"]),
                    "value":          row["value"],   # may be None (missing data)
                    "indicator_code": code,
                    "indicator_name": description,
                }
            )

        page += 1
        if page <= total_pages:
            time.sleep(0.3)  # don't hammer the API between pages

    df = pd.DataFrame(records)
    log.info("  WB %s: %d rows total", code, len(df))
    return df


# ---------------------------------------------------------------------------
# World Bank country metadata downloader
# ---------------------------------------------------------------------------
def fetch_worldbank_countries() -> pd.DataFrame:
    """
    Fetches country metadata from the World Bank: region, income level,
    capital city.  One request — all countries fit in a single page.

    This table becomes dim_country in the Gold layer.
    """
    url = "https://api.worldbank.org/v2/country?format=json&per_page=300"
    log.info("  WB GET  country metadata")

    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    meta, rows = resp.json()
    records = []
    for row in rows or []:
        records.append(
            {
                "country_code":  row["id"],               # ISO3
                "country_name":  row["name"],
                "region":        row["region"]["value"],
                "income_level":  row["incomeLevel"]["value"],
                "capital_city":  row.get("capitalCity", ""),
                "longitude":     row.get("longitude", ""),
                "latitude":      row.get("latitude", ""),
            }
        )

    df = pd.DataFrame(records)
    log.info("  WB countries: %d rows", len(df))
    return df


# ---------------------------------------------------------------------------
# WHO GHO downloader
# ---------------------------------------------------------------------------
def fetch_who_gho(indicator_code: str, description: str) -> pd.DataFrame:
    """
    Fetches one indicator from the WHO Global Health Observatory OData API.

    The response is a JSON object with a single "value" key whose content
    is a list of observation records.  We keep only the columns we need.
    """
    GHO_BASE = "https://ghoapi.azureedge.net/api"
    url = f"{GHO_BASE}/{indicator_code}"
    log.info("  WHO GET  %s  (%s)", indicator_code, description)

    resp = requests.get(url, headers=HEADERS, timeout=60)
    resp.raise_for_status()

    rows = resp.json().get("value", [])
    records = []
    for row in rows:
        records.append(
            {
                "country_code":   row.get("SpatialDim"),   # ISO3
                "year":           row.get("TimeDim"),
                "sex":            row.get("Dim1"),          # BTSX / MLE / FMLE
                "age_group":      row.get("Dim2"),          # populated for SDGSUICIDE
                "value":          row.get("NumericValue"),
                "indicator_code": indicator_code,
                "indicator_name": description,
            }
        )

    df = pd.DataFrame(records)
    log.info("  WHO %s: %d rows", indicator_code, len(df))
    return df


# ---------------------------------------------------------------------------
# Save raw DataFrame to bronze/
# ---------------------------------------------------------------------------
def save_bronze(df: pd.DataFrame, filename: str) -> None:
    """Writes a CSV to data/bronze/ — raw, untransformed (bronze = source of truth)."""
    os.makedirs(BRONZE_DIR, exist_ok=True)
    path = os.path.join(BRONZE_DIR, filename)
    df.to_csv(path, index=False)
    size_kb = os.path.getsize(path) / 1024
    log.info("  Saved %-40s  %.1f KB", filename, size_kb)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def run() -> None:
    log.info("=" * 60)
    log.info("Ingest started  %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    log.info("=" * 60)

    errors: list[str] = []

    # --- World Bank ---
    log.info("--- World Bank API ---")
    for code, description, filename in WB_INDICATORS:
        try:
            df = fetch_worldbank(code, description)
            save_bronze(df, filename)
        except Exception as exc:
            log.error("FAILED %s: %s", filename, exc)
            errors.append(filename)

    try:
        df = fetch_worldbank_countries()
        save_bronze(df, WB_COUNTRIES_FILE)
    except Exception as exc:
        log.error("FAILED %s: %s", WB_COUNTRIES_FILE, exc)
        errors.append(WB_COUNTRIES_FILE)

    # --- WHO GHO ---
    log.info("--- WHO Global Health Observatory ---")
    for filename, code, description in WHO_INDICATORS:
        try:
            df = fetch_who_gho(code, description)
            save_bronze(df, filename)
        except Exception as exc:
            log.error("FAILED %s: %s", filename, exc)
            errors.append(filename)

    # --- Final summary ---
    log.info("=" * 60)
    total = len(WB_INDICATORS) + 1 + len(WHO_INDICATORS)
    ok = total - len(errors)
    log.info("Ingest complete: %d/%d sources succeeded", ok, total)

    if errors:
        log.warning("Failed sources: %s", ", ".join(errors))
        raise SystemExit(1)

    log.info("Bronze layer ready.")


if __name__ == "__main__":
    run()
