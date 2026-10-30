"""Demonstrate actual dates, attributes, milestones, templates, and tooltips."""

from datetime import date

from ganttify import ganttify
from ganttify.datasets import get_test_project


def main() -> None:
    """Create a configured offline HTML chart."""
    project = get_test_project()
    for activity in project["activities"]:
        activity["Status"] = "Complete" if activity["End_Date_Actual"] else "In progress"
        activity["Owner"] = "Project team"
    for item in project["wbs_structure"]:
        item["Owner"] = "Project manager"

    chart = ganttify(
        project["wbs_structure"],
        project["activities"],
        chart_title="Planned and actual delivery",
        as_of=date(2025, 1, 1),
        x_range=(date(2024, 9, 1), date(2025, 2, 1)),
        color_config={
            "mode": "attribute",
            "attribute": {
                "column": "Status",
                "mapping": {"Complete": "#27AE60", "In progress": "#F39C12"},
                "wbs": "#34495E",
            },
        },
        display_config={"activity": {"show_names_on_bars": True}},
        label_config={"activity": {"yaxis": "{id}: {name} ({duration} days)"}},
        bar_config={"activity": {"dim_past_activities": True, "dim_opacity": 0.45}},
        layout_config={
            "max_visible_rows": 12,
            "yaxis_label_width": 320,
            "xaxis_position": "both",
        },
        tooltip_config={
            "wbs": {"Owner": "Project owner"},
            "activity": ["Status", "Owner"],
            "milestone": {"Description": "Notes"},
        },
        milestone_lines=[
            {
                "date": "10/01/2024",
                "label": "Development begins",
                "color": "#3498DB",
                "Description": "Start of implementation",
            },
            {
                "date": ["11/01/2024", "12/06/2024"],
                "label": "Review period",
                "color": "#9B59B6",
                "fill_opacity": 0.12,
                "label_level": 2,
                "Description": "Testing and technical review",
            },
        ],
    )
    chart.write_html("ganttify-advanced.html")
    print("Created ganttify-advanced.html")


if __name__ == "__main__":
    main()
