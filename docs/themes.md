# Themes, logo & the design shell

A theme controls the report's **colours, fonts and visual styling**; the **layout shell** (nav side,
logo, canvas) is controlled by flags. Together they let you match any house style.

## Built-in themes

```bash
pbigen themes           # midnight | slate | aurora
```

```python
pbigen.generate(..., theme="midnight")   # deep indigo sidebar, blue/teal data colours
pbigen.generate(..., theme="slate")      # neutral slate, red accent
pbigen.generate(..., theme="aurora")     # deep green sidebar, green/blue data colours
```

Each is a polished executive look: light canvas, white raised cards with coloured KPI accent bars,
big numbers, soft shadows, refined type, tidy legends.

## Bring your own theme

Point `--theme` (CLI) or `theme=` (Python) at any standard
[Power BI theme JSON](https://learn.microsoft.com/power-bi/create-reports/desktop-report-themes):

```bash
pbigen generate ... --theme ./corporate-theme.json
```
```python
pbigen.generate(..., theme="./corporate-theme.json")
```

The theme is copied into the report's registered resources (`<name>.Report/StaticResources/…`), so it
travels with the project. Files with a UTF-8 BOM (common from the gallery / Windows) load fine.

**Where to get themes:** the [Power BI Community Theme Gallery](https://community.fabric.microsoft.com/t5/Themes-Gallery/bd-p/ThemesGallery)
(click *Download*), Microsoft's [samples repo](https://github.com/microsoft/powerbi-desktop-samples),
or export the one applied in a report from Power BI Desktop → *View → Themes → Save current theme*.

### The two convenience keys: `sidebarColor` / `accentColor`

pbigen reads two optional keys to colour the **navigation sidebar**; both are stripped before the
theme file is written, so it stays a valid Power BI theme:

```json
{
  "name": "Corporate",
  "sidebarColor": "#1B1F3B",
  "accentColor": "#FFFFFF",
  "dataColors": ["#4C6FFF", "#22C1C3", "..."],
  "visualStyles": { "...": {} }
}
```

- If `sidebarColor` is **absent**, pbigen derives a cohesive nav colour from the theme's own dark
  brand colour (`foreground`/`maximum`), falling back to a dark indigo.
- Set `sidebarColor` (and optionally `accentColor`) explicitly to control the nav exactly.

> A theme only carries colours/fonts/visual styles — **not** the sidebar/background of some other
> report. To match a specific nav colour, set `sidebarColor` in the theme JSON.

## Layout shell — nav side, logo, canvas

```bash
pbigen generate ... --nav right                 # sidebar on the right (default: left)
pbigen generate ... --logo ./assets/logo.png    # a logo image in the nav sidebar
```

- `--nav left|right` mirrors the whole shell (sidebar, filters, logo, notes).
- `--logo` copies the image into the report's registered resources and binds it as an image visual;
  it replaces the text brand strip. If the path doesn't exist, pbigen warns and skips it.

## Reuse a whole report's design — template packs

A theme only carries colours, fonts and visual-style defaults. To reuse a report's *entire* look —
canvas, background, sidebar and header chrome, logo, title font and per-visual formatting — compile
it into a **template pack**:

```bash
pbigen template build their_report.pbix --out brand_pack
pbigen generate --source bigquery --set project=P dataset=D table=T --template brand_pack --out out
```

See [Template packs](templates.md). (The older `pbigen extract-template` still works and extracts
only the theme + images.)

## What the layout always gives you

In pbigen's own shell (no template), every page gets: a navigation sidebar (brand/logo, stacked
filters, a "how to use this report" note), a light canvas, a header with the page title and its
headline question, a KPI band with coloured accent bars and period-over-period deltas, and a
12-column story grid (hero + side, halves, thirds, full width). The theme decides how it *looks*; the shell flags decide *where* the nav and
logo go.
