# Themes

A theme controls the report's colours, fonts and the navigation sidebar. Use a built-in or bring
your own Power BI theme JSON.

## Built-in themes

```bash
dashforge themes           # midnight | slate | aurora
```

```python
dashforge.generate(..., theme="midnight")   # deep indigo sidebar, blue/teal data colours
dashforge.generate(..., theme="slate")      # neutral slate, red accent
dashforge.generate(..., theme="aurora")     # deep green sidebar, green/blue data colours
```

## Bring your own

Point `theme` at any standard [Power BI theme JSON](https://learn.microsoft.com/power-bi/create-reports/desktop-report-themes)
and it is applied as-is — drop in your corporate theme:

```python
dashforge.generate(..., theme="./corporate-theme.json")
```

The theme is written into the report as a registered custom theme, so it travels with the project.

### Sidebar colours

dashforge reads two optional convenience keys from a theme document to colour the navigation
sidebar; both are stripped before the theme file is written, so the file stays a valid Power BI
theme:

```json
{
  "name": "Corporate",
  "sidebarColor": "#1B1F3B",
  "accentColor": "#FFFFFF",
  "dataColors": ["#4C6FFF", "#22C1C3", "..."],
  "visualStyles": { "...": {} }
}
```

If you omit them, the sidebar defaults to a dark indigo with white brand text.

## What the layout gives you

Regardless of theme, every page gets a left navigation sidebar (brand strip, stacked filters, a
"how to use this report" note) and a main area with a KPI card row and charts/tables packed by
footprint. The theme decides how it *looks*; the layout decides where things *go*.
