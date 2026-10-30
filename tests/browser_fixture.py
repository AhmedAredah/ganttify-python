"""Generate the deterministic standalone document exercised by browser_smoke.cjs."""

import sys
from datetime import date
from pathlib import Path
from typing import Any

from ganttify import GanttChart, ganttify
from ganttify.datasets import get_test_project


def smoke_chart() -> GanttChart:
    project = get_test_project()
    project["activities"].insert(
        0,
        {
            "WBS_ID": "W1",
            "Activity_ID": "SAME-DAY",
            "Activity_Name": "Same day dispatch with a deliberately long accessible label 🚢",
            "Start_Date": "09/10/2024",
            "End_Date": "09/10/2024",
            "Owner": "Harbor team",
        },
    )
    chart = ganttify(
        project["wbs_structure"],
        project["activities"],
        as_of=date(2025, 1, 1),
        x_range=("2024-09-01", "2025-03-01"),
        milestone_lines=[
            {"date": ["09/05/2024", "09/20/2024"], "label": "Review area"},
            {"date": "12/01/2024", "label": "Release"},
        ],
        layout_config={
            "max_visible_rows": 8,
            "yaxis_label_width": 180,
            "yaxis_label_max_chars": 18,
            "xaxis_position": "both",
        },
        tooltip_config={"activity": {"Owner": "Responsible team"}},
    )
    return chart


def regression_chart(case: str) -> GanttChart:
    """Build focused public-API examples for real-browser regression checks."""
    if case in {"margin", "static", "labels"} or case.startswith("matrix-"):
        project = get_test_project()
        options: dict[str, Any] = {"max_visible_rows": 8, "xaxis_position": "both"}
        display = None
        if case.startswith("matrix-"):
            _, position, activities, wbs = case.split("-")
            options["xaxis_position"] = position
            options["show_yaxis_labels"] = activities == "1"
            display = {"wbs": {"show_labels": wbs == "1"}}
        chart = ganttify(
            project["wbs_structure"],
            project["activities"],
            as_of=date(2025, 1, 1),
            layout_config=options,
            display_config=display,
        )
        if case == "margin":
            chart.figure.update_layout(margin_l=80)
        if case == "labels":
            chart.figure.update_yaxes(
                ticktext=[
                    f"Custom row {index + 1} with a deliberately long title"
                    for index in range(len(chart.figure.layout.yaxis.tickvals))
                ]
            )
            chart.figure.update_layout(margin_l=100)
        return chart

    wbs = [{"ID": "P", "Name": "Project", "Parent": None}]
    activity: dict[str, Any] = {
        "WBS_ID": "P",
        "Activity_ID": "A",
        "Activity_Name": "Normalized schedule",
        "Start_Date": "01/01/2025",
        "End_Date": "01/10/2025",
    }
    if case == "normalized":
        activity.update(Start_Date_Actual="01/02/2025", End_Date_Actual=None, Status=1)
        return ganttify(
            wbs,
            [activity],
            as_of=date(2025, 2, 1),
            x_range=(date(2025, 1, 1), date(2025, 2, 10)),
            color_config={
                "mode": "attribute",
                "attribute": {"column": "Status", "mapping": {"1": "red"}},
            },
            tooltip_config={"activity": {"End_Date_Actual": "Computed actual end"}},
            milestone_lines=[{"date": ["02/05/2025", "02/05/2025"], "label": "One day range"}],
        )
    if case == "area":
        return ganttify(
            wbs,
            [activity],
            as_of=date(2025, 2, 1),
            x_range=(date(2025, 1, 1), date(2025, 2, 1)),
            milestone_lines=[{"date": ["01/01/1900", "01/01/2100"], "label": "Long review area"}],
        )
    if case in {"line", "line-scroll"}:
        activities = [activity]
        if case == "line-scroll":
            activities = [{**activity, "Activity_ID": f"A{index}"} for index in range(10)]
        return ganttify(
            wbs,
            activities,
            as_of=date(2025, 2, 1),
            x_range=(date(2025, 1, 1), date(2025, 1, 31)),
            layout_config={"max_visible_rows": 3},
            milestone_lines=[{"date": "01/20/2025", "label": "Deadline"}],
        )
    raise ValueError(f"Unknown browser fixture case: {case}")


def main() -> None:
    case = sys.argv[2] if len(sys.argv) > 2 else "smoke"
    chart = smoke_chart() if case == "smoke" else regression_chart(case)
    chart.write_html(
        Path(sys.argv[1]),
        div_id="ganttify-browser-test",
        config={"staticPlot": True} if case == "static" else None,
    )


if __name__ == "__main__":
    main()
