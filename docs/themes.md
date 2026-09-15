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

## Replicate a shared report's shell (`extract-template`)

Reuse the **look** of a report someone shares as a `.pbix` — its theme, colours, fonts, logo — and
pour **your own data** into it:

```bash
pbigen extract-template their_report.pbix --out template
#   template/theme.json          -> their custom theme (if any)
#   template/assets/<logo>.png    -> their logo / background images

pbigen generate --source bigquery --set project=P dataset=D table=T \
  --theme template/theme.json --logo template/assets/<logo>.png --nav right --out out
```

The **theme + logo + nav layout** are matched; your **charts follow your data** (not theirs). If the
shared report used only a built-in theme there's no custom `theme.json` to extract — `--nav`/`--logo`
+ a gallery theme still match the shell. For an *exact* clone of the same report on the same data,
use Power BI Desktop's **File → Save as → `.pbip`** — pbigen reuses the shell, it doesn't clone a
specific report.

## What the layout always gives you

Regardless of theme, every page gets: a navigation sidebar (brand/logo, stacked filters, a "how to
use this report" note), a light canvas, a KPI card row with coloured accent bars, and charts/tables
packed by footprint. The theme decides how it *looks*; the shell flags decide *where* the nav and
logo go.
