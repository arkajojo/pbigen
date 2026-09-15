# Publishing

How pbigen is built, tested and released to PyPI. This is the maintainer runbook.

## Layout

```
pbigen/
├── pyproject.toml           # hatchling build, metadata, optional-dependency extras
├── src/pbigen/           # src layout — import only works after install
│   ├── core/                # schema, design brain, layout, generator (no drivers)
│   ├── sources/             # source adapters + registry
│   ├── models/              # deterministic + LiteLLM models + registry
│   ├── emit/                # PBIR report + TMDL semantic model writers
│   └── themes/              # built-in theme JSON + loader
├── tests/                   # offline end-to-end tests (Parquet + SQLite)
├── docs/
└── examples/
```

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,lakehouse,sqlalchemy]"
ruff check src tests          # lint
pytest                        # test suite (runs fully offline)
```

## Cutting a release

1. Bump the version in **both** `pyproject.toml` and `src/pbigen/__init__.py` (`__version__`).
2. Update `CHANGELOG.md`.
3. Commit and tag: `git tag v0.1.0 && git push --tags`.
4. Build the artifacts:

   ```bash
   python -m build            # produces dist/*.whl and dist/*.tar.gz
   twine check dist/*
   ```

5. Publish (TestPyPI first is recommended):

   ```bash
   twine upload --repository testpypi dist/*        # verify install from TestPyPI
   twine upload dist/*                               # real PyPI
   ```

Use a [PyPI API token](https://pypi.org/help/#apitoken) (`__token__` as the username) or, better,
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/) from GitHub Actions so no token is
stored.

## Automated release (recommended)

Configure PyPI Trusted Publishing for this repository, then a tag push builds and publishes via the
GitHub Actions workflow. Until then, the CI workflow only lints, tests and builds on every push and
pull request.

## Versioning

Semantic versioning. Pre-1.0, minor versions may include breaking changes; they will be called out
in the changelog.
