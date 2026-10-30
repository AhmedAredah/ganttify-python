"""Source fidelity and public usability of the bundled example project."""

from datetime import date

from ganttify import ganttify
from ganttify.data import prepare_project
from ganttify.datasets import get_test_project

EXPECTED_WBS = [
    ("W1", "Project Summary", "None"),
    ("W2", "Project Details", "W1"),
    ("W3", "Phase 1", "W2"),
    ("W4", "Phase 2", "W2"),
    ("W5", "Design Phase", "W3"),
    ("W6", "Development Phase", "W3"),
    ("W7", "Testing Phase", "W4"),
    ("W8", "Deployment Phase", "W4"),
]
# Expected values transcribed from upstream data-raw/create_test_project.R.
EXPECTED_ACTIVITIES = [
    ("A1", "W5", "Design UI", "09/09/2024", "09/30/2024", "09/09/2024", "09/28/2024"),
    ("A2", "W5", "Design Architecture", "09/15/2024", "10/05/2024", "09/16/2024", "10/06/2024"),
    ("A3", "W5", "Design Database", "09/20/2024", "09/30/2024", "09/21/2024", "09/29/2024"),
    ("A4", "W6", "Code Frontend", "10/01/2024", "11/15/2024", "10/01/2024", "11/20/2024"),
    ("A5", "W6", "Code Backend", "10/01/2024", "11/30/2024", "10/03/2024", "12/05/2024"),
    ("A6", "W6", "Code API", "10/15/2024", "11/10/2024", "10/15/2024", "11/12/2024"),
    ("A7", "W6", "Code Database", "10/20/2024", "11/05/2024", "10/22/2024", "11/08/2024"),
    ("A8", "W7", "Unit Testing", "11/01/2024", "11/15/2024", "11/01/2024", "11/16/2024"),
    ("A9", "W7", "Integration Testing", "11/10/2024", "11/25/2024", "11/12/2024", "11/27/2024"),
    ("A10", "W7", "Performance Testing", "11/20/2024", "12/05/2024", "11/20/2024", "12/06/2024"),
    ("A11", "W8", "Deploy Dev", "12/01/2024", "12/15/2024", "12/01/2024", "12/14/2024"),
    ("A12", "W8", "Deploy Staging", "12/10/2024", "12/25/2024", "12/10/2024", "12/23/2024"),
    ("A13", "W8", "Deploy Production", "12/20/2024", "01/15/2025", "12/18/2024", None),
    ("A14", "W8", "User Training", "12/25/2024", "01/10/2025", None, None),
    ("A15", "W8", "Documentation", "12/28/2024", "01/20/2025", None, None),
]


def test_example_matches_original_project_records():
    sample = get_test_project()
    assert set(sample) == {"wbs_structure", "activities", "colors"}
    assert [
        (row["ID"], row["Name"], row["Parent"]) for row in sample["wbs_structure"]
    ] == EXPECTED_WBS
    keys = (
        "Activity_ID",
        "WBS_ID",
        "Activity_Name",
        "Start_Date",
        "End_Date",
        "Start_Date_Actual",
        "End_Date_Actual",
    )
    assert [tuple(row[key] for key in keys) for row in sample["activities"]] == EXPECTED_ACTIVITIES
    assert sample["colors"] == {
        "W1": "#FF6B6B",
        "W2": "#4ECDC4",
        "W3": "#45B7D1",
        "W4": "#FFA07A",
        "W5": "#95E1D3",
        "W6": "#F38181",
        "W7": "#A8E6CF",
        "W8": "#FFD3B6",
    }


def test_every_example_call_returns_fresh_editable_nested_records():
    first = get_test_project()
    second = get_test_project()
    first["wbs_structure"][0]["Name"] = "Changed"
    first["activities"][0]["End_Date"] = "01/01/2030"
    first["colors"]["W1"] = "black"
    first["wbs_structure"].append({"ID": "extra"})
    first["activities"].clear()
    assert second == get_test_project()
    assert len(second["wbs_structure"]) == 8
    assert len(second["activities"]) == 15


def test_ongoing_production_actual_end_is_reproducible_and_sample_remains_unchanged():
    sample = get_test_project()
    project = prepare_project(sample["wbs_structure"], sample["activities"], as_of=date(2025, 2, 1))
    production = next(activity for activity in project.activities if activity.id == "A13")
    assert production.start_actual == date(2024, 12, 18)
    assert production.end_actual == date(2025, 2, 1)
    assert sample["activities"][12]["End_Date_Actual"] is None
    assert project.activities[13].start_actual is None
    assert project.activities[14].start_actual is None


def test_entire_example_renders_through_public_api():
    sample = get_test_project()
    chart = ganttify(
        sample["wbs_structure"],
        sample["activities"],
        color_config={"wbs": sample["colors"]},
        as_of=date(2025, 2, 1),
    )
    assert chart.figure.layout.meta["ganttify"]["total_rows"] == 23
    assert len(chart.figure.layout.yaxis.tickvals) == 23
    traces = [trace for trace in chart.figure.data if trace.type == "bar"]
    assert len(traces) == 36  # 8 WBS + 15 planned + 13 actual
    production = next(
        trace
        for trace in traces
        if trace.meta["ganttify"]["id"] == "A13" and trace.meta["ganttify"]["role"] == "actual"
    )
    assert production.meta["ganttify"]["end"] == "2025-02-01"
    assert production.marker.color == sample["colors"]["W8"]
    assert production.marker.pattern.shape == "/"
    assert "Ganttify Python browser enhancements" in chart.to_html(include_plotlyjs=False)
