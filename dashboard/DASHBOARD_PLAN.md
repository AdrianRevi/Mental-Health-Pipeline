# Mental Health Dashboard — Plan

## Páginas

---

### Página 1 — Overview
Portada ejecutiva con los números clave de un vistazo.

**Visuals:**
- 4 KPI cards: avg suicide rate global, países cubiertos, rango de años, avg outpatient facilities
- Line chart: evolución del avg global de `suicide_rate_per_100k` por año
- Bar chart: top 10 países con mayor tasa de suicidio (año seleccionado)

**Filtros:** slicer de año

---

### Página 2 — World Map
El visual más impactante — mapa coroplético mundial.

**Visuals:**
- Filled map: `suicide_rate_per_100k` por país (color gradient)
- Tooltips: país, región, income level, tasa, año
- KPI card con el país más alto y más bajo del año seleccionado

**Filtros:** slicer de año, slicer de región, slicer de income level

---

### Página 3 — Socioeconomic Correlations
Cuenta la historia analítica — relación entre economía y salud mental.

**Visuals:**
- Scatter plot: `gdp_per_capita` (eje X) vs `suicide_rate_per_100k` (eje Y), puntos = países, color = región
- Scatter plot: `unemployment_rate` (eje X) vs `suicide_rate_per_100k` (eje Y), color = income level
- Tabla resumen: correlaciones por región

**Filtros:** slicer de año, slicer de región

---

### Página 4 — Resources & Access
Análisis de infraestructura de salud mental por país y nivel de ingresos.

**Visuals:**
- Bar chart: avg `outpatient_facilities` por `income_level`
- Scatter plot: `outpatient_facilities` vs `suicide_rate_per_100k` por país
- Tabla: países con menor acceso (bottom 20 en outpatient facilities)

**Filtros:** slicer de región, slicer de income level, slicer de año

---

## Diseño (Figma)

- **Canvas:** 1280×720 px
- **Estilo:** dark theme — fondo `#0d1117` o `#1a1a2e`
- **Acento:** teal `#00b4d8` o violeta `#7c3aed`
- **Exportar:** PNG → Power BI como wallpaper (View → Wallpaper) o imagen de fondo por página
- **Referencia:** buscar "Power BI dark dashboard" en Figma Community

## Campos disponibles

| Tabla | Campos |
|---|---|
| `fact_mental_health` | `suicide_rate_per_100k`, `gdp_per_capita`, `unemployment_rate`, `outpatient_facilities` |
| `dim_country` | `country`, `region`, `income_level`, `capital_city` |
| `dim_year` | `year`, `decade`, `period_label` |
