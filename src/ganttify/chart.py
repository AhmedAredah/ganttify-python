"""Public orchestration and HTML presentation; scheduling is renderer-independent."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from importlib.resources import files
from typing import Any, Protocol

import plotly.graph_objects as go
import plotly.io as pio

from ._browser import open_html_in_browser
from .config import (
    BarConfig,
    ChartConfig,
    ColorConfig,
    DisplayConfig,
    LabelConfig,
    LayoutConfig,
    TooltipConfig,
)
from .data import parse_date, prepare_project
from .models import Project, Row
from .scheduling import build_rows


class Renderer(Protocol):
    """Small extension interface for alternative figure renderers."""

    def render(
        self,
        project: Project,
        rows: Sequence[Row],
        config: ChartConfig,
        *,
        chart_title: str,
        x_range: tuple[date, date] | None,
        as_of: date,
    ) -> go.Figure: ...


def _html_options(options: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(options)
    runtime = files("ganttify").joinpath("assets/runtime.js").read_text(encoding="utf-8")
    extra = result.pop("post_script", None)
    result["post_script"] = [runtime]
    if extra is not None:
        result["post_script"].extend([extra] if isinstance(extra, str) else extra)
    plotly_config = result.get("config")
    if plotly_config is not None and not isinstance(plotly_config, Mapping):
        raise TypeError("config must be a mapping or None")
    result["config"] = {"responsive": True, "scrollZoom": False, **(plotly_config or {})}
    return result


class GanttChart:
    """A Plotly figure with Ganttify's browser behavior and offline HTML export.

    Use ``figure`` for the normal Plotly API or Dash integration. Use this
    wrapper's export/display methods to retain dynamic labels and scrolling.
    """

    def __init__(self, figure: go.Figure) -> None:
        self.figure = figure

    def to_html(self, **kwargs: Any) -> str:
        """Return interactive HTML, embedding Plotly by default for offline use.

        Accepts the keyword arguments of :func:`plotly.io.to_html`. User
        ``post_script`` callbacks run after the bundled Ganttify callback.
        """
        return str(pio.to_html(self.figure, **_html_options(kwargs)))

    def write_html(self, file: Any, **kwargs: Any) -> None:
        """Write HTML to a path or text stream; accepts Plotly HTML options."""
        pio.write_html(self.figure, file, **_html_options(kwargs))

    def show(self, renderer: str | None = None, **kwargs: Any) -> None:
        """Display in a browser or notebook, keeping all Ganttify interactions.

        ``renderer=None`` uses a notebook when IPython is active, otherwise a
        browser. Use ``figure.show()`` for other standard Plotly renderers.
        Browser previews wait up to 30 seconds for the page request, so scripts
        can exit without deleting an unread file. Save HTML for later reopening.
        """
        notebook = False
        try:
            from IPython import get_ipython

            notebook = get_ipython() is not None
        except ImportError:
            pass
        if renderer is None:
            renderer = "notebook" if notebook else "browser"
        if renderer in ("notebook", "notebook_connected", "jupyterlab", "colab"):
            try:
                from IPython.display import HTML, display
            except ImportError as exc:
                raise ImportError("Notebook display requires IPython") from exc
            kwargs.setdefault("full_html", False)
            display(HTML(self.to_html(**kwargs)))
        elif renderer == "browser":
            # A fresh preview needs Plotly and has no filesystem asset directory.
            bundle = kwargs.get("include_plotlyjs")
            if bundle is False or bundle == "directory":
                kwargs["include_plotlyjs"] = True
            elif isinstance(bundle, str) and bundle.endswith(".js"):
                if not bundle.startswith(("https://", "http://", "//")):
                    raise ValueError(
                        "Browser preview requires an HTTP(S) Plotly URL or an embedded bundle; "
                        "use write_html() for local JavaScript assets"
                    )
            open_html_in_browser(self.to_html(**kwargs))
        else:
            raise ValueError("Use renderer='browser' or 'notebook', or figure.show() for Plotly")

    def _repr_html_(self) -> str:
        return self.to_html(full_html=False)


def ganttify(
    wbs_structure: Any,
    activities: Any,
    chart_title: str = "Project Gantt Chart with WBS",
    x_range: Sequence[Any] | None = None,
    milestone_lines: Any = None,
    color_config: ColorConfig | Mapping[str, Any] | None = None,
    display_config: DisplayConfig | Mapping[str, Any] | None = None,
    label_config: LabelConfig | Mapping[str, Any] | None = None,
    bar_config: BarConfig | Mapping[str, Any] | None = None,
    layout_config: LayoutConfig | Mapping[str, Any] | None = None,
    tooltip_config: TooltipConfig | Mapping[str, Any] | None = None,
    *,
    date_format: str = "%m/%d/%Y",
    as_of: date | str | None = None,
    renderer: Renderer | None = None,
) -> GanttChart:
    """Create a hierarchical interactive Gantt chart from records or DataFrames.

    Column names and the six configuration sections follow the original R
    library. Nested dictionaries and typed configuration objects are accepted.
    The default format accepts US and ISO strings; an explicit nondefault
    ``date_format`` governs all date strings. Native dates bypass string parsing.
    ``as_of`` makes in-progress actual spans and dimming reproducible.
    """
    if not isinstance(chart_title, str):
        raise TypeError("chart_title must be a string")
    today = date.today() if as_of is None else parse_date(as_of, "as_of", date_format=date_format)
    assert today is not None
    bounds = None
    if x_range is not None:
        if isinstance(x_range, (str, bytes)) or not isinstance(x_range, Sequence):
            raise TypeError("x_range must be a two-date sequence")
        if len(x_range) != 2:
            raise ValueError("x_range must contain exactly two dates")
        start = parse_date(x_range[0], "x_range start", date_format=date_format)
        end = parse_date(x_range[1], "x_range end", date_format=date_format)
        assert start is not None and end is not None
        if end <= start:
            raise ValueError("x_range end must be after its start")
        bounds = (start, end)
    config = ChartConfig.from_configs(
        color_config=color_config,
        display_config=display_config,
        label_config=label_config,
        bar_config=bar_config,
        layout_config=layout_config,
        tooltip_config=tooltip_config,
    )
    project = prepare_project(
        wbs_structure, activities, milestone_lines, date_format=date_format, as_of=today
    )
    rows = build_rows(project, config.display, bounds)
    if renderer is None:
        from .rendering import PlotlyRenderer

        renderer = PlotlyRenderer()
    return GanttChart(
        renderer.render(project, rows, config, chart_title=chart_title, x_range=bounds, as_of=today)
    )


# Compatibility spelling for users moving examples from the R package.
Ganttify = ganttify
