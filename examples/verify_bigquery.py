"""Comprehensive verification: generate from BigQuery across model x theme combinations.

Runs four generations from the SAME BigQuery table and reports on each:
  A) deterministic model + built-in theme
  B) Gemini model      + built-in theme
  C) deterministic model + custom theme (examples/custom_theme.json)
  D) Gemini model      + custom theme

For each it prints the model used, page/visual counts, and validates every emitted report JSON
against Microsoft's published PBIR schemas — so you can see the package works end to end before
handing it to the team.

Configure via environment variables:
    export BQ_PROJECT=your-project
    export BQ_DATASET=your_dataset
    export BQ_TABLE=your_table
    export BQ_BILLING_PROJECT=your-billing-project   # optional (defaults to BQ_PROJECT)
    export GEMINI_API_KEY=...                          # for the Gemini runs (Google AI Studio)
    export PBIGEN_GEMINI_MODEL=gemini/gemini-2.5-flash # optional override

Auth for BigQuery introspection uses Application Default Credentials:
    gcloud auth application-default login

Run:  python examples/verify_bigquery.py

Author: Arka Gupta
"""
from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.request

import pbigen

_SCHEMA_CACHE: dict = {}
_SSL = ssl.create_default_context()


def _fetch_schema(uri: str):
    if uri not in _SCHEMA_CACHE:
        with urllib.request.urlopen(uri, timeout=25, context=_SSL) as r:  # noqa: S310
            _SCHEMA_CACHE[uri] = json.loads(r.read().decode())
    return _SCHEMA_CACHE[uri]


def _validate_report_json(report_dir: str) -> tuple[int, list[str]]:
    """Validate every *.json with a $schema under the report definition. Returns (ok_count, errors)."""
    try:
        from jsonschema import Draft7Validator
        from referencing import Registry, Resource
        from referencing.jsonschema import DRAFT7
        reg = Registry(retrieve=lambda u: Resource.from_contents(_fetch_schema(u), default_specification=DRAFT7))
    except Exception:  # noqa: BLE001 - validation is optional tooling
        return (-1, ["(install jsonschema + referencing to validate: pip install jsonschema referencing)"])

    import glob
    ok, errors = 0, []
    for path in glob.glob(os.path.join(report_dir, "definition", "**", "*.json"), recursive=True):
        obj = json.load(open(path))
        su = obj.get("$schema")
        if not su:
            continue
        errs = sorted(Draft7Validator(_fetch_schema(su), registry=reg).iter_errors(obj), key=lambda e: e.path)
        if errs:
            short = path.split("definition/", 1)[1]
            errors.append(f"{short}: {errs[0].message[:120]}")
        else:
            ok += 1
    return (ok, errors)


def _run(label: str, name: str, *, model, theme, cfg: dict) -> None:
    print(f"\n{'='*72}\n{label}\n{'='*72}")
    try:
        result = pbigen.generate(
            "bigquery",
            source_config=cfg,
            objective="Executive overview: key measures by segment over time",
            model=model,
            theme=theme,
            out_dir="out",
            name=name,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"  FAILED: {type(exc).__name__}: {exc}")
        return

    print(f"  model used     : {result.model_name}")
    print(f"  table          : {result.table}  ({result.n_columns} columns)")
    print(f"  pages          : {result.n_pages}  ->  {[p.name for p in result.design.pages]}")
    for p in result.design.pages:
        print(f"     - {p.name}: slicers={p.slicers} visuals={[v.type for v in p.visuals]}")
    report_dir = os.path.join("out", name, f"{name}.Report")
    ok, errors = _validate_report_json(report_dir)
    if ok == -1:
        print(f"  schema check   : skipped — {errors[0]}")
    elif errors:
        print(f"  schema check   : {ok} valid, {len(errors)} INVALID")
        for e in errors[:5]:
            print(f"       ! {e}")
    else:
        print(f"  schema check   : ALL {ok} report files valid against Microsoft's PBIR schemas")
    print(f"  open in Desktop: out/{name}/{name}.pbip")


def main() -> int:
    project = os.environ.get("BQ_PROJECT")
    dataset = os.environ.get("BQ_DATASET")
    table = os.environ.get("BQ_TABLE")
    if not (project and dataset and table):
        print("Set BQ_PROJECT, BQ_DATASET, BQ_TABLE (and run: gcloud auth application-default login).")
        return 2

    cfg = {"project": project, "dataset": dataset, "table": table}
    if os.environ.get("BQ_BILLING_PROJECT"):
        cfg["billing_project"] = os.environ["BQ_BILLING_PROJECT"]

    gemini = os.environ.get("PBIGEN_GEMINI_MODEL", "gemini/gemini-2.5-flash")
    have_key = bool(os.environ.get("GEMINI_API_KEY"))
    theme_file = os.path.join(os.path.dirname(__file__), "custom_theme.json")

    # A) deterministic + built-in theme
    _run("A) deterministic model  +  built-in theme (midnight)", "BQ_A_Deterministic_Builtin",
         model=None, theme="midnight", cfg=cfg)

    # B) Gemini + built-in theme
    if have_key:
        _run(f"B) Gemini ({gemini})  +  built-in theme (midnight)", "BQ_B_Gemini_Builtin",
             model=gemini, theme="midnight", cfg=cfg)
    else:
        print("\nB) SKIPPED — set GEMINI_API_KEY to run the Gemini + built-in theme case.")

    # C) deterministic + custom theme
    _run("C) deterministic model  +  custom theme (examples/custom_theme.json)", "BQ_C_Deterministic_Custom",
         model=None, theme=theme_file, cfg=cfg)

    # D) Gemini + custom theme
    if have_key:
        _run(f"D) Gemini ({gemini})  +  custom theme", "BQ_D_Gemini_Custom",
             model=gemini, theme=theme_file, cfg=cfg)
    else:
        print("\nD) SKIPPED — set GEMINI_API_KEY to run the Gemini + custom theme case.")

    print("\nDone. Open each .pbip in Power BI Desktop (PBIR preview enabled) and Refresh.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
