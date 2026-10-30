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
