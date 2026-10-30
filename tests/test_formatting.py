"""Calendar formatting stays consistent with normalized domain values."""

from datetime import date

from ganttify.formatting import custom_tooltip, format_label
from ganttify.models import Row


def test_label_dates_have_four_digit_years_on_every_platform():
    row = Row(
        kind="wbs",
        id="W",
        name="Project",
        wbs_id="W",
        level=0,
        start=date(1, 1, 2),
        end=date(999, 12, 31),
        activity=None,
        fields={},
    )
    assert format_label("{start} - {end}", row) == "01/02/0001 - 12/31/0999"


def test_normalized_date_tooltip_keeps_iso_calendar_value():
    assert custom_tooltip({"End": date(1, 1, 2)}, {"End": "Resolved end"}, 50) == [
        "<b>Resolved end:</b> 0001-01-02"
    ]
