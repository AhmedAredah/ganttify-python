# Porting from R Ganttify

This package adapts [Ganttify R 0.2.12](https://github.com/AhmedAredah/Ganttify/tree/5853bf763e1ad3fc25d82e4a9e9435d3ee798bd1),
commit `5853bf763e1ad3fc25d82e4a9e9435d3ee798bd1`. The entire tracked source,
documentation, example dataset, metadata, and workflows were reviewed before the
Python design. The original GPL license and Ahmed Aredah attribution are retained.
The Python implementation is a separate package with an independent version series.

## API mapping

| R | Python |
|---|---|
| `library(ganttify)` | `from ganttify import ganttify` |
| `Ganttify(...)` | `ganttify(...)`; `Ganttify` alias also available |
| `data.frame(...)` | Records, column mappings, or pandas DataFrames |
| `list(...)` for configuration | Nested dictionaries or configuration dataclasses |
| `NULL` / `NA` | `None`; dataframe null values are normalized |
| `TRUE` / `FALSE` | `True` / `False` |
| `Date` | `datetime.date` |
| `data(test_project)` | `from ganttify.datasets import get_test_project` |
| `test_project$activities` | `get_test_project()["activities"]` |
| `c(Column="Friendly label")` | `{"Column": "Friendly label"}` |
| `c("Status", "Owner")` | `["Status", "Owner"]` |
| `htmlwidgets::saveWidget(chart, path)` | `chart.write_html(path)` |
| Plotly widget | `GanttChart` wrapper with `.figure` |

The original column names are preserved to make existing datasets easy to reuse.
Public Python functions use snake_case. R list-column milestone dates become a
single Python date value or a list/tuple of two dates. The six configuration-group
names and nested keys retain their original meaning.

## Preserved feature groups

- WBS hierarchy, descendant date spans, input ordering, and activity indentation.
- WBS, uniform, and attribute color modes with custom mappings.
- Independent WBS/activity visibility, y labels, and names at bar ends.
- Label placeholders, custom tooltip fields, friendly labels, and text wrapping.
- Planned/actual bars, patterned actuals, ongoing work, and duration variance.
- Milestone lines/areas, line styling, opacity, label positions, and levels 1/2.
- Scrollable row viewport, short-bar visibility, original-date hover values, and IDs.
- Adaptive date labels and time bands; bottom, top, and mirrored axes.
- Offline HTML export and the original 8-WBS/15-activity sample.

The browser appearance is reconstructed with native Plotly bar traces rather than
requiring pixel-identical SVG output from the R widget. Actual patterns use native
bar patterns instead of eight extra scatter traces per activity. Browser-only
features are installed by the chart wrapper's export/display methods.

## Deliberate corrections

| Upstream behavior | Python behavior and reason |
|---|---|
| README advertises `date_format`, but the public R function has no corresponding argument | Explicit `date_format`, ISO strings, and native Python dates provide a usable and documented date API |
| Dimming compares planned end dates to hardcoded `2025-10-22` while ongoing actual work uses the current date | One injectable `as_of` drives both, making charts reproducible |
| Activity opacity is overwritten to `1.0` while drawing; configured bar heights are unused | Respect opacity and height settings |
| `x_range` filters planned overlaps and then derives different buffered limits | Use the exact requested bounds and preserve planned or actual overlaps |
| Cycles, duplicate IDs, missing parents, and orphan activities are not adequately checked | Validate graph and references before traversal; reject invalid schedules clearly |
| Reversed intervals may survive into plots and negative durations | Reject reversed planned, actual, and milestone intervals |
| Actual parsing requires both actual-date columns to exist | Accept actual start with missing end, then resolve its display end from `as_of` |
| Empty WBS rows can reach hover-point generation with missing dates | Keep their labels and omit an undefined bar |
| Minimum-width adjustment converts sub-day values back to date-only strings | Preserve UTC fractional timestamps for visual width while retaining original dates |
| Timeline JS mixes local dates with UTC serialization | Use UTC arithmetic to prevent timezone-dependent day shifts |
| Overlong single tooltip words are truncated | Wrap without discarding content |
| User strings are interpolated into tooltip HTML | Escape text and preserve literal data instead of executing markup |

The relevant source sections are the [public function and date preparation](https://github.com/AhmedAredah/Ganttify/blob/5853bf763e1ad3fc25d82e4a9e9435d3ee798bd1/R/Ganttify.R#L309),
[hierarchy and filtering](https://github.com/AhmedAredah/Ganttify/blob/5853bf763e1ad3fc25d82e4a9e9435d3ee798bd1/R/Ganttify.R#L949),
[bar drawing](https://github.com/AhmedAredah/Ganttify/blob/5853bf763e1ad3fc25d82e4a9e9435d3ee798bd1/R/Ganttify.R#L1254),
and [browser runtime](https://github.com/AhmedAredah/Ganttify/blob/5853bf763e1ad3fc25d82e4a9e9435d3ee798bd1/R/Ganttify.R#L1994).

## Calendar and scope

Durations count calendar days inclusively. The difference between actual and planned
duration is duration variance, not a completion-date delay. This package visualizes
supplied schedules; it does not calculate project dependencies, a critical path,
working calendars, resource constraints, or Primavera-compatible schedule files.

## Version and dependency policy

CPython 3.11–3.15 are CI targets, chosen from the maintained versions in the
[Python Developer's Guide](https://devguide.python.org/versions/). Python 3.10 and
older are outside this policy. Plotly is constrained to `>=6,<8`, with an explicit
minimum-version test. Pandas is optional (`>=2.2`). Passing CI results establish
verified combinations; configuration alone does not prove compatibility.

The implementation uses modern [PyPA metadata](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/),
a `src` layout, a packaged typing marker, and wheel/source builds. It does not reuse
R-specific CRAN checks, documentation generation, or the upstream automatic
force-tagging release workflow.
