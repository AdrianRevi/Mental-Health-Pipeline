# Mental Health Dashboard — Plan

## Páginas

---

### Página 1 — Overview
Portada ejecutiva con los números clave de un vistazo.

#### Fondo Figma
Canvas `1280×720` · Fondo `#080808` · Exportar como PNG y cargar en Power BI como Wallpaper.
Estructura: Top Bar (Y:0–80) · Sidebar (X:0–140) · Footer (Y:694–720) · 8 cards de contenido.

#### Paleta de acentos
| Color | Hex | Aparece en |
|---|---|---|
| Teal | `#0D9488` | Line chart · KPI 4 |
| Cyan | `#06B6D4` | KPI 3 · Highlight card |
| Indigo | `#6366F1` | KPI 1 · Bar chart |
| Violet | `#8B5CF6` | KPI 2 · Slicer |

#### Cards — layout exacto
Todas las cards: Fill `#0C0C10` · Stroke `#17171F` 0.8px · Corner radius 8 · Accent line H:2px en la parte superior.

| Card Figma | X | Y | W | H | Accent | Visual Power BI |
|---|---|---|---|---|---|---|
| `card-line-chart` | 156 | 96 | 680 | 320 | Teal | Line chart |
| `card-kpi-1` | 848 | 96 | 200 | 152 | Indigo | KPI avg suicide rate |
| `card-kpi-2` | 1060 | 96 | 204 | 152 | Violet | KPI países cubiertos |
| `card-kpi-3` | 848 | 260 | 200 | 156 | Cyan | KPI rango de años |
| `card-kpi-4` | 1060 | 260 | 204 | 156 | Teal | KPI avg outpatient facilities |
| `card-slicer` | 156 | 428 | 326 | 254 | Violet | Slicer de año |
| `card-bar-chart` | 494 | 428 | 354 | 254 | Indigo | Bar chart top 10 países |
| `card-highlight` | 860 | 428 | 404 | 254 | Cyan | Highlight — país con tasa más alta + delta vs año anterior |

#### Visuals — detalle de campos

**Line chart** — evolución temporal
- Eje X: `dim_year[year]`
- Eje Y: `AVG(fact_mental_health[suicide_rate_per_100k])`
- Sin leyenda · línea color `#0D9488` · fondo transparente

**KPI 1 — Avg suicide rate global**
- Valor: `AVG(fact_mental_health[suicide_rate_per_100k])`
- Unidad: per 100k

**KPI 2 — Países cubiertos**
- Valor: `DISTINCTCOUNT(dim_country[country])`

**KPI 3 — Rango de años**
- Valor: texto dinámico `MIN(year) – MAX(year)`

**KPI 4 — Avg outpatient facilities**
- Valor: `AVG(fact_mental_health[outpatient_facilities])`

**Bar chart — Top 10 países**
- Eje Y: `dim_country[country]`
- Eje X: `AVG(fact_mental_health[suicide_rate_per_100k])`
- Top N filter: 10 · ordenado descendente · barras color `#6366F1`

**Highlight card — País con tasa más alta**
- País con `MAX(suicide_rate_per_100k)` del año seleccionado
- Delta vs año anterior
- Implementar como card con medidas DAX

**Slicer de año**
- Campo: `dim_year[year]`
- Estilo: vertical list o between (rango)

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

- **Canvas:** 1280×720 px · Fondo `#080808`
- **Estructura:** Top Bar (H:80) · Sidebar (W:140) · Footer (H:26) · Cards de contenido
- **Top bar:** degradado `#0A0A0A → #1A1A1E → #0A0A0A` · accent line 2px `#0D9488 → #6366F1`
- **Sidebar:** franja accent 4px izquierda `#0D9488 → #6366F1 → #6366F130`
- **Paleta de acentos:** Teal `#0D9488` · Cyan `#06B6D4` · Indigo `#6366F1` · Violet `#8B5CF6`
- **Exportar:** PNG por página → Power BI View → Wallpaper
- **Títulos y navegación:** nativos de Power BI (no en Figma)

## Campos disponibles

| Tabla | Campos |
|---|---|
| `fact_mental_health` | `suicide_rate_per_100k`, `gdp_per_capita`, `unemployment_rate`, `outpatient_facilities` |
| `dim_country` | `country`, `region`, `income_level`, `capital_city` |
| `dim_year` | `year`, `decade`, `period_label` |
