"""Normalize source tables and reject invalid project data at the boundary."""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Mapping
from datetime import date, datetime
from numbers import Real
from types import MappingProxyType
from typing import Any, cast

from .models import Activity, Milestone, Project, WBSNode

_MILESTONE_COLORS = (
    "#8B4513",
    "#2E8B57",
    "#4682B4",
    "#9932CC",
    "#FF6347",
    "#FFD700",
    "#00CED1",
    "#FF1493",
    "#32CD32",
    "#FF8C00",
)
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


def is_missing(value: Any) -> bool:
    """Recognize scalar nulls without importing pandas or NumPy."""
    if value is None:
        return True
    if type(value).__name__ in {"NAType", "NaTType"}:
        return True
    if isinstance(value, str):
        return not value.strip()
    try:
        missing = value != value
        return bool(missing)
    except (TypeError, ValueError):
        return False


def parse_date(
    value: Any,
    field: str,
    *,
    date_format: str = "%m/%d/%Y",
    optional: bool = False,
) -> date | None:
    """Parse a date object, configured string format, or ISO ``YYYY-MM-DD``.

    Ambiguous numeric dates are interpreted only with ``date_format``. Datetime
    values retain their calendar date; schedules do not represent time zones or
    time-of-day. Optional fields also accept scalar nulls and blank strings.
    """
    if is_missing(value):
        if optional:
            return None
        raise ValueError(f"{field} requires a date")
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a date, datetime, or date string")
    text = value.strip()
    try:
        if _ISO_DATE.fullmatch(text):
            return date.fromisoformat(text)
        return datetime.strptime(text, date_format).date()
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"Invalid date in {field}: {value!r}; use {date_format!r}, "
            "ISO YYYY-MM-DD, or a date object"
        ) from exc


def _is_column(value: Any) -> bool:
    return (
        not isinstance(value, (str, bytes, Mapping, date))
        and isinstance(value, Iterable)
        and hasattr(value, "__len__")
    )


def _records(data: Any, name: str) -> list[dict[str, Any]]:
    """Copy rows from records, column mappings, or DataFrame-like objects."""
    if isinstance(data, Mapping):
        if not data:
            return []
        marker = {"wbs_structure": "ID", "activities": "Activity_ID", "milestone_lines": "label"}[
            name
        ]
        if marker in data and not _is_column(data[marker]):
            source = [data]
        else:
            if not all(_is_column(column) for column in data.values()):
                raise TypeError(f"{name} column mappings must contain equal-length columns")
            columns = {key: list(values) for key, values in data.items()}
            lengths = {len(values) for values in columns.values()}
            if len(lengths) != 1:
                raise ValueError(f"{name} columns must have equal lengths")
            source = [
                dict(zip(columns, values, strict=True))
                for values in zip(*columns.values(), strict=True)
            ]
    elif callable(getattr(data, "to_dict", None)):
        try:
            source = data.to_dict(orient="records")
        except TypeError as exc:
            raise TypeError(f"{name} must support to_dict(orient='records')") from exc
    else:
        if isinstance(data, (str, bytes)) or not isinstance(data, Iterable):
            raise TypeError(f"{name} must be an iterable of mappings or a DataFrame")
        source = list(data)
    records: list[dict[str, Any]] = []
    for index, row in enumerate(source):
        if not isinstance(row, Mapping):
            raise TypeError(f"{name} row {index + 1} must be a mapping")
        if not all(isinstance(key, str) for key in row):
            raise TypeError(f"{name} row {index + 1} column names must be strings")
        records.append(dict(row))
    return records


def _require(row: Mapping[str, Any], columns: tuple[str, ...], context: str) -> None:
    missing = set(columns).difference(row)
    if missing:
        raise ValueError(f"{context} is missing required columns: {', '.join(sorted(missing))}")


def _text(value: Any, field: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ValueError(
            f"{field} must be a {'possibly empty ' if allow_empty else 'nonempty '}string"
        )
    return value


def _number(value: Any, field: str, *, minimum: float = 0, maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"{field} must be a finite number")
    result = float(value)
    if result < minimum or (maximum is not None and result > maximum):
        bounds = f"[{minimum}, {maximum}]" if maximum is not None else f">= {minimum}"
        raise ValueError(f"{field} must be {bounds}")
    return result


def _validate_graph(nodes: tuple[WBSNode, ...]) -> None:
    """Check references and cycles in linear time without recursion."""
    by_id: dict[str, WBSNode] = {}
    for node in nodes:
        if node.id in by_id:
            raise ValueError(f"Duplicate WBS ID: {node.id!r}")
        by_id[node.id] = node
    for node in nodes:
        if node.parent is not None and node.parent not in by_id:
            raise ValueError(f"WBS {node.id!r} references unknown parent {node.parent!r}")
    complete: set[str] = set()
    for node in nodes:
        trail: list[str] = []
        visiting: set[str] = set()
        current: str | None = node.id
        while current is not None and current not in complete:
            if current in visiting:
                raise ValueError(f"WBS hierarchy contains a cycle involving {current!r}")
            visiting.add(current)
            trail.append(current)
            current = by_id[current].parent
        complete.update(trail)


def _option(row: Mapping[str, Any], key: str, default: Any) -> Any:
    """Use defaults for absent optional cells, including DataFrame nulls."""
    value = row.get(key)
    return default if is_missing(value) else value


def _prepare_milestones(records: list[dict[str, Any]], date_format: str) -> tuple[Milestone, ...]:
    milestones: list[Milestone] = []
    for index, row in enumerate(records):
        context = f"milestone_lines row {index + 1}"
        _require(row, ("date", "label"), context)
        label = _text(row["label"], f"{context}.label", allow_empty=True)
        value = row["date"]
        dates = list(value) if _is_column(value) else [value]
        if len(dates) not in (1, 2):
            raise ValueError(f"{context}.date must contain one or two dates")
        start = cast(date, parse_date(dates[0], f"{context}.date", date_format=date_format))
        end = cast(date, parse_date(dates[-1], f"{context}.date", date_format=date_format))
        if end < start:
            raise ValueError(f"{context} end date must not precede start date")
        position = _option(row, "label_position", "top")
        if position not in ("top", "middle", "bottom"):
            raise ValueError(f"{context}.label_position must be 'top', 'middle', or 'bottom'")
        level = _option(row, "label_level", 1)
        if isinstance(level, bool) or level not in (1, 2):
            raise ValueError(f"{context}.label_level must be 1 or 2")
        dash = _option(row, "dash", "dash")
        if dash not in ("solid", "dash", "dot", "dashdot", "longdash", "longdashdot"):
            raise ValueError(f"{context}.dash is not a supported Plotly line style")
        width = _number(_option(row, "width", 2), f"{context}.width")
        if width == 0:
            raise ValueError(f"{context}.width must be greater than zero")
        milestones.append(
            Milestone(
                start=start,
                end=end,
                label=label,
                color=_text(
                    _option(row, "color", _MILESTONE_COLORS[index % len(_MILESTONE_COLORS)]),
                    f"{context}.color",
                ),
                dash=dash,
                width=width,
                fill_opacity=_number(
                    _option(row, "fill_opacity", 0.15 if len(dates) == 2 else 1.0),
                    f"{context}.fill_opacity",
                    maximum=1,
                ),
                label_position=position,
                label_level=int(level),
                fields=MappingProxyType(dict(row)),
            )
        )
    return tuple(milestones)


def prepare_project(
    wbs_structure: Any,
    activities: Any,
    milestone_lines: Any = None,
    *,
    date_format: str = "%m/%d/%Y",
    as_of: date,
) -> Project:
    """Copy and normalize original Ganttify input tables into a project.

    Extra fields are retained for labels, coloring, and custom tooltips. Input
    tables are never mutated. WBS identifiers and activity identifiers must each
    be unique. Empty projects and WBS nodes without activities are supported.
    """
    if not isinstance(date_format, str) or not date_format:
        raise ValueError("date_format must be a nonempty strptime format string")
    if not isinstance(as_of, date) or isinstance(as_of, datetime):
        raise TypeError("as_of must be a date")
    nodes: list[WBSNode] = []
    for index, row in enumerate(_records(wbs_structure, "wbs_structure")):
        context = f"wbs_structure row {index + 1}"
        _require(row, ("ID", "Name", "Parent"), context)
        parent_value = row["Parent"]
        parent = (
            None
            if is_missing(parent_value) or parent_value == "None"
            else _text(parent_value, f"{context}.Parent")
        )
        nodes.append(
            WBSNode(
                id=_text(row["ID"], f"{context}.ID"),
                name=_text(row["Name"], f"{context}.Name", allow_empty=True),
                parent=parent,
                fields=MappingProxyType(dict(row)),
            )
        )
    wbs = tuple(nodes)
    _validate_graph(wbs)
    wbs_ids = {node.id for node in wbs}
    prepared_activities: list[Activity] = []
    activity_ids: set[str] = set()
    for index, row in enumerate(_records(activities, "activities")):
        context = f"activities row {index + 1}"
        _require(row, ("WBS_ID", "Activity_ID", "Activity_Name", "Start_Date", "End_Date"), context)
        identifier = _text(row["Activity_ID"], f"{context}.Activity_ID")
        if identifier in activity_ids:
            raise ValueError(f"Duplicate activity ID: {identifier!r}")
        activity_ids.add(identifier)
        wbs_id = _text(row["WBS_ID"], f"{context}.WBS_ID")
        if wbs_id not in wbs_ids:
            raise ValueError(f"Activity {identifier!r} references unknown WBS ID {wbs_id!r}")
        dates = {
            field: parse_date(
                row.get(field),
                f"{context}.{field}",
                date_format=date_format,
                optional=field.endswith("_Actual"),
            )
            for field in ("Start_Date", "End_Date", "Start_Date_Actual", "End_Date_Actual")
        }
        start, end = cast(date, dates["Start_Date"]), cast(date, dates["End_Date"])
        start_actual, end_actual = dates["Start_Date_Actual"], dates["End_Date_Actual"]
        if end < start:
            raise ValueError(f"Activity {identifier!r} planned end must not precede start")
        if end_actual is not None and start_actual is None:
            raise ValueError(f"Activity {identifier!r} actual end requires an actual start")
        if start_actual is not None and end_actual is None:
            end_actual = max(as_of, start_actual)
        if start_actual is not None and end_actual is not None and end_actual < start_actual:
            raise ValueError(f"Activity {identifier!r} actual end must not precede start")
        prepared_activities.append(
            Activity(
                id=identifier,
                name=_text(row["Activity_Name"], f"{context}.Activity_Name", allow_empty=True),
                wbs_id=wbs_id,
                start=start,
                end=end,
                start_actual=start_actual,
                end_actual=end_actual,
                fields=MappingProxyType(dict(row)),
            )
        )
    milestones = (
        ()
        if milestone_lines is None
        else _prepare_milestones(_records(milestone_lines, "milestone_lines"), date_format)
    )
    return Project(wbs=wbs, activities=tuple(prepared_activities), milestones=milestones)
