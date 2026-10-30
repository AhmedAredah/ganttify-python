"""Order visible schedule rows and roll up dates through a WBS forest."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from types import MappingProxyType
from typing import TYPE_CHECKING

from .data import _validate_graph
from .models import Activity, Project, Row

if TYPE_CHECKING:
    from .config import DisplayConfig


def _overlaps(activity: Activity, limits: tuple[date, date]) -> bool:
    start, end = limits
    if activity.end >= start and activity.start <= end:
        return True
    return (
        activity.start_actual is not None
        and activity.end_actual is not None
        and activity.end_actual >= start
        and activity.start_actual <= end
    )


def build_rows(
    project: Project,
    display: DisplayConfig,
    x_range: tuple[date, date] | None = None,
) -> list[Row]:
    """Build depth-first rows in input order with inclusive date-range filtering.

    Every WBS span includes planned and actual dates from all its descendants,
    even when activities or WBS rows are hidden. Requested ranges retain any
    activity whose planned *or* actual interval overlaps the viewport, together
    with its ancestors. Empty WBS rows remain visible when no range is supplied.
    The implementation is iterative to support deeply nested projects.
    """
    if x_range is not None and (len(x_range) != 2 or x_range[1] < x_range[0]):
        raise ValueError("x_range must contain an ordered pair of dates")
    _validate_graph(project.wbs)
    by_id = {node.id: node for node in project.wbs}
    children: dict[str | None, list[str]] = defaultdict(list)
    for node in project.wbs:
        children[node.parent].append(node.id)
    direct_activities: dict[str, list[Activity]] = defaultdict(list)
    spans: dict[str, tuple[date, date] | None] = {node.id: None for node in project.wbs}
    for activity in project.activities:
        if activity.wbs_id not in by_id:
            raise ValueError(
                f"Activity {activity.id!r} references unknown WBS ID {activity.wbs_id!r}"
            )
        direct_activities[activity.wbs_id].append(activity)
        start = (
            min(activity.start, activity.start_actual)
            if activity.start_actual is not None
            else activity.start
        )
        end = (
            max(activity.end, activity.end_actual)
            if activity.end_actual is not None
            else activity.end
        )
        previous = spans[activity.wbs_id]
        spans[activity.wbs_id] = (
            (min(previous[0], start), max(previous[1], end)) if previous else (start, end)
        )
    order: list[tuple[str, int]] = []
    stack = [(identifier, 0) for identifier in reversed(children[None])]
    while stack:
        identifier, level = stack.pop()
        order.append((identifier, level))
        stack.extend((child, level + 1) for child in reversed(children[identifier]))
    for identifier, _ in reversed(order):
        parent = by_id[identifier].parent
        span = spans[identifier]
        if parent is not None and span is not None:
            previous = spans[parent]
            spans[parent] = (
                (min(previous[0], span[0]), max(previous[1], span[1])) if previous else span
            )
    visible: set[str] | None = None
    if x_range is not None:
        visible = set()
        for identifier in direct_activities:
            direct_activities[identifier] = [
                activity
                for activity in direct_activities[identifier]
                if _overlaps(activity, x_range)
            ]
            if direct_activities[identifier]:
                current: str | None = identifier
                while current is not None and current not in visible:
                    visible.add(current)
                    current = by_id[current].parent
    rows: list[Row] = []
    for identifier, level in order:
        if visible is not None and identifier not in visible:
            continue
        node = by_id[identifier]
        span = spans[identifier]
        if display.wbs.show:
            rows.append(
                Row(
                    kind="wbs",
                    id=identifier,
                    name=node.name,
                    wbs_id=identifier,
                    level=level,
                    start=span[0] if span else None,
                    end=span[1] if span else None,
                    activity=None,
                    fields=MappingProxyType(
                        {
                            **node.fields,
                            "Level": level,
                            "Start_Date": span[0] if span else None,
                            "End_Date": span[1] if span else None,
                        }
                    ),
                )
            )
        if display.activity.show:
            for activity in direct_activities[identifier]:
                rows.append(
                    Row(
                        kind="activity",
                        id=activity.id,
                        name=activity.name,
                        wbs_id=identifier,
                        level=level + 1,
                        start=activity.start,
                        end=activity.end,
                        activity=activity,
                        fields=activity.fields,
                    )
                )
    return rows
