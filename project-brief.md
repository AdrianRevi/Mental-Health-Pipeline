# 🧠 Mental Health Pipeline — Project Brief

## Overview

An end-to-end ETL data engineering pipeline that ingests, cleans, validates, and
transforms public mental health data from WHO, Our World in Data, and the World Bank.
Built to be portfolio-ready and interview-relevant for junior Data Engineer roles.

**Owner:** Adrian  
**Start date:** May 2026  
**Status:** Week 1 — not started  
**Last updated:** 2026-05-09

---

## Goals

1. Build a complete ETL pipeline following the **Medallion Architecture** (Bronze → Silver → Gold)
2. Demonstrate data quality practices using **Great Expectations**
3. Implement pipeline **orchestration** with GitHub Actions (free, no cloud VM needed)
4. Store and query processed data with **DuckDB** (local, free, production-grade)
5. Produce a portfolio-ready **GitHub repository** with documentation
6. Optional: connect a **Power BI Desktop** report on top of the Gold layer

---

## Tech Stack

| Layer | Tool | Why |
|---|---|---|
| Language | Python 3.11+ | Core stack |
| Transformation | pandas + PySpark (basic) | Current skill set |
| Storage | Local files + DuckDB | Free, no cloud needed |
| Data Quality | Great Expectations | Industry standard |
| Orchestration | GitHub Actions | Free tier, interview-relevant |
| Version Control | GitHub | Portfolio visibility |
| Output (optional) | Power BI Desktop | Existing skill |

**Total monthly cost: €0**

---

## Data Sources

All datasets are free, publicly downloadable as CSV — no API keys required.

| Dataset | Source | URL |
|---|---|---|
| Mental health prevalence by country/year | Our World in Data | https://ourworldindata.org/mental-health |
| Mental health resources (psychiatrists, beds) | WHO Global Health Observatory | https://www.who.int/data/gho |
| Socioeconomic context (GDP, unemployment) | World Bank Open Data | https://data.worldbank.org |

---

## Architecture

```
Raw CSVs (WHO, OWID, World Bank)
        │
        ▼
  🥉 Bronze Layer     Raw files ingested as-is, no transformations
        │
        ▼
  🥈 Silver Layer     Cleaned, typed, validated, joined across sources
        │
        ▼
  🥇 Gold Layer       Aggregated, analysis-ready tables
        │
        ▼
  DuckDB (local)      Queryable with SQL
        │
        ▼
  Power BI Desktop    Final dashboard (optional)
```

This pattern is called the **Medallion Architecture** — used by companies like
Microsoft, Databricks, and most modern data teams. Knowing it by name matters in interviews.

---

## Folder Structure

```
mental-health-pipeline/
│
├── data/
│   ├── bronze/              ← raw CSVs as downloaded, never modified
│   ├── silver/              ← cleaned .parquet files
│   └── gold/                ← aggregated, analysis-ready tables
│
├── scripts/
│   ├── ingest.py            ← loads raw files into bronze/
│   ├── transform_silver.py  ← cleans and standardizes data
│   ├── transform_gold.py    ← builds aggregated tables
│   ├── quality_checks.py    ← Great Expectations data validation
│   └── load_duckdb.py       ← loads gold tables into DuckDB
│
├── .github/
│   └── workflows/
│       └── pipeline.yml     ← GitHub Actions schedule (runs pipeline automatically)
│
├── tests/                   ← unit tests for transformation logic
├── logs/                    ← pipeline run logs
├── dbt/ (optional)          ← if SQL transformations grow complex
└── README.md                ← portfolio documentation
```

---

## 6-Week Roadmap

### Week 1 — Project Setup & Bronze Layer
- Set up folder structure and virtual environment
- Download raw CSVs from all 3 sources
- Write `ingest.py`: loads raw files into `data/bronze/` with zero transformation
- Add basic logging (every run writes to `logs/`)
- First Git commit

**Milestone:** Raw data flowing into Bronze with a clean, reproducible script.

---

### Week 2 — Silver Layer: Cleaning & Transformation
- Clean nulls, fix data types, standardize column names
- Solve the **country name mismatch problem** across sources
  (WHO uses "United States", World Bank uses "US" — this is a real production challenge)
- Write `transform_silver.py`: outputs cleaned `.parquet` files to `data/silver/`
- Join the three datasets on country + year

**Milestone:** One unified, clean dataset per country/year in Silver.

---

### Week 3 — Data Quality Layer
- Write `quality_checks.py` using **Great Expectations**
- Define expectations: column types, null thresholds, value ranges (e.g. prevalence 0–100%)
- Pipeline fails loudly with clear error messages if checks don't pass
- Add quality check results to the log

**Milestone:** Pipeline validates its own data and refuses to proceed on bad input.

---

### Week 4 — Gold Layer & DuckDB
- Write `transform_gold.py`: build aggregated tables
  - Prevalence trends by region over time
  - Resource gap table (high prevalence + low mental health funding)
  - Year-over-year change metrics
- Write `load_duckdb.py`: load Gold tables into a local DuckDB database
- Query the data with SQL to verify results

**Milestone:** Business-ready tables queryable via SQL in DuckDB.

---

### Week 5 — Orchestration with GitHub Actions
- Write `.github/workflows/pipeline.yml`
- Schedule the full pipeline to run automatically (e.g. weekly)
- Pipeline runs: ingest → validate → transform silver → transform gold → load DuckDB
- Pipeline status (success/failure) visible in GitHub

**Milestone:** Pipeline runs automatically without manual intervention.

---

### Week 6 — Polish & Portfolio
- Write a proper `README.md` (architecture diagram, how to run, what it does)
- Add screenshots or a short walkthrough video
- Optional: connect Power BI Desktop to the DuckDB Gold layer
- Publish everything to GitHub

**Milestone:** A shareable, documented project ready to show in interviews.

---

## Progress Log

| Week | Status | Notes |
|------|--------|-------|
| Week 1 — Setup & Bronze | ✅ Done | `ingest.py` — World Bank API (3 indicators) + WHO GHO API. 5/5 sources via live APIs, no manual downloads. |
| Week 2 — Silver Layer | ✅ Done | `transform_silver.py` — filters WB aggregates, joins 4 sources on country_code+year, outputs `mental_health.parquet` (6525 rows × 7 cols). |
| Week 3 — Data Quality | ✅ Done | `quality_checks.py` — 20 Great Expectations rules (structural, range, coverage, volume). Pipeline stops on any failure. |
| Week 4 — Gold & DuckDB | ✅ Done | `transform_gold.py` + `load_duckdb.py` — star schema: `dim_country` (217), `dim_year` (25), `fact_mental_health` (6525). Loaded into `mental_health.duckdb`. |
| Week 5 — GitHub Actions | ✅ Done | `.github/workflows/pipeline.yml` — triggers on push to main + weekly (Mon 08:00 UTC). Email alert on failure via GitHub notifications. |
| Week 6 — Polish & Portfolio | 🔲 Pending | Fix `dim_year` for PBI calendar, README.md, Power BI dashboard. |

---

## Interview Talking Point

> *"I built an end-to-end ETL pipeline on mental health data from WHO, Our World in Data,
> and the World Bank, following the Medallion Architecture — Bronze for raw ingestion,
> Silver for cleaned and validated data, Gold for business-ready aggregates.
> I used Python and pandas for transformation, Great Expectations for data quality,
> DuckDB as a local analytical database, and GitHub Actions for orchestration.
> The pipeline runs automatically on a schedule and fails with clear error logs
> if data quality checks don't pass."*

---

## Project Instructions for Claude

- Adrián is a junior data analyst/engineer learning through hands-on, project-based work
- Current stack: SQL, Power BI, Python, Spark (basic), Microsoft Azure/suite
- Always keep explanations beginner-friendly but technically accurate
- At the end of every development session, explain: what tools were used, why they were
  chosen, and how they work — not just that something works
- Respond in English (Adrián writes in Spanish but reads technical content in English)
- When writing code, always explain what each section does and why
- Preferred working style: build step by step, one script at a time, verify before moving on
