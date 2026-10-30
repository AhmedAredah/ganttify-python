# Contributing

Use a supported CPython version and a virtual environment:

```sh
python -m venv .venv
# Activate .venv with the command appropriate to your operating system.
python -m pip install -e ".[dev,dataframe]"
```

Before proposing a change, run:

```sh
python -m ruff check .
python -m ruff format --check .
python -m mypy src
python -m pytest --cov=ganttify --cov-report=term-missing
node --test tests/test_runtime.mjs
python -m build
python -m twine check dist/*
```

Node.js 22 is used for the browser-runtime tests; Node is not a runtime dependency
for Python users. The separate Chromium integration test can be run with:

```sh
npm install --no-save --package-lock=false playwright@1.62.1
npx playwright install --with-deps chromium
node tests/browser_smoke.cjs
node tests/browser_regressions.cjs
```

This test needs a real Chromium installation; the Node runtime unit tests do not.
Add behavior-focused tests when changing dates, hierarchy,
configuration, rendering, or exported interaction. Include combinations that cross
module boundaries: parsed/inferred dates used by selectors and colors, explicit
custom formats, nested defaults, equal-date intervals, and changed Plotly margins.
Browser regressions should exercise actual hover hit-testing, static exports, and
viewport/size changes, rather than checking only serialized trace metadata.
Keep the stdlib domain independent
of Plotly and pandas, and update the API and porting notes for public behavior changes.

Public Python functions use snake_case, type annotations, and concise docstrings.
Configuration uses validated dataclasses or dictionaries. Prefer small collaborators
with clear responsibilities over inheritance hierarchies.

Include the reason for the change and the checks you actually ran in pull requests.
Do not claim platform or version verification from a CI configuration alone. Releases
must pass package checks and an installed-wheel smoke test outside the source checkout.
There is no automatic PyPI publishing workflow.

Distinguish standalone Chromium checks, notebook Python-boundary checks, actual
notebook frontend checks, and R-versus-Python golden comparisons in reports. A pass
in one category does not establish another. When an intentional compatibility rule
changes, update [porting notes](docs/porting.md) alongside the regression tests.

Contributions are distributed under GPL-3.0-only. Preserve the original Ganttify
attribution in [NOTICE](NOTICE).
