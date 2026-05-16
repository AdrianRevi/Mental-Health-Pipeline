# Mental Health Pipeline — Claude Code Context

## Project
End-to-end ETL pipeline on public mental health data (WHO, World Bank).
Goal: portfolio-ready project for junior Data Engineer interviews.
Owner: Adrian | Started: May 2026 | Cost: €0

## Current Status
Pipeline complete — all 5 scripts written and running on GitHub Actions.
Next: Power BI dashboard (`mental_health_dashboard.pbix`).

## Tech Stack
- Language: Python 3.11+
- Transformation: pandas
- Storage: local files + DuckDB
- Data Quality: Great Expectations 0.17.x
- Orchestration: GitHub Actions
- Output (optional): Power BI Desktop

## Architecture
Bronze (raw CSVs) → Silver (cleaned .parquet) → Gold (star schema) → DuckDB → Power BI

## Instructions for Claude
- Adrian is a junior data analyst/engineer — keep explanations beginner-friendly but technically accurate
- Build step by step, one script at a time; verify before moving on
- Always explain what each code section does AND why it was written that way
- At the end of every dev session: summarize tools used, why chosen, how they work
- Respond in English (Adrian writes in Spanish but reads technical content in English)
- Prefer free, local tooling — no cloud costs
- Suggest things that are interview-relevant for junior DE roles

## Key Files
- `data/bronze/` — raw CSVs, never modified
- `data/silver/` — cleaned .parquet files
- `data/gold/` — star schema (dim_country, dim_year, fact_mental_health)
- `data/mental_health.duckdb` — analytical database (gitignored)
- `scripts/` — Python ETL scripts (ingest → silver → quality → gold → duckdb)
- `.github/workflows/pipeline.yml` — GitHub Actions orchestration
- `requirements.txt` — GX pinned to `>=0.17,<0.18` (0.18+ broke the fluent API)
