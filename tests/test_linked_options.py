"""Verify layout, template, and tooltip options through the complete public API."""

from datetime import date

from ganttify import ganttify


def test_layout_templates_and_normalized_tooltip_fields_share_one_schedule():
    wbs = [
        {"ID": "R", "Name": "Root", "Parent": None},
        {"ID": "C", "Name": "Child", "Parent": "R"},
    ]
    activities = [
        {
            "WBS_ID": "C",
            "Activity_ID": "A",
            "Activity_Name": "Work",
            "Start_Date": "01/01/2025",
            "End_Date": "01/05/2025",
            "Start_Date_Actual": "01/02/2025",
            "Note": "abcdefghijklmnopqrstuvwx",
        }
    ]
    chart = ganttify(
        wbs,
        activities,
        as_of=date(2025, 1, 10),
        display_config={"activity": {"show_names_on_bars": True}},
        label_config={
            "wbs": {
                "yaxis": "{name}|{id}|{start}|{end}|{duration}",
                "bar": "WBS:{id}:{duration}",
            },
            "activity": {
                "yaxis": (
                    "{name}|{id}|{start}|{end}|{start_actual}|{end_actual}|{duration}|{wbs_id}"
                ),
                "bar": "ACT:{id}:{wbs_id}:{duration}",
            },
        },
        layout_config={
            "indent_size": 7,
            "max_visible_rows": 2,
            "y_scroll_position": 1,
            "hover_popup_max_chars": 8,
        },
        tooltip_config={
            "wbs": {"Level": "Depth", "End_Date": "Summary end"},
            "activity": {"Note": "Details", "End_Date_Actual": "Resolved end"},
        },
    )
    figure = chart.figure
    assert list(figure.layout.yaxis.range) == [0.5, 2.5]
    labels = figure.layout.meta["ganttify"]["full_labels"]
    assert labels[0] == "Root|R|01/01/2025|01/10/2025|10"
    assert labels[1].startswith("\u00a0" * 7)
    assert labels[2] == "\u00a0" * 14 + ("• Work|A|01/01/2025|01/05/2025|01/02/2025|01/10/2025|5|C")
    assert [item.text for item in figure.layout.annotations] == [
        "WBS:R:10",
        "WBS:C:10",
        "ACT:A:C:5",
    ]
    planned, actual = figure.data[-2:]
    assert planned.hovertext == actual.hovertext
    assert "abcdefgh<br>ijklmnop<br>qrstuvwx" in planned.hovertext[0]
    # Dates are wrapped with the same configured width as other selected fields.
    assert "<b>Resolved end:</b> 2025-01-<br>10" in planned.hovertext[0]
    assert "<b>Depth:</b> 0" in figure.data[0].hovertext[0]
    assert "<b>Summary end:</b> 2025-01-<br>10" in figure.data[0].hovertext[0]
