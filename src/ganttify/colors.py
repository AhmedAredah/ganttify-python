"""Color selection policies, independent of Plotly's rendering machinery."""

from __future__ import annotations

from typing import Any

from .config import ColorConfig
from .formatting import is_missing
from .models import Project, Row

WBS_PALETTE = (
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
)
ATTRIBUTE_PALETTE = (
    "#27AE60",
    "#F39C12",
    "#E74C3C",
    "#3498DB",
    "#9B59B6",
    "#1ABC9C",
    "#E67E22",
    "#95A5A6",
    "#34495E",
    "#16A085",
)


class ColorResolver:
    """Resolve WBS, uniform, or attribute colors with deterministic palettes."""

    def __init__(self, project: Project, config: ColorConfig) -> None:
        self._config = config
        self._wbs = (
            dict(config.wbs)
            if config.wbs
            else {
                node.id: WBS_PALETTE[index % len(WBS_PALETTE)]
                for index, node in enumerate(project.wbs)
            }
        )
        self._attributes: dict[Any, str] = dict(config.attribute.mapping)
        if config.mode == "attribute":
            column = config.attribute.column
            if not column:
                raise ValueError("Attribute color mode requires an attribute column")
            if project.activities and not any(
                column in activity.fields for activity in project.activities
            ):
                raise ValueError(f"Attribute color column {column!r} does not exist in activities")
            if not self._attributes:
                for activity in project.activities:
                    value = activity.fields.get(column)
                    if is_missing(value):
                        continue
                    try:
                        if value not in self._attributes:
                            self._attributes[value] = ATTRIBUTE_PALETTE[
                                len(self._attributes) % len(ATTRIBUTE_PALETTE)
                            ]
                    except TypeError as error:
                        raise ValueError(
                            f"Attribute color column {column!r} must contain scalar values"
                        ) from error

    def resolve(self, row: Row) -> str:
        """Return the color for one WBS or activity row."""
        config = self._config
        if config.mode == "wbs":
            return self._wbs.get(row.wbs_id, "#95A5A6" if row.kind == "wbs" else "#3498DB")
        if config.mode == "uniform":
            return config.uniform.wbs if row.kind == "wbs" else config.uniform.activity
        if row.kind == "wbs":
            return config.attribute.wbs
        value = row.fields.get(config.attribute.column or "")
        if is_missing(value):
            return "#95A5A6"
        try:
            return self._attributes.get(value, "#95A5A6")
        except TypeError:
            return "#95A5A6"
