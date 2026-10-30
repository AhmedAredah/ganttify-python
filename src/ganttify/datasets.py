"""Example project adapted from the original Ganttify dataset.

Copyright (C) 2026 Ahmed Aredah. SPDX-License-Identifier: GPL-3.0-only
"""

from __future__ import annotations

from typing import Any


def get_test_project() -> dict[str, Any]:
    """Return independent records for the original eight-WBS, fifteen-activity example.

    Dates retain the original MM/DD/YYYY strings. The in-progress production
    deployment has no actual end; pass ``as_of`` to ``ganttify`` for a reproducible
    chart. Every call allocates fresh lists and dictionaries.
    """
    names = [
        "Project Summary",
        "Project Details",
        "Phase 1",
        "Phase 2",
        "Design Phase",
        "Development Phase",
        "Testing Phase",
        "Deployment Phase",
    ]
    parents = ["None", "W1", "W2", "W2", "W3", "W3", "W4", "W4"]
    wbs = [
        {"ID": f"W{index}", "Name": name, "Parent": parent}
        for index, (name, parent) in enumerate(zip(names, parents, strict=True), start=1)
    ]
    activity_names = [
        "Design UI",
        "Design Architecture",
        "Design Database",
        "Code Frontend",
        "Code Backend",
        "Code API",
        "Code Database",
        "Unit Testing",
        "Integration Testing",
        "Performance Testing",
        "Deploy Dev",
        "Deploy Staging",
        "Deploy Production",
        "User Training",
        "Documentation",
    ]
    wbs_ids = ["W5"] * 3 + ["W6"] * 4 + ["W7"] * 3 + ["W8"] * 5
    starts = [
        "09/09/2024",
        "09/15/2024",
        "09/20/2024",
        "10/01/2024",
        "10/01/2024",
        "10/15/2024",
        "10/20/2024",
        "11/01/2024",
        "11/10/2024",
        "11/20/2024",
        "12/01/2024",
        "12/10/2024",
        "12/20/2024",
        "12/25/2024",
        "12/28/2024",
    ]
    ends = [
        "09/30/2024",
        "10/05/2024",
        "09/30/2024",
        "11/15/2024",
        "11/30/2024",
        "11/10/2024",
        "11/05/2024",
        "11/15/2024",
        "11/25/2024",
        "12/05/2024",
        "12/15/2024",
        "12/25/2024",
        "01/15/2025",
        "01/10/2025",
        "01/20/2025",
    ]
    actual_starts = [
        "09/09/2024",
        "09/16/2024",
        "09/21/2024",
        "10/01/2024",
        "10/03/2024",
        "10/15/2024",
        "10/22/2024",
        "11/01/2024",
        "11/12/2024",
        "11/20/2024",
        "12/01/2024",
        "12/10/2024",
        "12/18/2024",
        None,
        None,
    ]
    actual_ends = [
        "09/28/2024",
        "10/06/2024",
        "09/29/2024",
        "11/20/2024",
        "12/05/2024",
        "11/12/2024",
        "11/08/2024",
        "11/16/2024",
        "11/27/2024",
        "12/06/2024",
        "12/14/2024",
        "12/23/2024",
        None,
        None,
        None,
    ]
    activities = [
        {
            "WBS_ID": wbs_id,
            "Activity_ID": f"A{index}",
            "Activity_Name": name,
            "Start_Date": start,
            "End_Date": end,
            "Start_Date_Actual": actual_start,
            "End_Date_Actual": actual_end,
        }
        for index, (wbs_id, name, start, end, actual_start, actual_end) in enumerate(
            zip(wbs_ids, activity_names, starts, ends, actual_starts, actual_ends, strict=True),
            start=1,
        )
    ]
    colors = dict(
        zip(
            [f"W{index}" for index in range(1, 9)],
            [
                "#FF6B6B",
                "#4ECDC4",
                "#45B7D1",
                "#FFA07A",
                "#95E1D3",
                "#F38181",
                "#A8E6CF",
                "#FFD3B6",
            ],
            strict=True,
        )
    )
    return {"wbs_structure": wbs, "activities": activities, "colors": colors}
