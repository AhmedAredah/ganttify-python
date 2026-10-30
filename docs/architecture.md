# Architecture

Ganttify separates schedule interpretation from presentation. The public function
coordinates validated data, configuration, schedule rows, and a renderer. The
browser runtime adds behavior to an already valid Plotly figure.

## Package layout

| Path | Contents |
|---|---|
| `pyproject.toml` | Build metadata, dependencies, and development-tool configuration |
| `src/ganttify/__init__.py` | Public API |
| `src/ganttify/chart.py` | Factory, renderer contract, export wrapper |
| `src/ganttify/_browser.py` | One-use loopback delivery for browser display |
| `src/ganttify/config.py` | Typed and validated configuration |
| `src/ganttify/models.py` | Immutable domain records |
| `src/ganttify/data.py` | Input adaptation, parsing, validation |
| `src/ganttify/scheduling.py` | Hierarchy traversal and date aggregation |
| `src/ganttify/colors.py` | Color-selection policies |
| `src/ganttify/formatting.py` | Labels and escaped tooltip text |
| `src/ganttify/rendering.py` | Plotly figure construction |
| `src/ganttify/datasets.py` | Original sample records |
| `src/ganttify/py.typed` | Typing marker |
| `src/ganttify/assets/runtime.js` | Export-time browser interactions |
| `tests/`, `examples/`, `docs/` | Verification, usage, and documentation |

The `src` layout avoids accidental imports of uninstalled checkout code and allows
CI to validate the installed wheel. Build metadata includes the typing marker,
browser runtime, license, and attribution notice.

## Responsibilities and extension points

| Component | Responsibility | Depends on |
|---|---|---|
| Models | WBS, activity, milestone, project, and display-row values | Standard library |
| Input adapter | Normalize records/dataframes; validate types, references, dates, and graphs | Models and standard library |
| Schedule builder | Stable hierarchy order, WBS spans, visible rows | Domain/configuration |
| Configuration | Defaults and validation for each option family | Standard library |
| Color/format helpers | Select colors and build escaped text | Domain/configuration |
| Plotly renderer | Translate prepared domain rows into figure data/layout | Plotly and helpers |
| Chart wrapper | Compose pipeline and display/export with runtime | Renderer contract and Plotly HTML export |
| Browser runtime | Respond to pan/zoom/scroll and fit labels | Figure metadata and browser Plotly |

The SOLID principles guide these boundaries:

- Each module has one coherent reason to change. Date validation is independent
  of trace rendering, and export is independent of hierarchy traversal.
- An application can supply a renderer implementing the small renderer protocol
  without changing date, hierarchy, or input-adaptation code.
- A custom renderer must honor the same prepared-project and row contract; callers
  can substitute it without changing the schedule pipeline.
- The renderer interface contains only rendering behavior. Domain records do not
  acquire display or file-writing methods.
- The coordinator depends on the renderer contract. The standard Plotly renderer
  is the default implementation, while the domain stays free of Plotly and pandas.

No abstract class hierarchy is required for ordinary records or helpers. Frozen
dataclasses represent validated values; configuration mappings are defensive copies.
The optional pandas integration checks unique column names, then converts a dataframe
through its public record interface. It does not make pandas a dependency of the
core model. Configuration defaults are resolved at the boundary, including nested
`None` values for non-nullable options; genuinely nullable options retain `None`.

## Data and browser contracts

Date parsing produces calendar-day `date` values. One `as_of` value drives both
unfinished actual intervals and dimming. WBS span aggregation includes actual dates
and works regardless of input order. Graph validation runs before traversal.
Iterative traversal supports deep WBS trees without depending on Python's recursion
limit. Display flags determine row inclusion before numeric row positions are set.

The default string-date parser accepts US and ISO strings. A nondefault explicit
format is authoritative, including for date-shaped strings that could also be ISO.
Normalized activity fields carry the same parsed and inferred dates as their domain
attributes. WBS display rows overlay computed level/start/end fields before custom
tooltip selection. This keeps colors, custom tooltips, labels, and bars on the same
date values while retaining unrelated source fields and leaving caller data unchanged.
Milestones retain whether the caller supplied one date or a two-date interval,
including an interval with equal endpoints.

The Plotly renderer uses horizontal bars on a date axis. Per-trace metadata records
the original date interval, row type, ID, and planned/actual role. The browser may
widen a short visual bar to keep it usable; it does not rewrite original dates or
reported duration. Patterned actual bars provide visual distinction without many
decorative stripe traces.

Layout metadata carries row count, viewport size, complete labels, and row kinds.
The runtime uses this metadata for left-aligned labels, truncation tooltips, and
vertical scroll bounds. Label fitting reads the current Plotly margin so normal
figure styling cannot leave the stored gutter width stale. Milestone hover coverage
adapts to the current viewport and rendered pixel dimensions; area hover points are
clipped to the visible timeline while preserving the original interval in tooltips.
Timeline changes update date formats and alternating background bands while preserving
milestone shapes. Very wide year ranges use coarser bands across the full extent.
UTC arithmetic avoids browser time-zone shifts. Event guards prevent a runtime update
from feeding itself, and `staticPlot` exports do not install custom input handlers.

JavaScript is an ordinary packaged asset, loaded through package resources and
installed with Plotly's `post_script` hook. It is not embedded in a Python source
string. See the official [Plotly HTML export API](https://plotly.com/python-api-reference/generated/plotly.io.to_html.html).

Browser display uses one-use loopback HTTP delivery, waits for the HTML request,
then closes the server. It does not depend on an asynchronously opened temporary
file surviving Python process exit. Explicit HTML export remains the persistent-file
route. Bare Plotly consumers, including Dash, do not receive the custom browser
runtime automatically; applications can embed the wrapper's exported HTML.

## Compatibility and verification

The supported-version target is CPython 3.11–3.15, corresponding to maintained
branches in the [Python Developer's Guide](https://devguide.python.org/versions/).
The CI matrix tests all target versions on Linux and Python 3.13 on macOS/Windows.
A separate job tests the lowest declared Plotly version. The result of a specific
run establishes verification for that commit; the configured matrix alone does not.

Ruff checks style/imports, mypy checks the typed implementation, pytest checks
schedule and figure behavior, and Node tests check the runtime. Chromium checks
exercise standalone HTML, hovering, axis synchronization, zoom, labels, scrolling,
and regressions for input/display integration. Distribution checks
build source/wheel artifacts, validate metadata, install a wheel in a new environment,
and exercise HTML export outside the checkout. Browser rendering should also be
visually checked when interaction or layout changes. There is no automatic PyPI
publication or force-tagging release workflow.

Actual Jupyter/Colab frontend execution and automated cross-language golden fixtures
are separate verification work. Standalone-browser checks or emitted HTML strings
do not establish either guarantee. See [validation](validation.md) for recorded runs.

Packaging follows the [PyPA pyproject guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/).
