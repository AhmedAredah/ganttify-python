"""Boundary tests for record normalization and validation."""

from datetime import date, datetime

import pytest

from ganttify.data import parse_date, prepare_project

AS_OF = date(2025, 2, 1)
WBS = [{"ID": "W1", "Name": "Project", "Parent": "None"}]
ACTIVITY = {
    "WBS_ID": "W1",
    "Activity_ID": "A1",
    "Activity_Name": "Design",
    "Start_Date": "01/01/2025",
    "End_Date": "01/10/2025",
}


def project(*, wbs=None, activities=None, milestones=None):
    return prepare_project(
        WBS if wbs is None else wbs,
        [ACTIVITY] if activities is None else activities,
        milestones,
        as_of=AS_OF,
    )


@pytest.mark.parametrize(
    "value", ["01/10/2025", "2025-01-10", date(2025, 1, 10), datetime(2025, 1, 10, 23, 59)]
)
def test_date_inputs(value):
    assert parse_date(value, "date") == date(2025, 1, 10)


def test_custom_date_format_does_not_guess_ambiguous_dates():
    assert parse_date("10/01/2025", "date", date_format="%d/%m/%Y") == date(2025, 1, 10)
    assert parse_date("2025-01-10", "date", date_format="%d/%m/%Y") == date(2025, 1, 10)
    with pytest.raises(ValueError, match="Invalid date"):
        parse_date("31/01/2025", "date")


@pytest.mark.parametrize("value", [None, "", "   ", float("nan")])
def test_optional_missing_dates(value):
    assert parse_date(value, "actual", optional=True) is None
    with pytest.raises(ValueError, match="requires a date"):
        parse_date(value, "required")


@pytest.mark.parametrize("value", [True, 20250110, [], {}])
def test_non_date_inputs_rejected(value):
    with pytest.raises(TypeError):
        parse_date(value, "date")


def test_invalid_calendar_date_rejected():
    with pytest.raises(ValueError, match="Invalid date"):
        parse_date("2025-02-29", "date")


def test_inputs_copied_and_extra_fields_preserved():
    source = dict(ACTIVITY, Status="Delayed")
    result = project(activities=[source])
    source["Activity_Name"] = "Changed later"
    assert result.activities[0].name == "Design"
    assert result.activities[0].fields["Status"] == "Delayed"
    assert source["Start_Date"] == "01/01/2025"
    with pytest.raises(TypeError):
        result.activities[0].fields["Status"] = "Changed"


def test_actual_start_only_infers_current_end_without_mutating_source():
    source = dict(ACTIVITY, Start_Date_Actual="01/02/2025")
    actual = project(activities=[source]).activities[0]
    assert actual.start_actual == date(2025, 1, 2)
    assert actual.end_actual == AS_OF
    assert "End_Date_Actual" not in source


def test_future_actual_start_infers_same_day_end():
    actual = project(activities=[dict(ACTIVITY, Start_Date_Actual="03/01/2025")]).activities[0]
    assert actual.start_actual == actual.end_actual == date(2025, 3, 1)


def test_actual_end_without_start_rejected():
    with pytest.raises(ValueError, match="actual end requires"):
        project(activities=[dict(ACTIVITY, End_Date_Actual="01/10/2025")])


@pytest.mark.parametrize(
    "updates,match",
    [
        ({"End_Date": "12/31/2024"}, "planned end"),
        ({"Start_Date_Actual": "01/10/2025", "End_Date_Actual": "01/09/2025"}, "actual end"),
        ({"WBS_ID": "missing"}, "unknown WBS"),
        ({"Activity_ID": ""}, "nonempty"),
        ({"Start_Date": None}, "requires a date"),
    ],
)
def test_invalid_activities_fail_early(updates, match):
    with pytest.raises(ValueError, match=match):
        project(activities=[dict(ACTIVITY, **updates)])


def test_duplicate_activity_ids_rejected():
    with pytest.raises(ValueError, match="Duplicate activity"):
        project(activities=[ACTIVITY, ACTIVITY])


@pytest.mark.parametrize(
    "wbs,match",
    [
        ([WBS[0], WBS[0]], "Duplicate WBS"),
        ([dict(WBS[0], Parent="missing")], "unknown parent"),
        ([dict(WBS[0], Parent="W1")], "cycle"),
        (
            [
                {"ID": "W1", "Name": "One", "Parent": "W2"},
                {"ID": "W2", "Name": "Two", "Parent": "W1"},
            ],
            "cycle",
        ),
        ([{"ID": "W1", "Name": "One"}], "missing required columns"),
    ],
)
def test_invalid_hierarchies_fail_early(wbs, match):
    with pytest.raises(ValueError, match=match):
        project(wbs=wbs, activities=[])


def test_record_and_column_mapping_and_generator_inputs():
    columns = {key: [value] for key, value in ACTIVITY.items()}
    assert project(wbs=WBS[0], activities=columns).activities[0].id == "A1"
    assert (
        project(wbs=(row for row in WBS), activities=(row for row in [ACTIVITY])).wbs[0].id == "W1"
    )
    with pytest.raises(ValueError, match="equal lengths"):
        project(activities=dict(columns, Activity_ID=["A1", "A2"]))
    with pytest.raises(TypeError, match="mapping"):
        project(activities=["A1"])


def test_empty_project_and_empty_milestones():
    assert project(wbs=[], activities=[], milestones=[]).wbs == ()
    assert project(wbs={}, activities={}).activities == ()


def test_milestone_defaults_and_range_data():
    result = project(
        milestones=[
            {"date": "2025-01-01", "label": "Kickoff"},
            {
                "date": ["2025-01-02", "2025-01-04"],
                "label": "Review",
                "Owner": "PM",
                "label_level": 2,
            },
        ]
    )
    first, second = result.milestones
    assert not first.is_area
    assert first.dash == "dash" and first.width == 2 and first.fill_opacity == 1
    assert second.is_area and second.fill_opacity == 0.15 and second.label_level == 2
    assert second.fields["Owner"] == "PM"


@pytest.mark.parametrize(
    "updates,match",
    [
        ({"date": []}, "one or two"),
        ({"date": ["2025-01-02", "2025-01-01"]}, "must not precede"),
        ({"date": None}, "requires a date"),
        ({"label_position": "center"}, "label_position"),
        ({"label_level": True}, "label_level"),
        ({"label_level": 3}, "label_level"),
        ({"width": 0}, "width"),
        ({"width": float("inf")}, "finite number"),
        ({"fill_opacity": 2}, "fill_opacity"),
        ({"dash": "zigzag"}, "line style"),
    ],
)
def test_invalid_milestones(updates, match):
    with pytest.raises(ValueError, match=match):
        project(milestones=[{"date": "2025-01-01", "label": "Kickoff", **updates}])


def test_pandas_inputs_and_missing_actuals():
    pd = pytest.importorskip("pandas")
    activities = pd.DataFrame([dict(ACTIVITY, Start_Date_Actual=pd.NaT, End_Date_Actual=pd.NA)])
    result = project(wbs=pd.DataFrame(WBS), activities=activities)
    assert result.activities[0].start_actual is None
    assert result.activities[0].end_actual is None
    assert parse_date(pd.Timestamp("2025-01-10"), "date") == date(2025, 1, 10)
    assert parse_date(pd.NaT, "date", optional=True) is None


def test_mixed_dataframe_milestone_options_use_defaults_for_null_cells():
    pd = pytest.importorskip("pandas")
    milestones = pd.DataFrame(
        [
            {"date": "2025-01-01", "label": "Kickoff", "color": "red", "width": 3},
            {"date": ["2025-01-02", "2025-01-03"], "label": "Review", "label_level": 2},
        ]
    )
    first, second = project(milestones=milestones).milestones
    assert first.color == "red" and first.width == 3 and first.label_level == 1
    assert second.width == 2 and second.label_level == 2 and second.color == "#2E8B57"
