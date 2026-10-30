# Changelog

## 0.1.1

- Make explicit custom date formats authoritative and reject duplicate DataFrame
  column names before converting input tables.
- Share normalized dates, inferred actual ends, and computed WBS fields across
  rendering, attribute coloring, and custom tooltip selectors.
- Accept nested `None` defaults and support native plus R/JSON-style string keys
  in attribute color mappings.
- Preserve two-date milestone interval semantics when both endpoints are equal.
- Keep automatic project bounds independent of distant milestone markers.
- Fix browser-display document lifetime, live margin-based label fitting, and
  custom interaction handling for `staticPlot` exports.
- Adapt milestone hover coverage to the viewport and rendered size; retain timeline
  coverage for wide year ranges with coarser calendar bands.
- Add regressions for the audited input, display, and embedding cases, and clarify
  remaining compatibility and frontend-verification limits in the documentation.

## 0.1.0

Initial Python adaptation of Ganttify R 0.2.12, source commit
`5853bf763e1ad3fc25d82e4a9e9435d3ee798bd1`.

- Interactive WBS hierarchy, planned and actual bars, color strategies, milestones,
  custom labels and tooltips, date-axis placement, and HTML export.
- Typed domain models, validated configuration, separate rendering and browser runtime,
  and an optional dataframe adapter.
- Standard `src` package, wheel and source-distribution builds, development tools,
  and a Python 3.11–3.15 CI matrix with Windows and macOS jobs.
- Graph/date validation and consistent `as_of` handling; corrected opacity, bar-height,
  and viewport behavior. See [porting notes](docs/porting.md).

The Python package has an independent version sequence from the R package.
