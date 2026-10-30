# Validation record

The adaptation baseline is upstream R Ganttify 0.2.12 at
[`5853bf7`](https://github.com/AhmedAredah/Ganttify/tree/5853bf763e1ad3fc25d82e4a9e9435d3ee798bd1).
All tracked upstream files were reviewed, including the renderer, browser code,
documentation, sample data, metadata, license, and workflows.

## Version 0.1.1 regression scope

The follow-up investigation found input and display cases that were not established
by the original passing suite. Version 0.1.1 adds focused regressions for:

- Explicit custom date formats with ISO-shaped strings, and duplicate DataFrame
  column names in every supported table.
- Consistent normalized/inferred activity fields and computed WBS fields in colors,
  custom tooltips, and labels.
- Nested `None` defaults, native and canonical string color keys, and date labels
  with four-digit years.
- Equal-endpoint milestone intervals and project bounds unaffected by distant markers.
- Browser delivery from short-lived scripts, failed browser launches, and load timeouts.
- Label fitting after ordinary margin customization, static exports, pixel-aware
  milestone hover coverage, tight zoom inside long milestone intervals, and calendar
  bands spanning wide year ranges.

| Check | Result |
|---|---|
| Built-wheel tests, CPython 3.11 through 3.15 on Linux | 162 passed per version |
| Built-wheel tests, CPython 3.11 / minimum Plotly 6.0.0 | 162 passed |
| Browser runtime unit tests in Node.js | 17 passed |
| Chromium 153, CPython 3.12 / Plotly 7.1.0 | Baseline integration and 19 regression cases passed |
| Chromium 153, CPython 3.11 / Plotly 6.0.0 | Baseline integration and 19 regression cases passed |
| Ruff lint and formatting, mypy | Passed |
| Source distribution and wheel build, Twine checks | Passed |

Browser checks use the installed wheel, exercise all four axis positions with each
label mode, and verify label/margin overrides, static mode, normalized tooltips and
colors, equal-endpoint intervals, and milestone hover after scrolling, zooming, and
resizing. They produced no browser errors or external HTTP(S) requests. The Python
suite also checks browser delivery from a short-lived subprocess and rejects
unexpected hostname lookups during loopback server startup. Synthetic clients
connect directly, independently of system proxy discovery.

The current commit's [GitHub Actions results](https://github.com/AhmedAredah/ganttify-python/actions)
record the hosted checks, including Windows and macOS. Commands are in
[CONTRIBUTING.md](../CONTRIBUTING.md). The results below belong to version 0.1.0.

## Version 0.1.0 completed checks

| Check | Result |
|---|---|
| Built-wheel tests, CPython 3.11.17 on Linux | 118 passed |
| Built-wheel tests, CPython 3.12.14 on Linux | 118 passed |
| Built-wheel tests, CPython 3.13.16 on Linux | 118 passed |
| Built-wheel tests, CPython 3.14.8 on Linux | 118 passed |
| Built-wheel tests, CPython 3.15.0 on Linux | 118 passed |
| Browser runtime unit tests in Node.js | 11 passed |
| Chromium 153, CPython 3.12.14 / Plotly 7.1.0 | Integration passed |
| Chromium 153, CPython 3.11.17 / Plotly 6.0.0 | Integration passed |
| Ruff lint and formatting | Passed |
| mypy, package source | Passed |
| Source distribution and wheel build | Passed |
| Twine metadata checks for both distributions | Passed |
| Installed-wheel HTML export outside the checkout | Passed |
| Basic and advanced examples | Passed |
| Original sample data fidelity | All 8 WBS / 15 activity records matched |

The Python tests cover hierarchy ordering and rollups, a 2,500-level tree, invalid
references and cycles, dates and ongoing actuals, input immutability, DataFrames,
configuration validation, all color modes, labels, tooltips, milestones, display
flags, renderer substitution, HTML export, and R-compatible click metadata.

The browser checks exercise rendered striped bars, activity hovers within milestone
areas, accessible full label text after repeated redraws, minimum widths at wide
and narrow zoom ranges, original-date preservation, date axes through zoom and pan,
milestone/background preservation, mirrored axes, wheel scrolling, viewport bounds,
and event-loop guards. Self-contained export made zero HTTP(S) requests and produced
no browser console errors during these checks.

Browser integration identified and resolved two regressions: milestone-area hover
polygons intercepting activity tooltips, and Plotly data updates re-inferring a
date axis as numeric. Regression checks are included in the repository.

The initial [GitHub Actions run, attempt 2](https://github.com/AhmedAredah/ganttify-python/actions/runs/41007016992/attempts/2)
also passed all 11 jobs, including the Linux version matrix and Python 3.13 on
Windows and macOS. That result applies to the initial commit, not automatically
to later changes.

## Verification limits

The local checks above ran on Linux. Windows and macOS remain separate GitHub
Actions jobs. The configured workflow repeats the Python-version matrix,
minimum-Plotly tests, browser tests, and installed-distribution checks for updates.

Actual Jupyter/Colab frontend execution and automated R-versus-Python golden-output
comparisons have not been established by these checks. A notebook HTML representation
or a stubbed display call verifies the Python boundary, not the notebook frontend.
The 11 original arguments and 35 configuration settings are mapped in
[porting notes](porting.md#input-surface-and-compatibility-policy); input-surface
coverage alone does not prove every combination or R value is equivalent.

The port preserves the source feature groups and corrects the behaviors documented
in [porting notes](porting.md). It does not claim pixel-identical output from the
R htmlwidget or replace project scheduling/critical-path software.
