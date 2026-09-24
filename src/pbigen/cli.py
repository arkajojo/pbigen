"""Command-line interface.

    pbigen template build their_report.pbix --out my_pack     # compile a report into a template pack
    pbigen generate --source bigquery --set project=p dataset=d table=t \
                    --template my_pack --model gpt-4o --context brief.md --research web
    pbigen template show my_pack         # what a pack captured
    pbigen doctor --model gpt-4o         # check extras + model credentials
    pbigen sources | themes              # list source kinds / built-in themes
    pbigen test --source lakehouse --set uri=data.parquet fmt=parquet

Config values are passed as ``key=value`` pairs after ``--set`` and forwarded to the adapter.
Integers and booleans are coerced; everything else stays a string.

Author: Arka Gupta
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from . import __version__
from .sources import available_kinds, get_source
from .themes import available_themes


def _coerce(value: str) -> Any:
    low = value.lower()
    if low in ("true", "false"):
        return low == "true"
    if value.isdigit():
        return int(value)
    return value


def _parse_set(pairs: list[str]) -> dict:
    cfg: dict[str, Any] = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise SystemExit(f"--set expects key=value, got {pair!r}")
        key, _, value = pair.partition("=")
        cfg[key.strip()] = _coerce(value.strip())
    return cfg


def _cmd_generate(args: argparse.Namespace) -> int:
    from .core.generator import generate
    cfg = _parse_set(args.set)
    result = generate(
        args.source,
        out_dir=args.out,
        name=args.name,
        objective=args.objective or "",
        model=args.model,
        theme=args.theme,
        mode=args.mode,
        nav=args.nav,
        logo=args.logo,
        source_config=cfg,
        template=args.template,
        context=args.context or "",
        audience=args.audience or "",
        profile=args.profile,
        research=args.research,
        critique=not args.no_critique,
        compare_days=args.compare_days,
    )
    shell = f"template '{result.template}'" if result.template else "pbigen shell"
    print(f"Generated {result.n_pages} pages from {result.table} "
          f"({result.n_columns} columns) using {result.model_name}, in the {shell}.")
    print(f"Open:   {result.pbip_path}")
    print(f"Why:    {result.design_md}   (business context, KPI tree, storyline)")
    print("Tip:    Power BI Desktop > Options > Preview features > enable "
          "'Store reports using enhanced metadata format (PBIR)'. Keep the .pbip, .Report and "
          ".SemanticModel together; sign in to the source when prompted, then Refresh.")
    return 0


def _cmd_template_build(args: argparse.Namespace) -> int:
    from .template.pack import build_pack, describe
    out = args.out or os.path.splitext(os.path.basename(args.report.rstrip("/")))[0] + "_pack"
    pack = build_pack(args.report, out, page=args.page, name=args.name)
    print(describe(pack))
    print(f"\nSaved template pack -> {out}/")
    print(f"Use it:  pbigen generate --source <kind> --set <...> --template {out}")
    return 0


def _cmd_template_show(args: argparse.Namespace) -> int:
    from .template.pack import describe, load_pack
    print(describe(load_pack(args.pack)))
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    import importlib.util
    import platform
    ok = True
    print(f"pbigen {__version__} · Python {platform.python_version()}")
    extras = {"bigquery": "google.cloud.bigquery", "sqlalchemy": "sqlalchemy", "lakehouse": "duckdb",
              "cube": "requests", "llm": "litellm"}
    for extra, mod in extras.items():
        try:
            present = importlib.util.find_spec(mod) is not None
        except (ModuleNotFoundError, ValueError):
            present = False
        print(f"  {'✓' if present else '·'} {extra:<10} {'installed' if present else f'not installed (pip install pbigen[{extra}])'}")
    if args.model:
        try:
            import litellm
            resp = litellm.completion(model=args.model, max_tokens=5,
                                      messages=[{"role": "user", "content": "Reply with OK"}])
            print(f"  ✓ model {args.model} answered: {resp['choices'][0]['message']['content']!r}")
            try:
                web = litellm.supports_web_search(model=args.model) or args.model.lower().startswith(("anthropic/", "claude"))
            except Exception:  # noqa: BLE001
                web = False
            print(f"  {'✓' if web else '·'} web research {'available' if web else 'not available — --research web falls back to built-in'}")
        except Exception as exc:  # noqa: BLE001
            ok = False
            print(f"  ✗ model {args.model}: {type(exc).__name__}: {str(exc)[:200]}")
            print("    set the provider key (e.g. OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY) in this shell")
    return 0 if ok else 1


def _cmd_sources(_: argparse.Namespace) -> int:
    print("Available sources:")
    for kind in available_kinds():
        print(f"  - {kind}")
    return 0


def _cmd_themes(_: argparse.Namespace) -> int:
    print("Built-in themes (or pass a path to your own Power BI theme JSON):")
    for name in available_themes():
        print(f"  - {name}")
    return 0


def _cmd_extract_template(args: argparse.Namespace) -> int:
    from .reference import extract_template
    r = extract_template(args.pbix, args.out)
    print(f"Extracted design shell from {args.pbix} into {args.out}/")
    if r.theme_path:
        print(f"  theme  -> {r.theme_path}   (from {r.theme_source})")
    else:
        print("  theme  -> none found (the report likely uses a built-in theme; use --nav/--logo/--canvas)")
    if r.images:
        print(f"  images -> {args.out}/assets/: {', '.join(r.images)}")
    else:
        print("  images -> none found")
    logo = f" --logo {args.out}/assets/{r.images[0]}" if r.images else ""
    theme = f" --theme {r.theme_path}" if r.theme_path else ""
    print("\nNext, generate your data into the same shell, e.g.:")
    print(f"  pbigen generate --source <kind> --set <...>{theme}{logo} --nav right --out out")
    return 0


def _cmd_test(args: argparse.Namespace) -> int:
    src = get_source(args.source, **_parse_set(args.set))
    result = src.test_connection()
    print(result.message)
    return 0 if result.ok else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pbigen",
                                description="Generate Power BI dashboards from any data source.")
    p.add_argument("--version", action="version", version=f"pbigen {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    g = sub.add_parser("generate", help="generate a Power BI project from a source")
    g.add_argument("--source", required=True, help=f"source kind ({', '.join(available_kinds())})")
    g.add_argument("--set", nargs="*", default=[], help="source config as key=value pairs")
    g.add_argument("--template", help="template pack folder, or a .pbix/.pbit/.pbip to use as the design shell")
    g.add_argument("--objective", help="what the dashboard should answer")
    g.add_argument("--context", help="business context: text, or a path to a brief/notes file")
    g.add_argument("--audience", help="who reads it, e.g. 'COO and regional ops managers'")
    g.add_argument("--model", help="LiteLLM model id for the AI design pipeline (omit for deterministic)")
    g.add_argument("--research", choices=["builtin", "web", "off"], default="builtin",
                   help="research stage: built-in playbooks (default), live web search, or off")
    g.add_argument("--profile", action="store_true",
                   help="send aggregate value profiles (min/max/top values, never rows) to the model")
    g.add_argument("--no-critique", action="store_true", help="skip the design critique & repair stage")
    g.add_argument("--compare-days", type=int, default=30,
                   help="KPI card delta window: last N days vs the prior N (default 30)")
    g.add_argument("--theme", help="built-in theme name or path to a Power BI theme JSON (overrides a template's)")
    g.add_argument("--mode", choices=["import", "directquery"], default="import",
                   help="storage mode: import (default, loads a copy) or directquery (live queries)")
    g.add_argument("--nav", choices=["left", "right"], default="left",
                   help="navigation sidebar side for the pbigen shell (default: left)")
    g.add_argument("--logo", help="path to a logo image (png/jpg) for the pbigen shell's sidebar")
    g.add_argument("--out", default="out", help="output directory (default: out)")
    g.add_argument("--name", help="project name (default: derived from the table)")
    g.set_defaults(func=_cmd_generate)

    tp = sub.add_parser("template", help="build or inspect template packs from your own reports")
    tsub = tp.add_subparsers(dest="template_command", required=True)
    tb = tsub.add_parser("build", help="compile a .pbix/.pbit/.pbip report into a reusable template pack")
    tb.add_argument("report", help="path to a .pbix, .pbit, .pbip or .Report folder")
    tb.add_argument("--out", help="pack folder (default: <report>_pack)")
    tb.add_argument("--page", help="reference page name (default: the page with the most visuals)")
    tb.add_argument("--name", help="pack name (default: the report file name)")
    tb.set_defaults(func=_cmd_template_build)
    ts = tsub.add_parser("show", help="describe what a template pack captured")
    ts.add_argument("pack", help="template pack folder")
    ts.set_defaults(func=_cmd_template_show)

    d = sub.add_parser("doctor", help="check installed extras and (optionally) a model's credentials")
    d.add_argument("--model", help="LiteLLM model id to test, e.g. gpt-4o or gemini/gemini-2.5-flash")
    d.set_defaults(func=_cmd_doctor)

    t = sub.add_parser("test", help="test connectivity + introspection for a source")
    t.add_argument("--source", required=True)
    t.add_argument("--set", nargs="*", default=[])
    t.set_defaults(func=_cmd_test)

    e = sub.add_parser("extract-template",
                       help="(legacy) extract only theme + images from a .pbix — prefer `template build`")
    e.add_argument("pbix", help="path to a .pbix file")
    e.add_argument("--out", default="template", help="output directory (default: template)")
    e.set_defaults(func=_cmd_extract_template)

    sub.add_parser("sources", help="list available source kinds").set_defaults(func=_cmd_sources)
    sub.add_parser("themes", help="list built-in themes").set_defaults(func=_cmd_themes)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv if argv is not None else sys.argv[1:])
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
