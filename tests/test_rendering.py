"""Visual specification tests for Plotly serialization and chart semantics."""

from datetime import date

import pytest

from ganttify.config import ChartConfig
from ganttify.data import prepare_project
from ganttify.formatting import custom_tooltip, format_label, wrap_text
from ganttify.rendering import PlotlyRenderer
from ganttify.scheduling import build_rows

AS_OF = date(2025, 2, 15)


@pytest.fixture
def records():
    return (
        [
            {"ID": "P", "Name": "Project", "Parent": "None", "Owner": "Team"},
            {"ID": "C", "Name": "Child", "Parent": "P"},
        ],
        [
            {
                "WBS_ID": "C",
                "Activity_ID": "A",
                "Activity_Name": "Design",
                "Start_Date": "01/01/2025",
                "End_Date": "01/10/2025",
                "Status": "done",
            }
        ],
    )


def render(records, *, milestones=None, x_range=None, **options):
    project = prepare_project(*records, milestone_lines=milestones, as_of=AS_OF)
    config = ChartConfig.from_configs(**options)
    rows = build_rows(project, config.display, x_range)
    figure = PlotlyRenderer().render(
        project, rows, config, chart_title="Schedule", x_range=x_range, as_of=AS_OF
    )
    return figure, rows


def bars(figure):
    return [trace for trace in figure.data if trace.type == "bar"]


def test_hierarchical_labels_and_initial_viewport(records):
    figure, rows = render(records, layout_config={"max_visible_rows": 2})
    assert [row.id for row in rows] == ["P", "C", "A"]
    assert list(figure.layout.yaxis.tickvals) == [3, 2, 1]
    assert list(figure.layout.yaxis.range) == [1.5, 3.5]
    assert figure.layout.meta["ganttify"]["full_labels"] == [
        "Project",
        "\u00a0\u00a0Child",
        "\u00a0\u00a0\u00a0\u00a0• Design",
    ]
    assert figure.layout.yaxis.ticktext[0] == "<b>Project</b>"
    assert len(bars(figure)) == 3


def test_actual_bars_use_patterns_and_identical_complete_hover(records):
    records[1][0].update(Start_Date_Actual="01/03/2025", End_Date_Actual="01/14/2025")
    figure, _ = render(records)
    planned, actual = bars(figure)[-2:]
    assert actual.marker.pattern.shape == "/"
    assert actual.y[0] < planned.y[0]
    assert actual.hovertext == planned.hovertext
    assert "<b>Variance:</b> +2 days" in actual.hovertext[0]
    assert actual.meta["ganttify"]["start"] == "2025-01-03"
    assert actual.meta["ganttify"]["role"] == "actual"


def test_actual_ongoing_dates_reach_as_of_and_expand_hidden_wbs_view(records):
    records[1][0].update(Start_Date_Actual="01/03/2025")
    figure, _ = render(records, display_config={"wbs": {"show": False}})
    assert len(bars(figure)) == 2
    assert bars(figure)[-1].meta["ganttify"]["end"] == "2025-02-15"
    assert figure.layout.xaxis.range[1] == "2025-03-17"


def test_bar_options_and_deterministic_dimming_are_honored(records):
    figure, _ = render(
        records,
        bar_config={
            "wbs": {"opacity": 0.6, "height": 0.45},
            "activity": {"opacity": 0.7, "height": 0.9},
        },
    )
    assert bars(figure)[0].opacity == 0.6
    assert bars(figure)[0].width == 0.45
    assert bars(figure)[-1].opacity == 0.7
    assert bars(figure)[-1].width == 0.9
    dimmed, _ = render(
        records, bar_config={"activity": {"dim_past_activities": True, "dim_opacity": 0.2}}
    )
    assert bars(dimmed)[-1].opacity == 0.2


@pytest.mark.parametrize(
    "color_config, expected_wbs, expected_activity",
    [
        ({"wbs": {"C": "red"}}, "red", "red"),
        ({"mode": "uniform", "uniform": {"wbs": "black", "activity": "blue"}}, "black", "blue"),
        (
            {"mode": "attribute", "attribute": {"column": "Status", "mapping": {"done": "green"}}},
            "#34495E",
            "green",
        ),
        ({"mode": "attribute", "attribute": {"column": "Status"}}, "#34495E", "#27AE60"),
    ],
)
def test_color_modes(records, color_config, expected_wbs, expected_activity):
    figure, _ = render(records, color_config=color_config)
    assert bars(figure)[1].marker.color == expected_wbs
    assert bars(figure)[-1].marker.color == expected_activity


def test_attribute_fallback_and_missing_column(records):
    figure, _ = render(
        records,
        color_config={
            "mode": "attribute",
            "attribute": {"column": "Status", "mapping": {"other": "blue"}},
        },
    )
    assert bars(figure)[-1].marker.color == "#95A5A6"
    with pytest.raises(ValueError, match="does not exist"):
        render(records, color_config={"mode": "attribute", "attribute": {"column": "missing"}})


def test_xrange_is_exact_and_keeps_actual_overlap(records):
    records[1][0].update(Start_Date_Actual="02/01/2025", End_Date_Actual="02/10/2025")
    figure, rows = render(records, x_range=(date(2025, 2, 5), date(2025, 2, 7)))
    assert [row.id for row in rows] == ["P", "C", "A"]
    assert figure.layout.xaxis.range == ("2025-02-05", "2025-02-07")


def test_milestone_shapes_tooltips_labels_and_level_hiding(records):
    milestones = [
        {"date": "01/02/2025", "label": "Kickoff", "Owner": "PM", "label_level": 1},
        {
            "date": ["01/04/2025", "01/09/2025"],
            "label": "Review",
            "label_level": 2,
            "fill_opacity": 0.25,
            "label_position": "middle",
        },
    ]
    figure, _ = render(
        records,
        milestones=milestones,
        display_config={"milestone": {"hide_label_levels": [1]}},
        tooltip_config={"milestone": {"Owner": "Project owner"}},
    )
    shapes = figure.layout.shapes
    assert [shape.type for shape in shapes] == ["line", "rect"]
    assert all(shape.name == "ganttify-milestone" for shape in shapes)
    assert all(shape.yref == "paper" and shape.y0 == 0 and shape.y1 == 1 for shape in shapes)
    assert shapes[1].opacity == 0.25
    assert "Kickoff" not in [annotation.text for annotation in figure.layout.annotations]
    review = next(
        annotation for annotation in figure.layout.annotations if annotation.text == "Review"
    )
    assert review.yref == "paper" and review.y == 0.5
    hover = [trace for trace in figure.data if trace.type == "scatter"]
    assert "Project owner" in hover[0].hovertext[0]
    assert hover[0].meta["ganttify"]["kind"] == "milestone-line"
    assert hover[0].meta["ganttify"]["date"].startswith("2025-01-02")
    assert min(hover[0].y) == figure.layout.yaxis.range[0]
    assert max(hover[0].y) == figure.layout.yaxis.range[1]
    assert hover[1].mode == "markers"
    assert hover[1].fill is None
    assert set(hover[1].y) == {2}
    assert "<b>Duration:</b> 6 days" in hover[1].hovertext[0]


def test_narrow_area_uses_line_and_preserves_interval_hover(records):
    figure, _ = render(
        records,
        milestones=[{"date": ["01/02/2025", "01/03/2025"], "label": "Brief"}],
        layout_config={"buffer_days": 365},
    )
    assert figure.layout.shapes[0].type == "line"
    assert "<b>Duration:</b> 2 days" in figure.data[-1].hovertext[0]


@pytest.mark.parametrize("position", ["bottom", "top", "both"])
def test_time_axis_positions(records, position):
    figure, _ = render(records, layout_config={"xaxis_position": position})
    assert figure.layout.xaxis.side == ("top" if position == "top" else "bottom")
    if position == "both":
        assert figure.layout.xaxis2.side == "top"
        assert figure.layout.xaxis2.matches == "x"


def test_independent_label_visibility_and_full_text(records):
    figure, _ = render(records, layout_config={"show_yaxis_labels": False})
    assert figure.layout.yaxis.ticktext[-1] == ""
    assert figure.layout.yaxis.ticktext[0] == "<b>Project</b>"
    hidden, _ = render(
        records,
        display_config={"wbs": {"show_labels": False}},
        layout_config={"show_yaxis_labels": False},
    )
    assert all(label == "" for label in hidden.layout.meta["ganttify"]["full_labels"])
    assert hidden.layout.margin.l == 50


def test_templates_and_truncation_keep_full_metadata(records):
    figure, rows = render(
        records,
        label_config={"activity": {"yaxis": "{id} {duration} {start} {unknown}"}},
        layout_config={"yaxis_label_max_chars": 10},
    )
    assert format_label("{id}: {start} / {unknown}", rows[-1]) == "A: 01/01/2025 / {unknown}"
    assert "…" in figure.layout.yaxis.ticktext[-1]
    assert "A 10 01/01/2025 {unknown}" in figure.layout.meta["ganttify"]["full_labels"][-1]


def test_user_content_is_escaped_and_not_interpolated_twice(records):
    records[1][0]["Activity_Name"] = "<script>alert(1)</script> %{x}"
    records[1][0]["Owner"] = "<b>Admin</b>"
    figure, _ = render(records, tooltip_config={"activity": {"Owner": "<script>Owner</script>"}})
    trace = bars(figure)[-1]
    assert trace.hovertemplate == "%{hovertext}<extra></extra>"
    assert "&lt;script&gt;" in trace.hovertext[0]
    assert "&lt;b&gt;Admin&lt;/b&gt;" in trace.hovertext[0]
    assert "%{x}" in trace.hovertext[0]
    assert "<script>" not in figure.to_json()


def test_wrapping_does_not_discard_long_words_and_hides_missing_fields():
    assert wrap_text("abcdefghijk", 4) == "abcd<br>efgh<br>ijk"
    assert custom_tooltip(
        {"a": None, "b": float("nan"), "c": " ", "d": "text"}, ["missing", "a", "b", "c", "d"], 50
    ) == ["<b>d:</b> text"]


def test_empty_wbs_row_is_labeled_without_invalid_bar():
    figure, rows = render(([{"ID": "P", "Name": "Empty", "Parent": None}], []))
    assert len(rows) == 1
    assert len(figure.data) == 0
    assert figure.layout.yaxis.ticktext == ("<b>Empty</b>",)
    assert figure.layout.xaxis.range == ("2025-02-15", "2026-02-15")


def test_same_day_activity_stays_visible_with_original_dates(records):
    records[1][0]["End_Date"] = "01/01/2025"
    figure, _ = render(records)
    activity = bars(figure)[-1]
    assert activity.x[0] > 0
    assert activity.meta["ganttify"]["start"] == activity.meta["ganttify"]["end"]
    assert "<b>Duration:</b> 1 days" in activity.hovertext[0]


@pytest.mark.parametrize("position, expected", [("top", 3.5), ("middle", 2.5), ("bottom", 1.5)])
def test_area_hover_uses_visible_label_edge_without_covering_bars(records, position, expected):
    figure, _ = render(
        records,
        milestones=[
            {"date": ["01/01/2025", "01/10/2025"], "label": "Review", "label_position": position}
        ],
        layout_config={"max_visible_rows": 2},
    )
    hover = figure.data[-1]
    assert hover.mode == "markers" and hover.fill is None
    assert set(hover.y) == {expected}
    assert hover.meta["ganttify"]["kind"] == "milestone-area"
    assert hover.meta["ganttify"]["label_position"] == position


def test_area_hover_sampling_is_bounded(records):
    figure, _ = render(
        records,
        milestones=[{"date": ["01/01/1900", "01/01/2100"], "label": "Long range"}],
        x_range=(date(1900, 1, 1), date(2100, 1, 1)),
    )
    hover = figure.data[-1]
    assert len(hover.x) == 400
    assert hover.x[0].startswith("1900-01-01")
    assert hover.x[-1].startswith("2100-01-01")


def test_area_hover_initial_samples_are_clipped_to_visible_schedule(records):
    figure, _ = render(
        records,
        milestones=[{"date": ["01/01/1900", "01/01/2100"], "label": "Long range"}],
    )
    hover = figure.data[-1]
    assert hover.x[0].startswith(figure.layout.xaxis.range[0])
    assert hover.x[-1].startswith(figure.layout.xaxis.range[1])
    assert hover.meta["ganttify"]["original_start"] == "1900-01-01"
    assert hover.meta["ganttify"]["original_end"] == "2100-01-01"
    assert "<b>Start:</b> 1900-01-01" in hover.hovertext[0]
    assert "<b>End:</b> 2100-01-01" in hover.hovertext[0]


def test_two_row_milestone_line_covers_the_full_visible_height():
    records = (
        [{"ID": "P", "Name": "Project", "Parent": None}],
        [
            {
                "WBS_ID": "P",
                "Activity_ID": "A",
                "Activity_Name": "Work",
                "Start_Date": "01/01/2025",
                "End_Date": "01/10/2025",
            }
        ],
    )
    figure, _ = render(records, milestones=[{"date": "01/20/2025", "label": "Deadline"}])
    hover = figure.data[-1]
    lower, upper = figure.layout.yaxis.range
    pixels = figure.layout.height - figure.layout.margin.t - figure.layout.margin.b
    assert min(hover.y) == lower and max(hover.y) == upper
    for first, last in zip(hover.y, hover.y[1:], strict=False):
        assert (last - first) / (upper - lower) * pixels <= 8.000001
    # Unlike one marker per row boundary, row-center hovers are also reachable.
    for position in (1, 2):
        assert min(abs(value - position) for value in hover.y) / (upper - lower) * pixels <= 4


def test_distant_milestones_do_not_expand_project_automatic_bounds(records):
    baseline, _ = render(records)
    figure, _ = render(records, milestones=[{"date": "01/01/2050", "label": "Distant"}])
    assert figure.layout.xaxis.range == baseline.layout.xaxis.range
    assert not figure.layout.shapes
    assert not any(trace.type == "scatter" for trace in figure.data)


def test_marker_only_chart_gets_marker_bounds_and_explicit_range_admits_markers(records):
    marker = {"date": "01/01/2050", "label": "Distant"}
    empty, _ = render(([], []), milestones=[marker])
    assert empty.layout.xaxis.range == ("2049-12-02", "2050-01-31")
    figure, rows = render(
        records, milestones=[marker], x_range=(date(2049, 12, 1), date(2050, 2, 1))
    )
    assert rows == []
    assert figure.layout.xaxis.range == ("2049-12-01", "2050-02-01")
    assert len(figure.layout.shapes) == 1


def test_equal_endpoint_milestone_range_keeps_interval_tooltip(records):
    interval, _ = render(
        records,
        milestones=[{"date": ["01/02/2025", "01/02/2025"], "label": "One-day interval"}],
    )
    point, _ = render(records, milestones=[{"date": "01/02/2025", "label": "Point"}])
    assert interval.layout.shapes[0].type == "line"
    assert "<b>Start:</b> 2025-01-02" in interval.data[-1].hovertext[0]
    assert "<b>End:</b> 2025-01-02" in interval.data[-1].hovertext[0]
    assert "<b>Duration:</b> 1 days" in interval.data[-1].hovertext[0]
    assert "<b>Date:</b> 2025-01-02" in point.data[-1].hovertext[0]
    assert "<b>Duration:</b>" not in point.data[-1].hovertext[0]


def test_bar_customdata_preserves_original_r_click_metadata(records):
    figure, _ = render(records)
    wbs, _, activity = bars(figure)
    assert wbs.customdata[0] == {
        "type": "wbs",
        "original_start": "2025-01-01",
        "original_end": "2025-01-10",
    }
    assert activity.customdata[0] == {
        "type": "activity",
        "original_start": "2025-01-01",
        "original_end": "2025-01-10",
        "activity_id": "A",
    }
    records[1][0].update(Start_Date_Actual="01/03/2025", End_Date_Actual="01/14/2025")
    stacked, _ = render(records)
    planned, actual = bars(stacked)[-2:]
    assert planned.customdata[0]["type"] == "activity_planned"
    assert actual.customdata[0] == {
        "type": "activity_actual",
        "original_start": "2025-01-03",
        "original_end": "2025-01-14",
        "activity_id": "A",
    }
