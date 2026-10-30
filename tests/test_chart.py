"""Public API, presentation, and renderer extension boundary tests."""

from datetime import date
from io import StringIO

import plotly.graph_objects as go
import pytest

from ganttify import ChartConfig, GanttChart, Ganttify, ganttify

WBS = [{"ID": "W", "Name": "Project", "Parent": None}]
ACTIVITIES = [
    {
        "Activity_ID": "A",
        "Activity_Name": "Design",
        "WBS_ID": "W",
        "Start_Date": "01/01/2025",
        "End_Date": "01/10/2025",
        "Start_Date_Actual": "01/03/2025",
    }
]


class RecordingRenderer:
    def __init__(self):
        self.calls = []
        self.figure = go.Figure()

    def render(self, project, rows, config, *, chart_title, x_range, as_of):
        self.calls.append((project, rows, config, chart_title, x_range, as_of))
        return self.figure


def test_facade_injects_renderer_with_normalized_project_and_config():
    renderer = RecordingRenderer()
    chart = ganttify(
        WBS,
        ACTIVITIES,
        chart_title="Delivery",
        x_range=("2025-01-02", "2025-01-20"),
        as_of="2025-01-15",
        display_config={"wbs": {"show": False}},
        renderer=renderer,
    )
    assert isinstance(chart, GanttChart)
    assert chart.figure is renderer.figure
    project, rows, config, title, bounds, as_of = renderer.calls[0]
    assert isinstance(config, ChartConfig)
    assert project.activities[0].end_actual == date(2025, 1, 15)
    assert [row.id for row in rows] == ["A"]
    assert config.display.wbs.show is False
    assert title == "Delivery"
    assert bounds == (date(2025, 1, 2), date(2025, 1, 20))
    assert as_of == date(2025, 1, 15)


def test_compatibility_alias_and_native_date_arguments():
    assert Ganttify is ganttify
    renderer = RecordingRenderer()
    Ganttify(WBS, ACTIVITIES, as_of=date(2025, 1, 15), renderer=renderer)
    assert renderer.calls[0][-1] == date(2025, 1, 15)


@pytest.mark.parametrize(
    "x_range,error",
    [
        ("2025-01-01", TypeError),
        (123, TypeError),
        (["2025-01-01"], ValueError),
        (["2025-01-01", "2025-01-01", "2025-01-02"], ValueError),
        (["2025-01-02", "2025-01-01"], ValueError),
        (["2025-01-01", "2025-01-01"], ValueError),
        ([None, "2025-01-02"], ValueError),
        (["invalid", "2025-01-02"], ValueError),
    ],
)
def test_invalid_xrange_rejected_before_rendering(x_range, error):
    renderer = RecordingRenderer()
    with pytest.raises(error):
        ganttify(WBS, ACTIVITIES, x_range=x_range, renderer=renderer)
    assert renderer.calls == []


@pytest.mark.parametrize(
    "as_of,error", [("invalid", ValueError), ("", ValueError), (True, TypeError), (123, TypeError)]
)
def test_invalid_as_of_rejected(as_of, error):
    with pytest.raises(error):
        ganttify(WBS, ACTIVITIES, as_of=as_of)


def test_chart_title_type_rejected():
    with pytest.raises(TypeError, match="chart_title"):
        ganttify(WBS, ACTIVITIES, chart_title=123)


def test_html_exports_embed_runtime_and_default_offline_plotly():
    chart = ganttify(WBS, ACTIVITIES, as_of="2025-01-15")
    html = chart.to_html(div_id="schedule-under-test")
    assert "<html>" in html and "plotly.js v" in html
    assert "Ganttify Python browser enhancements" in html
    assert "getElementById('schedule-under-test')" in html
    assert "getElementById('{plot_id}')" not in html
    assert "cdn.plot.ly" not in html.split("Plotly.newPlot(", 1)[-1]


def test_html_options_preserve_custom_config_and_callbacks_without_mutation():
    chart = ganttify([], [], as_of="2025-01-15")
    config = {"responsive": False, "displayModeBar": False}
    scripts = ["window.customCallback = '{plot_id}';"]
    html = chart.to_html(
        include_plotlyjs=False,
        full_html=False,
        div_id="callback-plot",
        config=config,
        post_script=scripts,
    )
    assert "<html>" not in html
    assert "window.customCallback = 'callback-plot';" in html
    assert html.index("Ganttify Python browser enhancements") < html.index("window.customCallback")
    assert '"responsive": false' in html and '"displayModeBar": false' in html
    assert config == {"responsive": False, "displayModeBar": False}
    assert scripts == ["window.customCallback = '{plot_id}';"]


def test_plotly_config_none_is_accepted():
    chart = ganttify([], [], as_of="2025-01-15")
    assert "Plotly.newPlot" in chart.to_html(config=None, include_plotlyjs=False)
    stream = StringIO()
    chart.write_html(stream, config=None, include_plotlyjs=False)
    assert "Ganttify Python browser enhancements" in stream.getvalue()


def test_write_html_path_and_text_stream_and_notebook_repr(tmp_path):
    chart = ganttify(WBS, ACTIVITIES, as_of="2025-01-15")
    target = tmp_path / "chart.html"
    chart.write_html(target, include_plotlyjs=False, div_id="file-plot")
    assert "getElementById('file-plot')" in target.read_text(encoding="utf-8")
    stream = StringIO()
    chart.write_html(stream, include_plotlyjs=False, full_html=False)
    assert "Ganttify Python browser enhancements" in stream.getvalue()
    representation = chart._repr_html_()
    assert "<html>" not in representation
    assert "Ganttify Python browser enhancements" in representation


def test_hostile_text_stays_data_in_exported_html():
    hostile = "</script><script>window.PWNED = true;</script> %{x} <img src=x onerror=alert(1)>"
    activity = dict(ACTIVITIES[0], Activity_Name=hostile, Owner="<b>Unknown</b>")
    chart = ganttify(
        WBS,
        [activity],
        as_of="2025-01-15",
        chart_title=hostile,
        tooltip_config={"activity": {"Owner": "<u>Owner</u>"}},
        display_config={"activity": {"show_names_on_bars": True}},
    )
    html = chart.to_html(include_plotlyjs=False)
    assert "</script><script>window.PWNED" not in html
    assert "<img src=x onerror=alert(1)>" not in html
    trace = next(
        trace for trace in chart.figure.data if trace.type == "bar" and trace.name == "Planned"
    )
    assert trace.hovertemplate == "%{hovertext}<extra></extra>"
    assert "&lt;b&gt;Unknown&lt;/b&gt;" in trace.hovertext[0]


def test_show_rejects_unknown_renderer():
    chart = ganttify([], [], as_of="2025-01-15")
    with pytest.raises(ValueError, match="renderer"):
        chart.show(renderer="unsupported")


def test_show_browser_delivers_exported_interactive_html(monkeypatch):
    chart = ganttify([], [], as_of="2025-01-15")
    delivered = []
    import ganttify.chart as chart_module

    monkeypatch.setattr(chart_module, "open_html_in_browser", delivered.append)
    chart.show(renderer="browser", include_plotlyjs=False)
    assert len(delivered) == 1
    assert "plotly.js v" in delivered[0]
    assert "Ganttify Python browser enhancements" in delivered[0]


def test_browser_preview_embeds_directory_mode_bundle(monkeypatch):
    import ganttify.chart as chart_module

    delivered = []
    monkeypatch.setattr(chart_module, "open_html_in_browser", delivered.append)
    ganttify([], [], as_of="2025-01-15").show(renderer="browser", include_plotlyjs="directory")
    assert "plotly.js v" in delivered[0]
    assert 'src="plotly.min.js"' not in delivered[0]


@pytest.mark.parametrize(
    "bundle", ["plotly-custom.js", "/assets/plotly.js", "file:///tmp/plotly.js"]
)
def test_browser_preview_rejects_unservable_local_bundle(monkeypatch, bundle):
    import ganttify.chart as chart_module

    monkeypatch.setattr(
        chart_module, "open_html_in_browser", lambda html: pytest.fail("Unexpected browser")
    )
    with pytest.raises(ValueError, match="HTTP"):
        ganttify([], [], as_of="2025-01-15").show(renderer="browser", include_plotlyjs=bundle)


def test_browser_preview_preserves_external_bundle_url(monkeypatch):
    import ganttify.chart as chart_module

    delivered = []
    monkeypatch.setattr(chart_module, "open_html_in_browser", delivered.append)
    url = "https://example.org/custom-plotly.js"
    ganttify([], [], as_of="2025-01-15").show(renderer="browser", include_plotlyjs=url)
    assert f'src="{url}"' in delivered[0]


def test_notebook_show_installs_runtime_without_opening_browser(monkeypatch):
    import sys
    from types import ModuleType

    import ganttify.chart as chart_module

    captured = []
    ipython = ModuleType("IPython")
    ipython.get_ipython = lambda: object()
    display = ModuleType("IPython.display")
    display.HTML = lambda value: value
    display.display = captured.append
    monkeypatch.setitem(sys.modules, "IPython", ipython)
    monkeypatch.setitem(sys.modules, "IPython.display", display)
    monkeypatch.setattr(
        chart_module, "open_html_in_browser", lambda html: pytest.fail("Unexpected browser")
    )
    ganttify([], [], as_of="2025-01-15").show(include_plotlyjs=False)
    assert len(captured) == 1
    assert "<html>" not in captured[0]
    assert "Ganttify Python browser enhancements" in captured[0]
