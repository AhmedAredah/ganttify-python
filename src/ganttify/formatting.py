"""Pure formatting helpers shared by chart labels and hover content."""

from __future__ import annotations

import re
import textwrap
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from html import escape
from numbers import Real
from typing import Any

from .models import Row


def is_missing(value: Any) -> bool:
    """Recognize empty scalar values without depending on pandas or NumPy."""
    if value is None or type(value).__name__ in {"NAType", "NaTType"}:
        return True
    if isinstance(value, str):
        return not value.strip()
    return isinstance(value, Real) and bool(value != value)


def safe_text(value: Any) -> str:
    """Escape user text before inserting it into Plotly's limited HTML markup."""
    return escape(str(value), quote=True)


def wrap_text(value: Any, width: int) -> str:
    """Wrap before escaping so HTML entities do not distort the character limit."""
    lines = textwrap.wrap(
        str(value),
        width=width,
        break_long_words=True,
        break_on_hyphens=False,
        replace_whitespace=True,
    )
    return "<br>".join(safe_text(line) for line in lines)


def label_values(row: Row) -> dict[str, Any]:
    """Build the original library's template namespace for a display row."""
    activity = row.activity
    return {
        "name": row.name,
        "id": row.id,
        "start": row.start,
        "end": row.end,
        "duration": (row.end - row.start).days + 1 if row.start and row.end else None,
        "wbs_id": row.wbs_id,
        "start_actual": activity.start_actual if activity else None,
        "end_actual": activity.end_actual if activity else None,
    }


def format_label(template: str, row: Row) -> str:
    """Substitute known placeholders, retaining unknown placeholders literally."""
    values = label_values(row)

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            return match.group(0)
        value = values[key]
        if value is None:
            return ""
        if isinstance(value, (datetime, date)):
            return value.strftime("%m/%d/%Y")
        return str(value)

    return re.sub(r"\{([a-z_]+)\}", replace, template)


def custom_tooltip(
    fields: Mapping[str, Any], selection: Sequence[str] | Mapping[str, str], width: int
) -> list[str]:
    """Render selected scalar fields while omitting missing and empty values."""
    entries = (
        selection.items() if isinstance(selection, Mapping) else ((key, key) for key in selection)
    )
    lines = []
    for key, title in entries:
        value = fields.get(key)
        if is_missing(value):
            continue
        if isinstance(value, (datetime, date)):
            value = value.isoformat()
        lines.append(f"<b>{safe_text(title)}:</b> {wrap_text(value, width)}")
    return lines


def interval_tooltip(start: date, end: date) -> list[str]:
    """Use inclusive calendar days for the user-facing duration."""
    return [
        f"<b>Start:</b> {start.isoformat()}",
        f"<b>End:</b> {end.isoformat()}",
        f"<b>Duration:</b> {(end - start).days + 1} days",
    ]


def row_tooltip(row: Row, label: str, fields: Sequence[str] | Mapping[str, str], width: int) -> str:
    """Generate the same complete tooltip for planned and actual bars."""
    lines = [f"<b>{wrap_text(label, width)}</b>"]
    activity = row.activity
    if row.start is not None and row.end is not None:
        if activity and activity.start_actual is not None and activity.end_actual is not None:
            lines.append("<b>Planned:</b>")
            lines.extend(interval_tooltip(row.start, row.end))
            lines.extend(["", "<b>Actual:</b>"])
            lines.extend(interval_tooltip(activity.start_actual, activity.end_actual))
            variance = (activity.end_actual - activity.start_actual).days - (
                row.end - row.start
            ).days
            lines.extend([f"<b>Variance:</b> {variance:+d} days", ""])
        else:
            lines.extend(interval_tooltip(row.start, row.end))
    lines.extend(custom_tooltip(row.fields, fields, width))
    return "<br>".join(lines)
