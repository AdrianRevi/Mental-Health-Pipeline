# Dashboard Technical Decisions

Decisions made during the design and build of `mental_health_dashboard.pbip`.
Updated as new pages are completed.

---

## Overview Page

### 1. Two fact tables — why grain matters

The model has two fact tables:

- `fact_mental_health` — grain: country × year. Contains GDP, unemployment, overall suicide rate, health indicators. Source: World Bank.
- `fact_suicide_by_age` — grain: country × year × age group × sex. Contains only the suicide rate. Source: WHO SDGSUICIDE.

They were not merged into a single table because adding `age_group` and `sex` to `fact_mental_health` would corrupt all GDP and unemployment measures. Filtering by "Male" would double the GDP (one row per sex per year). This is the **grain concept**: a fact table must have a single, consistent level of detail across all its columns.

---

### 2. "All Ages" — kept as the official WHO aggregate, hidden in the slicer

The WHO SDGSUICIDE indicator includes rows for specific age groups (10-19, 20-29, etc.) **and also** a row `age_group = "All Ages"` representing the total rate calculated by the WHO using population weighting.

**Decision:** keep "All Ages" in the data but hide it from the Age slicer visually (Filters on this visual → deselect "All Ages").

**Why:** if "All Ages" were removed and no age filter was active, the measure would compute a simple average across all groups. A country with a young population and one with an older population would return different numbers even if the underlying reality were the same, because age groups do not carry equal population weight. The WHO "All Ages" value already incorporates that weighting — it is the correct number.

**DAX implementation:** `ISFILTERED(dim_age[age_label])` detects whether the user has selected a specific group. If no filter is active, the measure explicitly forces `age_group = "All Ages"`.

---

### 3. "Both" for sex — same reasoning as "All Ages"

The same principle applied to sex. The value `sex = "Both"` is the official WHO rate for both sexes combined. A simple average of Male + Female would be nearly identical in this case (sex distribution is ~50/50 in all countries), but the same pattern was applied for consistency and technical correctness.

**Decision:** keep "Both" in `fact_suicide_by_age`, hide it from the Sex slicer, use it as the default value when no sex filter is active.

The practical difference vs "All Ages" is small numerically, but the logic is correct and explainable in an interview.

---

### 4. Uneven temporal coverage across dimensions

Exploring `fact_suicide_by_age` revealed:

- `sex = "Both"`, `"Male"`, `"Female"` → data from **2000 to 2021** (22 years)
- Specific age groups (10-19, 20-29, etc.) → **2021 only** (1 year)
- `age_group = "All Ages"` → data from **2000 to 2021** (22 years)

This has direct design implications:
- The historical trend area chart **ignores the age filter** because there is no time series for specific age groups. It does respond to the sex filter (Male/Female have full historical coverage).
- The area chart uses a dedicated measure (`Suicide Rate Trend`) that forces `age_group = "All Ages"` via `REMOVEFILTERS(dim_age)`.

---

### 5. SWITCH(TRUE()) pattern for conditional filtering

The main measure (`Avg Suicide Rate per 100k`) handles 4 possible filter combinations:

| HasAgeFilter | HasSexFilter | Behaviour |
|---|---|---|
| No | No | `All Ages` + `Both` → official WHO total rate |
| Yes | No | selected group + `Both` → official WHO rate for that group |
| No | Yes | `All Ages` + selected sex → historical trend by sex |
| Yes | Yes | selected group + selected sex |

Implemented with `SWITCH(TRUE())` instead of nested `IF` statements for readability.

---

### 6. KEEPFILTERS — why it is required with slicers

`CALCULATE(expr, fact_suicide_by_age[sex] <> "Both")` **replaces** the slicer filter instead of combining with it. If the slicer says `sex = "Male"`, the CALCULATE overrides it with `sex <> "Both"` = Male + Female.

`KEEPFILTERS(fact_suicide_by_age[sex] <> "Both")` **intersects** the new filter with the existing one: `sex = "Male"` ∩ `sex <> "Both"` = `sex = "Male"`. Correct.

Practical rule: use `KEEPFILTERS` whenever adding a condition without breaking existing filter context.

---

### 7. ISFILTERED on age_label, not age_group

The Age slicer filters `dim_age[age_label]`. `ISFILTERED(dim_age[age_group])` returns FALSE even when the slicer is active, because the direct filter is on `age_label`, not `age_group`. Always check `ISFILTERED` against the exact column the slicer uses.

---

### 8. Latest Year Available — static value from actual data

`MAX(dim_year[year])` returns the current year (2026) because `dim_year` is a dynamically generated date table. There is no suicide data for 2026.

The measure uses `ALL(fact_mental_health)` + `NOT ISBLANK(suicide_rate_per_100k)` to retrieve the last year with real data, immune to any dashboard filter.

---

### 9. WHO SDGSUICIDE field formats — discovered in production

The `SDGSUICIDE` WHO indicator uses different code formats from other WHO indicators:

- Age groups: `AGEGROUP_YEARS10-19`, `AGEGROUP_YEARS70PLUS`, `AGEGROUP_YEARSALL` (not `YEARS10-14` or `AGE10-14`)
- Sex: `SEX_BTSX`, `SEX_MLE`, `SEX_FMLE` (not `BTSX`, `MLE`, `FMLE`)
- Age groups are **10-year bands** (10-19, 20-29, etc.), not 5-year bands as initially assumed

`AGE_LABEL_MAP` and `SEX_LABEL_MAP` in `transform_silver.py` were updated to cover only the actual formats used by this indicator.

---

### 10. Two data sources for suicide rate — World Bank vs WHO

The model has **two distinct sources** for the suicide rate:

- `fact_mental_health[suicide_rate_per_100k]` → World Bank (`SH.STA.SUIC.P5`), country × year, no demographic breakdown
- `fact_suicide_by_age[suicide_rate_per_100k]` → WHO SDGSUICIDE, with age and sex breakdown

The numbers are not identical (different methodologies) but are consistent. The Overview uses `fact_suicide_by_age` exclusively for all suicide metrics, as it supports demographic filters. `fact_mental_health` will be used in pages where socioeconomic indicators (GDP, unemployment) are the focus.
