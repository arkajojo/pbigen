# Contributing to dashforge

Thanks for taking the time to contribute. dashforge aims to make good BI dashboards fall out of a
table and an objective — contributions that keep it correct, portable and pleasant to use are very
welcome.

## Getting set up

```bash
git clone https://github.com/arkajojo/dashforge
cd dashforge
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,lakehouse,sqlalchemy]"
```

Run the checks before opening a pull request:

```bash
ruff check src tests
pytest
```

The test suite runs entirely offline (Parquet via DuckDB, SQLite via SQLAlchemy) — no cloud
credentials required.

## Design principles

- **Portable core.** `core/` must not import a database driver or a cloud SDK. All vendor specifics
  live in `sources/` and `emit/`.
- **Metadata only.** Sources read schema and cardinality, never row data. Models see metadata only.
- **Never fail hard.** Best-effort steps (cardinality, LLM design) degrade gracefully.
- **Data-shape-driven.** Chart and filter choices follow from types and cardinality, not guesswork.

## Adding a source

1. Subclass `Source` (or `SqlSource` if it has a SQLAlchemy dialect) and implement `introspect`,
   `approx_distinct` and `power_query`.
2. Register it in `sources/__init__.py` and add its extra to `pyproject.toml`.
3. Add a row to `docs/sources.md` and, where it can run offline, a test.

## Pull requests

Keep them focused, include a clear description, and add or update tests for behaviour changes.
Match the surrounding style; `ruff` enforces most of it.

## Code of conduct

Be respectful and constructive. We follow the spirit of the
[Contributor Covenant](https://www.contributor-covenant.org/).
