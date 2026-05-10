import logging
import os
import requests
from datetime import datetime

# ---------------------------------------------------------------------------
# Logging setup
# Every run appends a timestamped block to logs/ingest.log
# ---------------------------------------------------------------------------
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "ingest.log"), encoding="utf-8"),
        logging.StreamHandler(),  # also prints to terminal
    ],
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data sources
# Each entry: (filename_to_save, direct_download_url)
# ---------------------------------------------------------------------------
BRONZE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "bronze")

SOURCES = {
    "owid_mental_health.csv": (
        "https://raw.githubusercontent.com/owid/owid-datasets/master/datasets/"
        "Mental%20health%20-%20Our%20World%20in%20Data/"
        "Mental%20health%20-%20Our%20World%20in%20Data.csv"
    ),
}

# NOTE: WHO and World Bank files require manual download (no stable direct URL).
# Instructions are printed at the end of this script.


def download_file(url: str, dest_path: str) -> bool:
    """Download a single file from url and save it to dest_path.

    Returns True on success, False on failure.
    Skips the download if the file already exists (idempotent behaviour).
    """
    filename = os.path.basename(dest_path)

    if os.path.exists(dest_path):
        log.info("SKIP   %s — already in bronze (delete to re-download)", filename)
        return True

    log.info("START  Downloading %s", filename)
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()  # raises an error for 4xx/5xx responses

        with open(dest_path, "wb") as f:
            f.write(response.content)

        size_kb = len(response.content) / 1024
        log.info("OK     %s saved (%.1f KB)", filename, size_kb)
        return True

    except requests.exceptions.RequestException as e:
        log.error("FAIL   %s — %s", filename, e)
        return False


def run():
    log.info("=" * 60)
    log.info("Ingest run started at %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    log.info("=" * 60)

    os.makedirs(BRONZE_DIR, exist_ok=True)

    results = {}
    for filename, url in SOURCES.items():
        dest = os.path.join(BRONZE_DIR, filename)
        results[filename] = download_file(url, dest)

    # Summary
    ok = sum(results.values())
    total = len(results)
    log.info("-" * 60)
    log.info("Ingest complete: %d/%d files downloaded successfully", ok, total)

    # Manual download instructions for WHO and World Bank
    print("\n" + "=" * 60)
    print("MANUAL DOWNLOADS REQUIRED")
    print("=" * 60)
    print("""
The following datasets must be downloaded manually and placed in data/bronze/:

1. WHO Global Health Observatory — Mental health atlas
   URL: https://www.who.int/data/gho/data/themes/mental-health
   Save as: data/bronze/who_mental_health.csv

2. World Bank — GDP per capita & unemployment
   URL: https://data.worldbank.org/indicator/NY.GDP.PCAP.CD
   Save as: data/bronze/worldbank_gdp.csv

   URL: https://data.worldbank.org/indicator/SL.UEM.TOTL.ZS
   Save as: data/bronze/worldbank_unemployment.csv
""")


if __name__ == "__main__":
    run()
