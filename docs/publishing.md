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

`.github/workflows/release.yml` builds, publishes to PyPI, and creates a GitHub Release on every
`v*` tag push — using **Trusted Publishing (OIDC)**, so no API token is ever stored.

One-time setup on PyPI: **Manage → Publishing → Add a GitHub publisher** with

- Owner: `arkajojo`
- Repository: `pbigen`
- Workflow name: `release.yml`
- Environment name: `pypi`

(Optionally create a matching `pypi` environment under the repo's **Settings → Environments** to add
approval gates.) After that, releasing is just:

```bash
# bump version in pyproject.toml and src/pbigen/__init__.py, update CHANGELOG.md, commit
git tag v0.1.0 && git push --tags        # the workflow does build + publish + GitHub Release
```

With the workflow in place, do **not** also run `twine upload` or `gh release create` by hand for
that version — the workflow owns it. The separate CI workflow keeps linting, testing and building on
every push and pull request.

## Versioning

Semantic versioning. Pre-1.0, minor versions may include breaking changes; they will be called out
in the changelog.
