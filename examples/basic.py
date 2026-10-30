"""Write a self-contained chart for the original example project."""

from datetime import date

from ganttify import ganttify
from ganttify.datasets import get_test_project


def main() -> None:
    """Create an offline HTML chart in the current directory."""
    project = get_test_project()
    chart = ganttify(
        project["wbs_structure"],
        project["activities"],
        chart_title="Software development schedule",
        color_config={"mode": "wbs", "wbs": project["colors"]},
        as_of=date(2025, 1, 1),
    )
    chart.write_html("ganttify-basic.html")
    print("Created ganttify-basic.html")


if __name__ == "__main__":
    main()
