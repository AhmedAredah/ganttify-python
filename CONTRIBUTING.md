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
```

This test needs a real Chromium installation; the Node runtime unit tests do not.
Add behavior-focused tests when changing dates, hierarchy,
configuration, rendering, or exported interaction. Keep the stdlib domain independent
of Plotly and pandas, and update the API and porting notes for public behavior changes.

Public Python functions use snake_case, type annotations, and concise docstrings.
Configuration uses validated dataclasses or dictionaries. Prefer small collaborators
with clear responsibilities over inheritance hierarchies.

Include the reason for the change and the checks you actually ran in pull requests.
Do not claim platform or version verification from a CI configuration alone. Releases
must pass package checks and an installed-wheel smoke test outside the source checkout.
There is no automatic PyPI publishing workflow.

Contributions are distributed under GPL-3.0-only. Preserve the original Ganttify
attribution in [NOTICE](NOTICE).
