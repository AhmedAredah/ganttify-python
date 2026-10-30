"""Schedule behavior and hierarchy regression tests."""

from datetime import date

from ganttify.config import DisplayConfig
from ganttify.data import prepare_project
from ganttify.scheduling import build_rows

AS_OF = date(2025, 2, 1)


def activity(identifier, wbs_id, start="2025-01-01", end="2025-01-10", **extras):
    return dict(
        Activity_ID=identifier,
        Activity_Name=identifier,
        WBS_ID=wbs_id,
        Start_Date=start,
        End_Date=end,
        **extras,
    )


def test_hierarchy_order_and_rolled_up_planned_actual_spans():
    project = prepare_project(
        [
            {"ID": "child", "Name": "Child", "Parent": "root"},
            {"ID": "other", "Name": "Other", "Parent": None},
            {"ID": "root", "Name": "Root", "Parent": ""},
        ],
        [
            activity("A1", "child", Start_Date_Actual="2024-12-31", End_Date_Actual="2025-01-20"),
            activity("A2", "root"),
        ],
        as_of=AS_OF,
    )
    rows = build_rows(project, DisplayConfig())
    assert [row.id for row in rows] == ["other", "root", "A2", "child", "A1"]
    assert [row.level for row in rows] == [0, 0, 1, 1, 2]
    assert rows[0].start is None and rows[0].end is None
    assert rows[1].start == date(2024, 12, 31)
    assert rows[1].end == date(2025, 1, 20)
    assert rows[3].start == rows[1].start
    assert rows[3].end == rows[1].end


def test_wbs_fields_expose_computed_values_over_conflicting_source_fields():
    nodes = [
        {
            "ID": "root",
            "Name": "Root",
            "Parent": None,
            "Level": 99,
            "Start_Date": "Wrong source value",
            "End_Date": "Another wrong value",
            "Owner": "PM",
        },
        {"ID": "child", "Name": "Child", "Parent": "root"},
        {"ID": "empty", "Name": "Empty", "Parent": None, "Level": 42},
    ]
    project = prepare_project(
        nodes,
        [activity("A", "child", Start_Date_Actual="2024-12-31", End_Date_Actual="2025-01-20")],
        as_of=AS_OF,
    )
    rows = build_rows(project, DisplayConfig())
    root, child, _, empty = rows
    for row, level in ((root, 0), (child, 1)):
        assert row.fields["Level"] == row.level == level
        assert row.fields["Start_Date"] == row.start == date(2024, 12, 31)
        assert row.fields["End_Date"] == row.end == date(2025, 1, 20)
    assert root.fields["Owner"] == "PM"
    assert empty.fields["Level"] == 0
    assert empty.fields["Start_Date"] is None and empty.fields["End_Date"] is None
    assert nodes[0]["Level"] == 99 and nodes[0]["Start_Date"] == "Wrong source value"
    assert project.wbs[0].fields["Level"] == 99  # original node fields remain untouched


def test_visibility_removes_rows_without_affecting_spans():
    from ganttify.config import ActivityDisplay, WBSDisplay

    project = prepare_project(
        [{"ID": "W1", "Name": "Root", "Parent": None}], [activity("A1", "W1")], as_of=AS_OF
    )
    activity_rows = build_rows(project, DisplayConfig(wbs=WBSDisplay(show=False)))
    assert [row.id for row in activity_rows] == ["A1"]
    wbs_rows = build_rows(project, DisplayConfig(activity=ActivityDisplay(show=False)))
    assert [row.id for row in wbs_rows] == ["W1"]
    assert wbs_rows[0].end == date(2025, 1, 10)
    assert (
        build_rows(
            project, DisplayConfig(wbs=WBSDisplay(show=False), activity=ActivityDisplay(show=False))
        )
        == []
    )


def test_range_filters_by_planned_or_actual_overlap_and_keeps_ancestors():
    project = prepare_project(
        [
            {"ID": "root", "Name": "Root", "Parent": None},
            {"ID": "child", "Name": "Child", "Parent": "root"},
            {"ID": "empty", "Name": "Empty", "Parent": None},
        ],
        [
            activity(
                "actual_visible",
                "child",
                Start_Date_Actual="2025-02-01",
                End_Date_Actual="2025-02-05",
            ),
            activity("planned_visible", "child", "2025-02-05", "2025-02-06"),
            activity("hidden", "root", "2025-03-01", "2025-03-10"),
        ],
        as_of=AS_OF,
    )
    rows = build_rows(project, DisplayConfig(), (date(2025, 2, 5), date(2025, 2, 5)))
    assert [row.id for row in rows] == ["root", "child", "actual_visible", "planned_visible"]
    assert rows[0].end == date(2025, 3, 10)  # rollup uses full project
    assert build_rows(project, DisplayConfig(), (date(2024, 1, 1), date(2024, 2, 1))) == []


def test_deep_tree_is_iterative_and_linear():
    count = 2500
    nodes = [
        {"ID": f"W{i}", "Name": f"Level {i}", "Parent": f"W{i - 1}" if i else None}
        for i in range(count)
    ]
    project = prepare_project(nodes, [activity("A", f"W{count - 1}")], as_of=AS_OF)
    rows = build_rows(project, DisplayConfig())
    assert len(rows) == count + 1
    assert rows[-1].level == count
    assert rows[0].start == rows[-1].start == date(2025, 1, 1)
    filtered = build_rows(project, DisplayConfig(), (date(2025, 1, 1), date(2025, 1, 1)))
    assert len(filtered) == count + 1
