# API reference

## Chart creation

```python
ganttify(
    wbs_structure,
    activities,
    chart_title="Project Gantt Chart with WBS",
    x_range=None,
    milestone_lines=None,
    color_config=None,
    display_config=None,
    label_config=None,
    bar_config=None,
    layout_config=None,
    tooltip_config=None,
    *,
    date_format="%m/%d/%Y",
    as_of=None,
    renderer=None,
)
```

Returns `GanttChart`. `Ganttify` is a compatibility alias for `ganttify`; prefer
snake_case in new Python code. `renderer` is an optional collaborator implementing
the renderer protocol, for applications that need a different presentation layer.

| Argument | Meaning |
|---|---|
| `wbs_structure` | Records with `ID`, `Name`, `Parent` |
| `activities` | Records with `WBS_ID`, `Activity_ID`, `Activity_Name`, `Start_Date`, `End_Date` |
| `milestone_lines` | Optional records with `date` and `label` plus styling/custom fields |
| `chart_title` | Plain text chart title |
| `x_range` | Two dates defining the exact initial x viewport; includes activities whose planned or actual interval overlaps |
| `date_format` | Explicit `datetime.strptime` format for non-ISO date strings; default US dates |
| `as_of` | Reference date for unfinished actual work and past-activity dimming; defaults to today's date |

A record collection can be a sequence of mappings, a mapping of equally sized
column sequences, or a pandas DataFrame. Empty collections are accepted. DataFrame
support is duck-typed: the domain package does not import pandas. Custom columns
are copied and retained for colors and tooltips.

WBS parents may be `None`, an empty string, or `"None"` for roots. Each non-root
parent must reference an existing WBS. WBS IDs and activity IDs must each be unique;
activities must reference existing WBS IDs. Row order is depth first, with a WBS's
direct activities before its child WBS nodes, retaining input order among siblings.

Required planned dates cannot be missing. Optional `Start_Date_Actual` and
`End_Date_Actual` support actual schedules. An actual start without an end displays
to `max(as_of, actual_start)`. An actual end without a start is invalid. Intervals
must not be reversed. Durations include both calendar endpoints; no working-day,
holiday, dependency, resource-leveling, or critical-path calculation is performed.

WBS spans cover every descendant activity's planned and actual intervals. An empty
WBS may have a label without a bar. Input date strings accept ISO `YYYY-MM-DD` or
`date_format`; native date/datetime values are also accepted. Date-time values are
normalized to dates because the schedule model uses calendar days.

## Configuration

Each group accepts its named dataclass or a dictionary with the keys below. Nested
partial dictionaries use defaults. Unknown keys, wrong types, invalid enum values,
and out-of-range numbers raise errors.

| Group | Keys and defaults |
|---|---|
| `ColorConfig` | `mode="wbs"`, `wbs={}`, `uniform=UniformColors()`, `attribute=AttributeColors()` |
| `UniformColors` | `wbs="#34495E"`, `activity="#2ECC71"` |
| `AttributeColors` | `column=None`, `mapping={}`, `wbs="#34495E"`; `column` required in attribute mode |
| `DisplayConfig` | `wbs=WBSDisplay()`, `activity=ActivityDisplay()`, `milestone=MilestoneDisplay()` |
| `WBSDisplay` | `show=True`, `show_labels=True`, `show_names_on_bars=True` |
| `ActivityDisplay` | `show=True`, `show_names_on_bars=False` |
| `MilestoneDisplay` | `hide_label_levels=()`; allowed levels 1 and 2 |
| `LabelConfig` | `wbs=LabelTemplate()`, `activity=LabelTemplate()` |
| `LabelTemplate` | `yaxis="{name}"`, `bar="{name}"` |
| `BarConfig` | `wbs=WBSBar()`, `activity=ActivityBar()` |
| `WBSBar` | `opacity=0.3`, `height=0.3` |
| `ActivityBar` | `opacity=1.0`, `height=0.8`, `dim_opacity=0.3`, `dim_past_activities=False` |
| `LayoutConfig` | `buffer_days=30`, `indent_size=2`, `max_visible_rows=20`, `y_scroll_position=None`, `yaxis_label_width=300`, `yaxis_label_max_chars=None`, `hover_popup_max_chars=50`, `show_yaxis_labels=True`, `xaxis_position="bottom"` |
| `TooltipConfig` | `wbs=()`, `activity=()`, `milestone=()` |

WBS colors use the default ten-color palette when unspecified. Activities use their
associated WBS color. Uniform mode uses one color for each row type. Attribute mode
uses a custom activity column; unspecified mappings receive generated palette colors,
and unmapped values fall back to gray.

Hiding WBS or activity rows removes their y-axis slots. `show_yaxis_labels` controls
activity labels; `WBSDisplay.show_labels` independently controls WBS labels. Heights
are fractions of one row. Opacities are in `[0, 1]`. `max_visible_rows` controls the
vertical viewport; scroll or pan to see additional rows. `y_scroll_position`, when
provided, is a numeric lower row position. `xaxis_position` accepts `"bottom"`,
`"top"`, or `"both"`.

Activity template fields are `{name}`, `{id}`, `{start}`, `{end}`, `{start_actual}`,
`{end_actual}`, `{duration}`, and `{wbs_id}`. WBS fields are `{name}`, `{id}`, `{start}`,
`{end}`, and `{duration}`. Date substitutions use `MM/DD/YYYY`. User text is treated
as text, not executable HTML. Tooltip custom fields may be a list of column names
or a mapping from column names to display labels:

```python
tooltip_config = {
    "wbs": {"Owner": "Project owner"},
    "activity": ["Status", "Priority"],
    "milestone": {"Description": "Notes"},
}
```

Missing, null, and blank custom values are omitted. Long tooltip text wraps without
losing words. When actuals exist, the default tooltip includes planned and actual
inclusive durations and their difference. Duration variance is not finish-date
variance.

## Milestones

| Field | Default and meaning |
|---|---|
| `date` | Required single date or two-date sequence |
| `label` | Required label text |
| `color` | Cycling milestone palette |
| `dash` | `"dash"`; line style |
| `width` | `2`; line width in pixels |
| `fill_opacity` | `0.15`; date-range area transparency |
| `label_position` | `"top"`; also `"middle"` or `"bottom"` |
| `label_level` | `1`; either 1 or 2 for label stacking |

The visual range may collapse into a line when it is narrower than the minimum
visible width. Tooltips retain the actual supplied interval. Hiding a label level
removes its annotation while preserving its visual milestone and hover content.

## GanttChart

| Member | Purpose |
|---|---|
| `.figure` | Underlying `plotly.graph_objects.Figure` |
| `.to_html(...)` | HTML string with Ganttify runtime installed |
| `.write_html(path, ...)` | Write interactive HTML to a filesystem path |
| `.show(renderer=None, **kwargs)` | Detect notebook display or open a browser; choose `"browser"` or `"notebook"` explicitly |
| `._repr_html_()` | Rich HTML display used by notebooks |

Use wrapper export/display methods for adaptive time bands, minimum bar widths,
vertical scroll, and hierarchy-label fitting. A bare Plotly figure remains useful
for static customization, but `figure.to_html()` and `figure.show()` do not know
about Ganttify's additional JavaScript. Self-contained HTML embeds Plotly by default;
choosing CDN delivery requires internet access. HTML export options follow
[Plotly's serializer](https://plotly.com/python-api-reference/generated/plotly.io.to_html.html),
with the wrapper installing its runtime before any user-supplied `post_script`.

Bar click events expose the original R-compatible fields in `point.customdata`:
`type`, `original_start`, `original_end`, and `activity_id` for activities. The types
are `wbs`, `activity`, `activity_planned`, and `activity_actual`. Per-trace
`meta.ganttify` also records the row ID, kind, original interval, and role. Visual
minimum-width changes do not alter these original dates.

## Example data

`from ganttify.datasets import get_test_project` returns a fresh dictionary with
`wbs_structure`, `activities`, and `colors`. It reproduces the upstream 8-WBS,
15-activity example and can be freely modified without affecting later calls.
