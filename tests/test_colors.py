"""Color policy behavior for incomplete and user-provided attributes."""

from datetime import date

import pytest

from ganttify.colors import ATTRIBUTE_PALETTE, ColorResolver
from ganttify.config import AttributeColors, ColorConfig, DisplayConfig
from ganttify.data import prepare_project
from ganttify.scheduling import build_rows


def project_and_rows(statuses):
    activities = [
        {
            "WBS_ID": "W",
            "Activity_ID": f"A{index}",
            "Activity_Name": "Activity",
            "Start_Date": "2025-01-01",
            "End_Date": "2025-01-10",
            **status,
        }
        for index, status in enumerate(statuses)
    ]
    project = prepare_project(
        [{"ID": "W", "Name": "Project", "Parent": None}], activities, as_of=date(2025, 2, 1)
    )
    return project, build_rows(project, DisplayConfig())


def test_generated_attribute_colors_follow_first_appearance_without_missing_shifts():
    project, rows = project_and_rows(
        [
            {"Status": None},
            {"Status": "Delayed"},
            {"Status": ""},
            {"Status": "Complete"},
            {"Status": "Delayed"},
            {},
        ]
    )
    resolver = ColorResolver(
        project, ColorConfig(mode="attribute", attribute=AttributeColors(column="Status"))
    )
    assert [resolver.resolve(row) for row in rows] == [
        "#34495E",
        "#95A5A6",
        ATTRIBUTE_PALETTE[0],
        "#95A5A6",
        ATTRIBUTE_PALETTE[1],
        ATTRIBUTE_PALETTE[0],
        "#95A5A6",
    ]


def test_generated_attribute_palette_cycles_for_many_distinct_values():
    project, rows = project_and_rows([{"Status": f"S{index}"} for index in range(12)])
    resolver = ColorResolver(project, ColorConfig(mode="attribute", attribute={"column": "Status"}))
    assert [resolver.resolve(row) for row in rows[1:]] == list(ATTRIBUTE_PALETTE) + list(
        ATTRIBUTE_PALETTE[:2]
    )


def test_generated_attribute_colors_reject_non_scalar_categories():
    project, _ = project_and_rows([{"Status": ["Delayed", "High priority"]}])
    with pytest.raises(ValueError, match="must contain scalar values"):
        ColorResolver(project, ColorConfig(mode="attribute", attribute={"column": "Status"}))


def test_missing_attribute_column_is_distinct_from_missing_cells():
    project, _ = project_and_rows([{"Owner": "PM"}, {}])
    with pytest.raises(ValueError, match="does not exist"):
        ColorResolver(project, ColorConfig(mode="attribute", attribute={"column": "Status"}))


@pytest.mark.parametrize(
    ("value", "text"),
    [(1, "1"), (1.0, "1"), (-2, "-2"), (2.5, "2.5"), (True, "TRUE"), (False, "FALSE")],
)
def test_json_string_mapping_keys_match_native_scalar_categories(value, text):
    import json

    project, rows = project_and_rows([{"Status": value}])
    mapping = json.loads(json.dumps({text: "red"}))
    resolver = ColorResolver(
        project, ColorConfig(mode="attribute", attribute={"column": "Status", "mapping": mapping})
    )
    assert resolver.resolve(rows[1]) == "red"


def test_native_category_key_takes_precedence_over_canonical_string():
    project, rows = project_and_rows([{"Status": 1}, {"Status": "1"}])
    resolver = ColorResolver(
        project,
        ColorConfig(
            mode="attribute", attribute={"column": "Status", "mapping": {1: "red", "1": "blue"}}
        ),
    )
    assert [resolver.resolve(row) for row in rows[1:]] == ["red", "blue"]


def test_boolean_does_not_match_numeric_key():
    project, rows = project_and_rows([{"Status": True}, {"Status": 1}])
    resolver = ColorResolver(
        project,
        ColorConfig(
            mode="attribute",
            attribute={"column": "Status", "mapping": {1: "red", "TRUE": "blue"}},
        ),
    )
    assert [resolver.resolve(row) for row in rows[1:]] == ["blue", "red"]


def test_generated_palette_keeps_booleans_and_strings_distinct_from_numbers():
    project, rows = project_and_rows(
        [{"Status": True}, {"Status": 1}, {"Status": 1.0}, {"Status": "1"}]
    )
    resolver = ColorResolver(project, ColorConfig(mode="attribute", attribute={"column": "Status"}))
    assert [resolver.resolve(row) for row in rows[1:]] == [
        ATTRIBUTE_PALETTE[0],
        ATTRIBUTE_PALETTE[1],
        ATTRIBUTE_PALETTE[1],
        ATTRIBUTE_PALETTE[2],
    ]


def test_normalized_dates_accept_iso_strings_and_native_date_key_precedence():
    project, rows = project_and_rows([{"Start_Date": date(2025, 1, 1)}])
    iso = ColorResolver(
        project,
        ColorConfig(
            mode="attribute", attribute={"column": "Start_Date", "mapping": {"2025-01-01": "red"}}
        ),
    )
    assert iso.resolve(rows[1]) == "red"
    native = ColorResolver(
        project,
        ColorConfig(
            mode="attribute",
            attribute={
                "column": "Start_Date",
                "mapping": {"2025-01-01": "red", date(2025, 1, 1): "blue"},
            },
        ),
    )
    assert native.resolve(rows[1]) == "blue"


def test_inferred_actual_end_reaches_attribute_color_lookup():
    project, rows = project_and_rows([{"Start_Date_Actual": "2025-01-02"}])
    resolver = ColorResolver(
        project,
        ColorConfig(
            mode="attribute",
            attribute={"column": "End_Date_Actual", "mapping": {"2025-02-01": "red"}},
        ),
    )
    assert resolver.resolve(rows[1]) == "red"
