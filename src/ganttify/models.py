"""Validated, renderer-independent project and schedule data models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class WBSNode:
    """A work breakdown structure node with its original source fields."""

    id: str
    name: str
    parent: str | None
    fields: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class Activity:
    """An activity with planned dates and optional actual dates."""

    id: str
    name: str
    wbs_id: str
    start: date
    end: date
    start_actual: date | None
    end_actual: date | None
    fields: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class Milestone:
    """A single date marker or a closed date interval."""

    start: date
    end: date
    label: str
    color: str
    dash: str
    width: float
    fill_opacity: float
    label_position: str
    label_level: int
    fields: Mapping[str, Any]

    @property
    def is_area(self) -> bool:
        """Whether this milestone covers more than one date."""
        return self.start != self.end


@dataclass(frozen=True, slots=True)
class Project:
    """A normalized project, independent of plotting or tabular libraries."""

    wbs: tuple[WBSNode, ...]
    activities: tuple[Activity, ...]
    milestones: tuple[Milestone, ...]


@dataclass(frozen=True, slots=True)
class Row:
    """One visible schedule row; dates may be absent on empty WBS nodes."""

    kind: Literal["wbs", "activity"]
    id: str
    name: str
    wbs_id: str
    level: int
    start: date | None
    end: date | None
    activity: Activity | None
    fields: Mapping[str, Any]
