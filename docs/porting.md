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
| `NULL` / `NA` | `None`; nested configuration defaults and nullable fields follow the rules below |
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

## Input surface and compatibility policy

All 11 original arguments are represented: `wbs_structure`, `activities`,
`chart_title`, `x_range`, `milestone_lines`, and the six configuration groups below.
Python additionally exposes `date_format`, `as_of`, and a renderer collaborator.
The configuration groups contain 35 leaf settings:

| Group | Leaf settings | Count |
|---|---|---|
| `color_config` | `mode`; `wbs`; `uniform.wbs`, `uniform.activity`; `attribute.column`, `attribute.mapping`, `attribute.wbs` | 7 |
| `display_config` | `wbs.show`, `wbs.show_labels`, `wbs.show_names_on_bars`; `activity.show`, `activity.show_names_on_bars`; `milestone.hide_label_levels` | 6 |
| `label_config` | `wbs.yaxis`, `wbs.bar`, `activity.yaxis`, `activity.bar` | 4 |
| `bar_config` | `wbs.opacity`, `wbs.height`; `activity.opacity`, `activity.height`, `activity.dim_opacity`, `activity.dim_past_activities` | 6 |
| `layout_config` | `buffer_days`, `indent_size`, `max_visible_rows`, `y_scroll_position`, `yaxis_label_width`, `yaxis_label_max_chars`, `hover_popup_max_chars`, `show_yaxis_labels`, `xaxis_position` | 9 |
| `tooltip_config` | `wbs`, `activity`, `milestone` | 3 |

The matching input surface does not imply that every R value or output is identical.
The Python contract is:

- The default string-date policy accepts US `MM/DD/YYYY` and ISO `YYYY-MM-DD`.
  A nondefault `date_format` controls every date string, including `as_of` and
  `x_range`; native Python dates bypass string parsing. An ISO-shaped string cannot
  silently override the explicitly supplied custom format.
- A nested configuration value of `None` selects its declared default. Genuinely
  nullable fields retain `None`, including `y_scroll_position`,
  `yaxis_label_max_chars`, and `attribute.column`. Attribute color mode still requires
  a column. Missing and blank optional table cells use their documented defaults.
- DataFrame column names must be unique. IDs must be nonempty strings, WBS and
  activity IDs must each be unique, and references and intervals must be valid.
- Activity date fields used for colors and custom tooltip selectors are parsed dates,
  including inferred actual ends. WBS tooltip selectors expose computed `Level`,
  `Start_Date`, and `End_Date`; computed values override conflicting input fields.
- Color mappings first match native values, then canonical string keys. Numeric `1`
  and integral `1.0` can match JSON key `"1"`; dates can match `"YYYY-MM-DD"`;
  booleans can match `"TRUE"` or `"FALSE"`. A native match wins when both native and
  string keys are present. Boolean and numeric categories remain distinct.
- A two-date milestone remains an interval when its endpoints are equal. Its narrow
  visual may be a line, while the tooltip retains Start, End, and Duration of one day.
- Automatic bounds come from the visible project rows' planned/actual dates plus the
  configured buffer. Out-of-range milestones are omitted. With no dated project rows,
  milestones may define the fallback bounds; explicit `x_range` always wins.
- Integer-valued layout settings require built-in Python integers. Use a two-element
  list or tuple for `x_range`, with its end strictly after its start. Invalid milestone
  styles and positions raise errors rather than using the R warning-and-fallback path.

An empty color mapping selects automatic palette generation. This is a Python
defaulting rule rather than a promise to preserve R's explicit empty-list behavior.

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

Ordinary Plotly styling, including margin changes, remains available through
`.figure`. Passing that bare figure to Dash or exporting it directly does not
install Ganttify's custom runtime. Embed the wrapper's exported HTML when those
additional interactions are required; no Dash-specific runtime adapter is included.

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

Version 0.1.1 also corrects gaps identified after the initial port: duplicate
DataFrame columns are rejected; explicit custom format precedence is unambiguous;
normalized and inferred dates reach colors and custom tooltips; nested `None`
defaults and R/JSON-style mapping keys are supported; and equal-endpoint milestone
intervals retain their tooltip semantics. The browser display handoff survives
short-lived callers, label fitting follows current margins, and `staticPlot`
disables custom scrolling.

The source's row-spaced milestone hover markers could leave gaps on short charts.
The Python runtime adapts hover samples to the rendered viewport instead. Wide
calendar extents retain timeline coverage through coarser year bands rather than
silently stopping after a fixed number of years.

The relevant source sections are the [public function and date preparation](https://github.com/AhmedAredah/Ganttify/blob/5853bf763e1ad3fc25d82e4a9e9435d3ee798bd1/R/Ganttify.R#L309),
[hierarchy and filtering](https://github.com/AhmedAredah/Ganttify/blob/5853bf763e1ad3fc25d82e4a9e9435d3ee798bd1/R/Ganttify.R#L949),
[bar drawing](https://github.com/AhmedAredah/Ganttify/blob/5853bf763e1ad3fc25d82e4a9e9435d3ee798bd1/R/Ganttify.R#L1254),
and [browser runtime](https://github.com/AhmedAredah/Ganttify/blob/5853bf763e1ad3fc25d82e4a9e9435d3ee798bd1/R/Ganttify.R#L1994).

## Calendar and scope

Durations count calendar days inclusively. The difference between actual and planned
duration is duration variance, not a completion-date delay. This package visualizes
supplied schedules; it does not calculate project dependencies, a critical path,
working calendars, resource constraints, or Primavera-compatible schedule files.
Input datetime values become calendar dates; sub-day scheduling is outside the
domain model. Browser zoom may show a smaller time interval for navigation, but it
does not add time-of-day precision to the supplied activities.

The public function and configuration names are mapped from the R package; neither
that mapping nor the current test suite certifies exhaustive R input equivalence.
Native Python validation and the compatibility policies above are deliberate parts
of the API. Actual Jupyter/Colab frontend behavior and cross-language golden-output
comparisons require their own checks rather than being inferred from HTML export.

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
