# Validation for the initial Python port

The adaptation baseline is upstream R Ganttify 0.2.12 at
[`5853bf7`](https://github.com/AhmedAredah/Ganttify/tree/5853bf763e1ad3fc25d82e4a9e9435d3ee798bd1).
All tracked upstream files were reviewed, including the renderer, browser code,
documentation, sample data, metadata, license, and workflows.

## Completed checks

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

## Platform limits

The local checks above ran on Linux. Windows and macOS are separate GitHub Actions
jobs; their live results, rather than this initial local record, establish platform
verification. The configured workflow also repeats the Python-version matrix,
minimum-Plotly tests, browser tests, and installed-distribution checks.

The port preserves the source feature groups and corrects the behaviors documented
in [porting notes](porting.md). It does not claim pixel-identical output from the
R htmlwidget or replace project scheduling/critical-path software.
