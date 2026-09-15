"""Command-line interface.

    dashforge generate --source bigquery --set project=p dataset=d table=t --theme midnight
    dashforge sources                       # list available source kinds
    dashforge themes                        # list built-in themes
    dashforge test --source lakehouse --set uri=data.parquet fmt=parquet

Config values are passed as ``key=value`` pairs after ``--set`` and forwarded to the adapter.
Integers and booleans are coerced; everything else stays a string.

Author: Arka Gupta
"""
from __future__ import annotations

import argparse
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
        source_config=cfg,
    )
    print(f"Generated {result.n_pages} pages from {result.table} "
          f"({result.n_columns} columns) using {result.model_name}.")
    print(f"Open: {result.pbip_path}")
    return 0


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


def _cmd_test(args: argparse.Namespace) -> int:
    src = get_source(args.source, **_parse_set(args.set))
    result = src.test_connection()
    print(result.message)
    return 0 if result.ok else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dashforge",
                                description="Generate Power BI dashboards from any data source.")
    p.add_argument("--version", action="version", version=f"dashforge {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    g = sub.add_parser("generate", help="generate a Power BI project from a source")
    g.add_argument("--source", required=True, help=f"source kind ({', '.join(available_kinds())})")
    g.add_argument("--set", nargs="*", default=[], help="source config as key=value pairs")
    g.add_argument("--objective", help="what the dashboard should answer")
    g.add_argument("--model", help="LiteLLM model id (omit for the deterministic design)")
    g.add_argument("--theme", help="built-in theme name or path to a Power BI theme JSON")
    g.add_argument("--out", default="out", help="output directory (default: out)")
    g.add_argument("--name", help="project name (default: derived from the table)")
    g.set_defaults(func=_cmd_generate)

    t = sub.add_parser("test", help="test connectivity + introspection for a source")
    t.add_argument("--source", required=True)
    t.add_argument("--set", nargs="*", default=[])
    t.set_defaults(func=_cmd_test)

    sub.add_parser("sources", help="list available source kinds").set_defaults(func=_cmd_sources)
    sub.add_parser("themes", help="list built-in themes").set_defaults(func=_cmd_themes)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv if argv is not None else sys.argv[1:])
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
