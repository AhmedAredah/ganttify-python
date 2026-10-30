# Changelog

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
