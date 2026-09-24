# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project adheres to semantic versioning.

## [0.4.0]

A re-foundation around two ideas: **reuse the design of a report you already have**, and **design
the story the way a senior BI consultant would**.

### Added

- **Template packs** — `pbigen template build <report.pbix|.pbit|.pbip> --out pack` compiles any
  report into a reusable design: canvas size, page background/wallpaper, the content region, filter
  rail and header measured from its richest page, chrome (sidebar panels, header bands, logos, page
  navigators), the title font/size/colour, per-visual-type formatting (borders, radius, shadows,
  title fonts, slicer look) with every data binding stripped, and its theme + images.
  `pbigen template show pack` describes it. `generate --template` accepts a pack **or a report file
  directly** (compiled on the fly). Reads legacy layouts and PBIR (incl. `.pbip` folders).
- **The AI design pipeline** (`--model`) — five expert stages with a curated knowledge base (IBCS,
  Few, Knaflic, Minto + 10 domain KPI playbooks) and strict JSON contracts: business context →
  objectives & KPI tree (with data gaps) → research → storyboard → critique & repair. Progress is
  printed per stage; any stage can fail without sinking the run.
- **Web research** — `--research web` uses live web search on providers that support it
  (OpenAI search models / GPT-5, Anthropic, Gemini) and cites sources; `builtin` (default) / `off`.
- **Opt-in data profiling** — `--profile` sends aggregates (min/max/avg, date ranges, top 5 values
  of low-cardinality text columns — never rows) to the model; implemented for BigQuery, every
  SQLAlchemy warehouse and the DuckDB lakehouse adapter.
- **Business context** — `--context` (text or a file path) and `--audience`.
- **`DESIGN.md`** next to every report: context, column meanings, objectives, KPI tree, research
  findings + sources, storyline with each visual's purpose, critique changes, gaps, caveats, stage log.
- **KPI cards with period-over-period deltas** — "▲ 4.2% vs prior 30 days" in the card subtitle,
  coloured green/red by whether the change is good for that KPI (`--compare-days`).
- **"About this report" page** — purpose, objectives, story flow, KPI definitions with direction,
  how to use, data source/grain/caveats/gaps.
- **Monthly trend grain** — a calculated `<date> Month` column (import mode); trends never plot raw
  timestamps.
- **New visuals** — combo (columns + line), waterfall, treemap (with a second level); subtitles on
  every visual; ranked (sorted) category charts; data labels.
- **KPI-on-KPI formulas** — `divide`, `add`, `subtract`, `multiply` (e.g. `Net Revenue = Gross −
  Discount`, `AOV = Revenue ÷ Orders`).
- **12-column editorial layout** — KPI band, hero + side, halves, thirds, full width; pages grow
  taller instead of squashing charts; layout works inside any template frame.
- `pbigen doctor [--model]` — installed extras, model credentials and web-research availability.

### Changed

- The deterministic engine now tells a story too: KPIs named after the grain (`Orders`, `Trips`),
  distinct-entity and efficiency KPIs, lower-is-better detection, a domain playbook, a question per
  page, a subtitle per visual, donuts only for ≤ 6 slices (ranked bars otherwise).
- `Model.design(schema, objective, request=None)` gains a `DesignRequest` (context, audience,
  research mode, critique). Custom models written for 0.3 keep working.
- `pbigen extract-template` is kept for compatibility; `template build` supersedes it.

## [0.3.4]

### Docs

- Added an **independent-project disclaimer** to the README and `AUTHORS.md`: pbigen is a personal
  open-source project, developed on personal time/equipment, using no employer code/data/systems,
  and is not affiliated with or endorsed by any employer.

## [0.3.3]

### Docs

- **README links resolve on PyPI.** Relative links (`docs/…`, `CONTRIBUTING.md`, `LICENSE`, …) are
  now absolute GitHub URLs, so they work on the PyPI/TestPyPI project pages (relative links there
  404'd).
- **Documentation website** — a MkDocs Material site (`mkdocs.yml` + `docs/index.md`) published to
  GitHub Pages via `.github/workflows/docs.yml`, with a `docs` extra and a Documentation project URL.

## [0.3.2]

### Fixed

- **A measure can never emit a broken column reference.** As a defense-in-depth complement to the
  0.3.1 parse-time drop, the DAX writer now degrades any measure that references a non-existent
  column (or an invalid ratio) to a safe `COUNTROWS` instead of `SUM('t'[missing])`, so an
  LLM-invented measure can't error a visual ("Something's wrong with one or more fields") even if it
  slips past parsing. The deterministic path (always valid columns) is unaffected.

## [0.3.1]

### Fixed

- **LLM-proposed measures that reference a non-existent column are now dropped** (and any visual left
  empty by that is removed), so an LLM design can't produce cards that error with "Something's wrong
  with one or more fields." COUNT measures still work with or without a column.
- **`--logo` warns instead of silently skipping** when the image path doesn't exist.

### Changed

- **Bring-your-own / extracted themes get a cohesive nav colour** — when a theme JSON defines no
  `sidebarColor`, pbigen derives it from the theme's own dark brand colour (`foreground`/`maximum`)
  instead of a fixed default. (Set `sidebarColor`/`accentColor` in the theme to override.)

## [0.3.0]

### Added — replicate a report's design shell

- **`--nav left|right`** — put the navigation sidebar on either side (match a "right nav panel").
- **`--logo <image>`** — drop a logo image into the nav sidebar (copied into the report's registered
  resources and bound as an image visual).
- **`pbigen extract-template <file.pbix> --out <dir>`** — pull the reusable design shell out of a
  shared `.pbix`: its custom **theme** (colours/fonts/visual styles) → `theme.json`, and its
  **images** (logo/background) → `assets/`. Then regenerate *your* data into that shell:
  `pbigen generate ... --theme <dir>/theme.json --logo <dir>/assets/<logo> --nav right`.
  It reuses the look (theme, logo, nav layout) — your charts still follow your data, not theirs.
  (A report that used only a built-in theme has no custom theme to extract; `--nav`/`--logo` still
  match the shell.)

## [0.2.1]

### Fixed

- **Equal padding below the page title.** The KPI card row started flush against the title; it now
  sits one gap below it, matching the spacing between every other row.

## [0.2.0]

### Changed — executive aesthetics pass

- **Light canvas** behind every page, so the white visuals read as raised, executive-style panels.
- **Coloured accent bars** down the left edge of each KPI card (cycled from the theme palette) — the
  modern KPI-card look.
- **Richer built-in themes** (midnight / slate / aurora): big semibold KPI numbers with muted
  category labels, white rounded cards with a soft drop shadow, refined title typography, softened
  gridlines, tidier legends, and a proper donut inner radius.
- **More breathing room** — taller KPI cards and larger gaps/margins.

All output remains schema-valid against Microsoft's PBIR schemas and opens in Power BI Desktop; the
report structure, custom-theme handling, DirectQuery/import, and every prior fix are unchanged.
Custom themes still apply as before (structural polish — canvas, accent bars, spacing — is
theme-independent, so a bring-your-own theme also benefits).

## [0.1.6]

### Fixed

- **Custom themes now actually apply.** The theme resource was written under
  `definition/StaticResources/…`, but Power BI resolves registered resources from
  `<name>.Report/StaticResources/…` (a sibling of `definition/`). It's now written there, so the
  custom theme is picked up instead of silently falling back to the default.

## [0.1.5]

### Fixed

- **Custom theme files with a UTF-8 BOM now load.** Theme JSONs downloaded from the Power BI theme
  gallery or exported on Windows often begin with a byte-order mark; the loader now reads them with
  `utf-8-sig` instead of failing with "Unexpected UTF-8 BOM".
- **Sidebar brand strip is now black text on a white card** — legible on any sidebar colour (the
  earlier transparent approach left white text unreadable on light themes).

## [0.1.4]

### Fixed

- **Sidebar brand strip was white-on-white.** The theme's default white fill was landing on the
  brand textbox, hiding the white brand text in a white box on the coloured sidebar. Textboxes with
  no explicit background are now transparent, so the brand text shows on the navigation colour (and
  the page title shows on the white page); the "how to use" note keeps its intentional white box.

## [0.1.3]

### Fixed

- **White-on-white visual title header.** With the stylable visual-container header enabled, the
  chart title is now written to `visualContainerObjects.title` (which the theme colours), and chrome
  visuals (textboxes, the sidebar shape, cards, slicers) explicitly hide that header — so no blank
  white title bar renders over them.

### Added

- **Row sampling** for BigQuery: pass `row_limit=<N>` (e.g. `--set … row_limit=50000`) to build and
  refresh against a `Table.FirstN` sample instead of a huge table — fast iteration on big sources.
- **Import vs DirectQuery** storage mode: `--mode import` (default, loads a copy) or
  `--mode directquery` (live queries), threaded into the TMDL partition mode. Python:
  `pbigen.generate(..., mode="directquery")`.

## [0.1.2]

### Fixed

- **BigQuery refresh on locked-down networks.** The generated Power Query now sets
  `UseStorageApi=false`, so refresh falls back to the REST API instead of the BigQuery Storage Read
  API — fixing `Storage API Error: failed to connect to all addresses` where a firewall blocks the
  storage endpoint.
- **Numeric geo/id codes are no longer summed into nonsense measures.** Census tracts, community
  areas, lat/long, ward/district/FIPS/zip codes are classified as geographies, not measures — no
  more "Total Pickup Census Tract".
- **No more "too many columns in the Legend bucket".** A field is only placed on a chart legend /
  matrix column when it has very few distinct values; high-cardinality dimensions become a bar
  category instead.

### Changed

- **Cleaner, more executive design.** Every table leads with a guaranteed-populated **Record Count**
  KPI; rate/ratio columns are averaged (not summed); charts use fewer measures with clear single-
  subject titles ("Revenue by Region"); the detail table is focused rather than every-field.

## [0.1.1]

### Fixed

- **Reports now open in Power BI Desktop.** `version.json` was missing its `$schema`, which current
  Desktop rejects on load ("Can't find '$schema' property in 'version.json'"). It is now written
  with the `versionMetadata/1.0.0` schema.
- **Custom themes now apply.** The report is written with a base theme + a `customTheme` named by its
  registered-resource **file name**, plus the `resourcePackages` declaration Power BI expects — the
  previous output named the theme by its display name and omitted the resource package, so the theme
  failed to resolve.

### Changed

- **Honest model reporting.** When an LLM can't be reached and generation falls back to the
  deterministic design, the result now says so (e.g. `deterministic (fallback — … did not run …)`)
  instead of reporting the requested model as if it ran. The model backend also prints a one-line
  reason to stderr on fallback.

## [0.1.0]

Initial release.

### Added

- Source adapters with one read-only introspect / cardinality / connect contract:
  - BigQuery, BigLake, BigQuery Omni
  - Redshift, Athena, Snowflake, Synapse/Fabric, Databricks, ClickHouse, PostgreSQL
  - Parquet, Apache Iceberg and Delta Lake on local disk, GCS, S3 or ADLS (DuckDB)
  - Cube semantic layer
- Deterministic, cardinality-aware design engine (charts and filters chosen from data shape).
- Optional LLM design refinement through LiteLLM (bring your own hosted or local model); metadata
  only, with schema-validated output and graceful fallback.
- Power BI emitter producing an openable PBIP project: PBIR report with a navigation sidebar,
  KPI cards, data-appropriate visuals and usage notes, plus a TMDL semantic model wired to the
  source. Output validates against Microsoft's published PBIR schemas.
- Built-in themes (midnight, slate, aurora) and bring-your-own Power BI theme JSON support.
- `pbigen` CLI (`generate`, `test`, `sources`, `themes`) and a `pbigen.generate()` Python API.
