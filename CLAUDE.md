# Mental Health Pipeline — Claude Code Context

## Project
End-to-end ETL pipeline on public mental health data (WHO, Our World in Data, World Bank).
Goal: portfolio-ready project for junior Data Engineer interviews.
Owner: Adrian | Started: May 2026 | Cost: €0

## Current Status
- Week 1 of 6 — not started
- See `project-brief.md` for full roadmap and architecture details

## Tech Stack
- Language: Python 3.11+
- Transformation: pandas + PySpark (basic)
- Storage: local files + DuckDB
- Data Quality: Great Expectations
- Orchestration: GitHub Actions
- Output (optional): Power BI Desktop

## Architecture
Bronze (raw CSVs) → Silver (cleaned .parquet) → Gold (aggregates) → DuckDB → Power BI

## Instructions for Claude
- Adrian is a junior data analyst/engineer — keep explanations beginner-friendly but technically accurate
- Build step by step, one script at a time; verify before moving on
- Always explain what each code section does AND why it was written that way
- At the end of every dev session: summarize tools used, why chosen, how they work
- Respond in English (Adrian writes in Spanish but reads technical content in English)
- Prefer free, local tooling — no cloud costs
- Suggest things that are interview-relevant for junior DE roles

## Key Files
- `project-brief.md` — full project brief, roadmap, folder structure, interview pitch
- `data/bronze/` — raw CSVs, never modified
- `data/silver/` — cleaned .parquet files
- `data/gold/` — aggregated tables
- `scripts/` — Python ETL scripts
- `.github/workflows/pipeline.yml` — GitHub Actions orchestration
