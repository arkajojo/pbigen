# Template packs — use any `.pbix` as the design

The fastest way to a dashboard that looks like *yours*: take a report you already like, compile it
into a **template pack**, and generate every new dashboard inside it.

```bash
pbigen template build company_standard.pbix --out brand_pack    # once
pbigen template show brand_pack                                 # see what was captured
pbigen generate --source <kind> --set <...> --template brand_pack
```

You can also skip the build step and pass the report directly — pbigen compiles it on the fly:

```bash
pbigen generate --source <kind> --set <...> --template ~/Downloads/company_standard.pbix
```

## Where to get the report

- **Power BI Service:** open the report → *File → Download this file* → *A copy of your report and
  data* (or *a live connection*). Either `.pbix` works — only the layout is read.
- **Power BI Desktop:** *File → Save as* `.pbix`, `.pbit` (template) or `.pbip` (project folder).
- **Gallery / community templates:** any `.pbix`/`.pbit` you are licensed to use.

Accepted inputs: legacy `.pbix`/`.pbit` (the classic `Report/Layout`), PBIR-format `.pbix`, a PBIP
project (`.pbip` file or its `.Report` folder). A report pbigen generated is itself a valid template.

## What a pack captures

pbigen picks the page with the most data visuals as the **reference page** (override with
`--page "Page name"`) and measures it:

| Captured | From | Used for |
|---|---|---|
| **Canvas** | page width/height, background image, wallpaper | every generated page |
| **Content region** | bounding box of their data visuals | where your KPI band and story grid go |
| **Filter rail** | bounding box of their slicers | your filters (stacked if tall, side by side if wide) |
| **Header** | their most prominent title textbox near the top: position, font, size, colour, alignment, background | your page title + the page's headline question |
| **Chrome** | shapes, images, page navigators outside the content (sidebar panels, header bands, logos) + large backdrop panels | copied with exact positions; full-height panels grow when a page grows |
| **Styles** | per visual type, the most-formatted example (borders, radius, shadows, title fonts, backgrounds, labels, slicer look) | merged under pbigen's own bindings on every matching visual |
| **Theme** | the report's custom theme JSON | registered as the report theme (`--theme` overrides) |
| **Assets** | images in the report's registered resources | copied when the background/chrome references them |

## What a pack deliberately leaves out

- **Data and field bindings** — no queries, no columns, no measures.
- **Data-bound formatting** — per-data-point colours with field selectors, conditional formatting
  bound to their measures.
- **Content text** — their visual titles, textbox text, slicer selections and dates.
- **Per-visual decorations inside the content area** — small icons or panels behind individual
  charts (those belonged to *their* layout).
- **Buttons and bookmarks** — they point at pages and bookmarks that won't exist in yours.

Everything left out is exactly what pbigen regenerates for your data. If you need an *exact* clone
of one report on the same data, use Power BI Desktop's *Save as → .pbip*.

## The pack folder

```
brand_pack/
├── pack.json        # canvas, frame (content / filters / header), chrome, title style, styles
├── theme.json       # their custom theme (if the report had one)
└── assets/          # their images (backgrounds, logos, icons)
```

`pack.json` is plain JSON — version it, review it, or tweak it (e.g. nudge the `content` rectangle or
remove a chrome element) and every future dashboard follows.

## Tips

- **Pick the right reference page.** If the report's first page is a cover, point at a real
  dashboard page: `pbigen template build r.pbix --page "Overview"`.
- **No custom theme?** Reports that used a built-in theme have no `theme.json`; the pack still
  carries canvas, chrome and styles. Add `--theme ./corporate.json` at generate time if you like.
- **Tall canvases** (e.g. 2500 × 2500 scroll pages) are preserved; pages that need more room grow
  taller rather than squashing charts.
- **Brand from Python:**

  ```python
  from pbigen.template import build_pack
  pack = build_pack("company_standard.pbix", "brand_pack")
  print(pack.content, pack.filters, pack.title_style)
  ```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `no report layout found` | The file isn't a Power BI report (or is password-protected/encrypted). Re-save it from Desktop. |
| Visuals overlap the report's own sidebar | The reference page had data visuals under the sidebar; choose another page with `--page`. |
| Title lands in the wrong place | The biggest text near the top wasn't the title; edit `header` in `pack.json`. |
| Theme looks default | The report used a built-in theme; pass `--theme` or accept the base theme. |
