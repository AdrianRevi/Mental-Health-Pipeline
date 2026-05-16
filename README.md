# Mental Health Pipeline

An end-to-end ETL pipeline on public mental health data following the **Medallion Architecture** (Bronze → Silver → Gold). Built as a portfolio project for junior Data Engineer roles.

**Stack:** Python · pandas · Great Expectations · DuckDB · GitHub Actions  
**Cost:** €0 — fully local, no cloud services required  
**Data:** World Bank API · WHO Global Health Observatory API

---

## Architecture

```
World Bank API          WHO GHO API
(GDP, unemployment,     (mental health
 suicide rate,           outpatient
 country metadata)       facilities)
        │                    │
        └──────┬─────────────┘
               ▼
        🥉 Bronze Layer          data/bronze/
           Raw CSVs as returned by APIs — never modified
               │
               ▼
        🥈 Silver Layer          data/silver/
           Cleaned, typed, joined into one unified table
           Validated with Great Expectations (20 rules)
               │
               ▼
        🥇 Gold Layer            data/gold/
           Star schema: dim_country · dim_year · fact_mental_health
               │
               ▼
          DuckDB                 data/mental_health.duckdb
          Queryable with SQL · connectable from Power BI
```

---

## Data Sources

| File | Source | What it contains |
|---|---|---|
| `worldbank_gdp.csv` | World Bank API `NY.GDP.PCAP.CD` | GDP per capita (current US$), 2000–2024 |
| `worldbank_unemployment.csv` | World Bank API `SL.UEM.TOTL.ZS` | Unemployment rate (% labour force), 2000–2024 |
| `worldbank_suicide.csv` | World Bank API `SH.STA.SUIC.P5` | Suicide mortality rate per 100k, 2000–2024 |
| `worldbank_countries.csv` | World Bank API `/country` | Country metadata: region, income level, capital |
| `who_mental_health.csv` | WHO GHO API `MH_6` | Mental health outpatient facilities per 100k |

All APIs are public and require no authentication.

---

## Star Schema (Gold Layer)

```
dim_country                    dim_year
───────────                    ────────
country_code  PK               year          PK
country                        decade
region                         period_label
income_level                   date
capital_city
      │                              │
      └──────────┬───────────────────┘
                 ▼
       fact_mental_health
       ──────────────────
       country_code        FK → dim_country
       year                FK → dim_year
       gdp_per_capita
       unemployment_rate
       suicide_rate_per_100k
       outpatient_facilities
```

---

## Pipeline Flow

```
ingest.py            Downloads raw data from 2 APIs → data/bronze/
transform_silver.py  Cleans, filters, joins → data/silver/mental_health.parquet
quality_checks.py    20 Great Expectations rules — fails loudly on bad data
transform_gold.py    Builds star schema → data/gold/ (3 parquet files)
load_duckdb.py       Loads gold tables → data/mental_health.duckdb
```

Each script is independent and exits with code 1 on failure, stopping the pipeline at the broken stage.

---

## Quick Start

```bash
# 1. Clone and create virtual environment
git clone https://github.com/AdrianRevi/mental-health-pipeline.git
cd mental-health-pipeline
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the full pipeline
python scripts/ingest.py
python scripts/transform_silver.py
python scripts/quality_checks.py
python scripts/transform_gold.py
python scripts/load_duckdb.py
```

All output lands in `data/`, all run logs in `logs/`.

---

## Automated Runs (GitHub Actions)

The pipeline runs automatically via `.github/workflows/pipeline.yml`:

- **On every push** to `main`
- **Every Monday at 08:00 UTC**

GitHub sends an email notification if any step fails. The Actions tab shows exactly which stage broke and how long each step took.

---

## Querying with DuckDB

```python
import duckdb

con = duckdb.connect("data/mental_health.duckdb")

# Average suicide rate by region and decade
con.execute("""
    SELECT
        c.region,
        y.decade,
        ROUND(AVG(f.suicide_rate_per_100k), 2) AS avg_suicide_rate,
        ROUND(AVG(f.gdp_per_capita), 0)         AS avg_gdp
    FROM fact_mental_health f
    JOIN dim_country c ON f.country_code = c.country_code
    JOIN dim_year    y ON f.year          = y.year
    WHERE f.suicide_rate_per_100k IS NOT NULL
    GROUP BY c.region, y.decade
    ORDER BY avg_suicide_rate DESC
""").df()
```

---

## Connecting Power BI Desktop

1. Open Power BI Desktop
2. **Get Data → ODBC**
3. DSN: point to `data/mental_health.duckdb` using the [DuckDB ODBC driver](https://duckdb.org/docs/api/odbc/overview)
4. Load `dim_country`, `dim_year`, `fact_mental_health`
5. In Model view, define relationships:
   - `fact_mental_health[country_code]` → `dim_country[country_code]`
   - `fact_mental_health[year]` → `dim_year[year]`
6. Mark `dim_year` as a Date Table using the `date` column to enable time intelligence (YTD, year-over-year comparisons)

---

## Project Structure

```
mental-health-pipeline/
│
├── data/
│   ├── bronze/              raw CSVs from APIs (gitignored)
│   ├── silver/              cleaned parquet (gitignored)
│   ├── gold/                star schema parquets (gitignored)
│   └── mental_health.duckdb analytical database (gitignored)
│
├── scripts/
│   ├── ingest.py            Bronze — API ingestion
│   ├── transform_silver.py  Silver — cleaning & joining
│   ├── quality_checks.py    Great Expectations validation
│   ├── transform_gold.py    Gold — star schema
│   └── load_duckdb.py       DuckDB loader
│
├── .github/workflows/
│   └── pipeline.yml         GitHub Actions orchestration
│
├── logs/                    Runtime logs (gitignored)
├── requirements.txt
└── README.md
```

---

## Interview Talking Point

> *"I built an end-to-end ETL pipeline on public mental health data from the World Bank and WHO, following the Medallion Architecture — Bronze for raw API ingestion, Silver for cleaned and validated data, Gold for a star schema ready for Power BI. I used Python and pandas for transformation, Great Expectations for automated data quality with 20 validation rules, DuckDB as a local analytical database, and GitHub Actions for weekly orchestration. The pipeline runs automatically, fails loudly with clear logs if data quality checks don't pass, and outputs a star schema queryable with SQL."*
