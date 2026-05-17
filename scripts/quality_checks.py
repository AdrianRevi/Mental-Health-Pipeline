"""
quality_checks.py — Data Quality Layer
Validates data/silver/mental_health.parquet using Great Expectations.
Raises SystemExit(1) if any expectation fails, stopping the pipeline.

Expectations defined
--------------------
STRUCTURAL  Columns exist, key columns never null, year in valid range
RANGE       Numeric values are non-negative / within domain bounds (when present)
COVERAGE    Null rates stay within documented thresholds per indicator
VOLUME      Table has enough rows and columns
"""

import logging
import os
import warnings
from datetime import datetime

import great_expectations as gx
import pandas as pd

# Suppress GX internal deprecation warnings — they're noise for us
warnings.filterwarnings("ignore", category=DeprecationWarning)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "quality.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# Silence GX's own verbose logging so our log messages stay readable
logging.getLogger("great_expectations").setLevel(logging.ERROR)

SILVER_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "silver")
SILVER_FILE = os.path.join(SILVER_DIR, "mental_health.parquet")


# ---------------------------------------------------------------------------
# GX setup
# ---------------------------------------------------------------------------

def build_validator(df: pd.DataFrame):
    """
    Creates a GX validator wrapping the silver DataFrame.

    EphemeralDataContext means GX stores nothing on disk — no config files,
    no metadata store, no Data Docs site.  Perfect for a CI/CD pipeline where
    we just want pass/fail, not a persistent results store.
    """
    context = gx.get_context()
    datasource = context.sources.add_pandas("silver_source")
    asset = datasource.add_dataframe_asset("mental_health")
    batch_request = asset.build_batch_request(dataframe=df)
    suite = context.add_expectation_suite("silver_suite")
    return context.get_validator(
        batch_request=batch_request,
        expectation_suite_name="silver_suite",
    )


# ---------------------------------------------------------------------------
# Expectations
# ---------------------------------------------------------------------------

def define_expectations(v) -> None:
    """
    Attaches every expectation to the validator.

    mostly=X means "at least X% of rows must satisfy this rule".
    Rows where the value is null are excluded from range checks automatically
    by GX — so expect_column_values_to_be_between only fires on non-null rows.

    Thresholds are set with a safety margin vs. current observed null rates:
      gdp_per_capita       2.9% null  → threshold 90% not-null  (10pp margin)
      unemployment_rate   11.6% null  → threshold 80% not-null  (9pp margin)
      suicide_rate_per_100k 22.8% null → threshold 65% not-null (12pp margin)
      outpatient_facilities 97.8% null → no null-coverage check (sparse by design)
    """

    # --- STRUCTURAL: core columns must always exist ---
    core_columns = [
        "country_code", "country", "year",
        "gdp_per_capita", "unemployment_rate", "suicide_rate_per_100k",
        "outpatient_facilities", "suicide_rate_male", "suicide_rate_female",
        "gini_index", "urban_population_pct", "youth_unemployment_rate",
        "unemployment_male", "unemployment_female",
        "health_expenditure_per_capita", "health_expenditure_gdp_pct",
        "life_expectancy", "mental_hospitals", "psychiatric_beds",
        "psychiatrists_per_100k", "mh_nurses_per_100k", "psychologists_per_100k",
        "day_treatment_facilities", "mh_expenditure_pct",
    ]
    for col in core_columns:
        v.expect_column_to_exist(col)

    # --- STRUCTURAL: key identifier columns never null ---
    v.expect_column_values_to_not_be_null("country_code")
    v.expect_column_values_to_not_be_null("country")
    v.expect_column_values_to_not_be_null("year")

    # --- STRUCTURAL: year within dataset scope ---
    v.expect_column_values_to_be_between("year", min_value=2000, max_value=datetime.now().year)

    # --- VOLUME: table must have at least this many rows and columns ---
    v.expect_table_row_count_to_be_between(min_value=6_000)
    v.expect_table_column_count_to_be_between(min_value=24)

    # --- RANGE: values must be non-negative when present ---
    v.expect_column_values_to_be_between("gdp_per_capita",           min_value=0, mostly=0.99)
    v.expect_column_values_to_be_between("unemployment_rate",        min_value=0, max_value=100, mostly=0.99)
    v.expect_column_values_to_be_between("suicide_rate_per_100k",    min_value=0, mostly=0.99)
    v.expect_column_values_to_be_between("suicide_rate_male",        min_value=0, mostly=0.99)
    v.expect_column_values_to_be_between("suicide_rate_female",      min_value=0, mostly=0.99)
    v.expect_column_values_to_be_between("outpatient_facilities",    min_value=0, mostly=0.99)
    v.expect_column_values_to_be_between("life_expectancy",          min_value=0, max_value=120, mostly=0.99)
    v.expect_column_values_to_be_between("urban_population_pct",     min_value=0, max_value=100, mostly=0.99)
    v.expect_column_values_to_be_between("gini_index",               min_value=0, max_value=100, mostly=0.99)

    # --- COVERAGE: null rates for core indicators ---
    v.expect_column_values_to_not_be_null("gdp_per_capita",          mostly=0.90)
    v.expect_column_values_to_not_be_null("unemployment_rate",       mostly=0.80)
    v.expect_column_values_to_not_be_null("suicide_rate_per_100k",   mostly=0.65)
    v.expect_column_values_to_not_be_null("life_expectancy",         mostly=0.85)


# ---------------------------------------------------------------------------
# Results reporting
# ---------------------------------------------------------------------------

def report_results(results) -> int:
    """
    Logs each expectation result as PASS or FAIL.
    Returns the number of failed expectations.
    """
    failed = 0
    log.info("%-8s  %-45s  %s", "STATUS", "EXPECTATION", "DETAIL")
    log.info("-" * 80)

    for r in results.results:
        exp_type = r.expectation_config.expectation_type
        kwargs   = r.expectation_config.kwargs

        # Build a short description of what was checked
        col    = kwargs.get("column", "")
        mostly = kwargs.get("mostly")
        lo     = kwargs.get("min_value")
        hi     = kwargs.get("max_value")

        if mostly is not None:
            detail = f"{col}  (mostly={mostly})"
        elif lo is not None or hi is not None:
            detail = f"{col}  [{lo}, {hi}]"
        else:
            detail = col or str(kwargs)

        if r.success:
            log.info("PASS      %-45s  %s", exp_type, detail)
        else:
            failed += 1
            # Extract observed value for context (e.g. actual % not-null)
            observed = ""
            result_dict = r.result
            if "unexpected_percent" in result_dict:
                observed = f"  ← {100 - result_dict['unexpected_percent']:.1f}% valid"
            elif "observed_value" in result_dict:
                observed = f"  ← observed: {result_dict['observed_value']}"
            log.error("FAIL      %-45s  %s%s", exp_type, detail, observed)

    return failed


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run() -> None:
    log.info("=" * 60)
    log.info("Quality checks started  %s",
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    log.info("=" * 60)

    if not os.path.exists(SILVER_FILE):
        log.error("Silver file not found: %s", SILVER_FILE)
        log.error("Run transform_silver.py before quality_checks.py")
        raise SystemExit(1)

    df = pd.read_parquet(SILVER_FILE)
    log.info("Loaded silver: %d rows × %d columns", *df.shape)

    validator = build_validator(df)
    define_expectations(validator)

    log.info("Running %d expectations…", len(validator.expectation_suite.expectations))
    log.info("-" * 60)

    results = validator.validate()

    log.info("-" * 60)
    failed = report_results(results)

    log.info("=" * 60)
    total = len(results.results)
    log.info("Results: %d passed, %d failed", total - failed, failed)

    if failed > 0:
        log.error("Quality checks FAILED — pipeline stopped.")
        raise SystemExit(1)

    log.info("All checks passed. Silver layer is clean.")


if __name__ == "__main__":
    run()
