import logging
import os
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
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Expected files in bronze/
# The pipeline does not download files — it validates that they are present.
# This mirrors real-world pipelines where files arrive via SFTP/S3/manual drop.
# ---------------------------------------------------------------------------
BRONZE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "bronze")

EXPECTED_FILES = {
    "owid_mental_health.csv": (
        "Our World in Data — Mental health prevalence\n"
        "  Download: https://ourworldindata.org/mental-health\n"
        "  Click 'Download' -> 'Full Data' -> save as owid_mental_health.csv"
    ),
    "who_mental_health.csv": (
        "WHO Global Health Observatory — Mental health atlas\n"
        "  Download: https://www.who.int/data/gho/data/themes/mental-health\n"
        "  Save as: who_mental_health.csv"
    ),
    "worldbank_gdp.csv": (
        "World Bank — GDP per capita (current US$)\n"
        "  Download: https://data.worldbank.org/indicator/NY.GDP.PCAP.CD\n"
        "  Click 'Download' -> CSV -> save as worldbank_gdp.csv"
    ),
    "worldbank_unemployment.csv": (
        "World Bank — Unemployment, total (% of labor force)\n"
        "  Download: https://data.worldbank.org/indicator/SL.UEM.TOTL.ZS\n"
        "  Click 'Download' -> CSV -> save as worldbank_unemployment.csv"
    ),
}


def check_bronze_files() -> dict[str, bool]:
    """Check which expected files are present in data/bronze/.

    Returns a dict mapping filename -> True (present) / False (missing).
    """
    os.makedirs(BRONZE_DIR, exist_ok=True)
    results = {}
    for filename in EXPECTED_FILES:
        path = os.path.join(BRONZE_DIR, filename)
        present = os.path.isfile(path) and os.path.getsize(path) > 0
        results[filename] = present
        if present:
            size_kb = os.path.getsize(path) / 1024
            log.info("OK     %-40s (%.1f KB)", filename, size_kb)
        else:
            log.warning("MISS   %s — not found in data/bronze/", filename)
    return results


def print_missing_instructions(results: dict[str, bool]) -> None:
    missing = [f for f, present in results.items() if not present]
    if not missing:
        return
    print("\n" + "=" * 60)
    print(f"ACTION REQUIRED — {len(missing)} file(s) missing from data/bronze/")
    print("=" * 60)
    for filename in missing:
        print(f"\n  {EXPECTED_FILES[filename]}")
    print()


def run():
    log.info("=" * 60)
    log.info("Ingest run started at %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    log.info("=" * 60)

    results = check_bronze_files()

    ok = sum(results.values())
    total = len(results)
    log.info("-" * 60)
    log.info("Bronze check: %d/%d files present", ok, total)

    print_missing_instructions(results)

    if ok < total:
        log.warning("Pipeline cannot proceed until all files are in data/bronze/")
        raise SystemExit(1)

    log.info("All files present. Bronze layer ready.")


if __name__ == "__main__":
    run()
