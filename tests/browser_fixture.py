"""Generate the deterministic standalone document exercised by browser_smoke.cjs."""

import sys
from datetime import date
from pathlib import Path

from ganttify import ganttify
from ganttify.datasets import get_test_project


def main() -> None:
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
    chart.write_html(Path(sys.argv[1]), div_id="ganttify-browser-test")


if __name__ == "__main__":
    main()
