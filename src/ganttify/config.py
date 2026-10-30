"""Typed, immutable chart options with strict validation at the API boundary."""

from __future__ import annotations

import math
import types
from collections.abc import Mapping, Sequence
from dataclasses import MISSING, dataclass, field, fields
from types import MappingProxyType
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints


def _convert(value: Any, annotation: Any, path: str) -> Any:
    if annotation is Any:
        return value
    origin, args = get_origin(annotation), get_args(annotation)
    if origin in (Union, types.UnionType):
        for candidate in args:
            try:
                return _convert(value, candidate, path)
            except (TypeError, ValueError):
                pass
        raise TypeError(f"{path} has an invalid value: {value!r}")
    if annotation is type(None):
        if value is not None:
            raise TypeError(f"{path} must be None")
        return None
    if origin is Literal:
        if value not in args:
            raise ValueError(f"{path} must be one of {args!r}")
        return value
    if isinstance(annotation, type) and issubclass(annotation, _Config):
        if isinstance(value, annotation):
            return value
        if not isinstance(value, Mapping):
            raise TypeError(f"{path} must be a mapping or {annotation.__name__}")
        unknown = value.keys() - {f.name for f in fields(annotation)}  # type: ignore[arg-type]
        if unknown:
            raise ValueError(f"Unknown option(s) in {path}: {', '.join(map(str, unknown))}")
        return annotation(**value)
    if origin is Mapping:
        if not isinstance(value, Mapping):
            raise TypeError(f"{path} must be a mapping")
        return MappingProxyType(
            {
                _convert(k, args[0], f"{path} key"): _convert(v, args[1], f"{path}[{k!r}]")
                for k, v in value.items()
            }
        )
    if origin in (tuple, Sequence):
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
            raise TypeError(f"{path} must be a sequence")
        return tuple(_convert(v, args[0], path) for v in value)
    if annotation is float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{path} must be a number")
        if not math.isfinite(value):
            raise ValueError(f"{path} must be finite")
        return float(value)
    if annotation in (int, bool, str):
        if type(value) is not annotation:
            raise TypeError(f"{path} must be {annotation.__name__}")
        return value
    raise TypeError(f"Unsupported option type for {path}: {annotation}")


class _Config:
    __slots__ = ()

    def __post_init__(self) -> None:
        hints = get_type_hints(type(self))
        for item in fields(self):  # type: ignore[arg-type]
            annotation = hints[item.name]
            value = getattr(self, item.name)
            # R's NULL selects the default for ordinary configuration fields.
            # Preserve None only where it has an explicit, nullable meaning.
            nullable = annotation is type(None) or (
                get_origin(annotation) in (Union, types.UnionType)
                and type(None) in get_args(annotation)
            )
            if value is None and not nullable:
                if item.default is not MISSING:
                    value = item.default
                elif item.default_factory is not MISSING:
                    value = item.default_factory()
            object.__setattr__(
                self,
                item.name,
                _convert(value, annotation, item.name),
            )
        self._validate()

    def _validate(self) -> None:
        pass


def _unit(value: float, name: str) -> None:
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class UniformColors(_Config):
    wbs: str = "#34495E"
    activity: str = "#2ECC71"


@dataclass(frozen=True, slots=True)
class AttributeColors(_Config):
    column: str | None = None
    mapping: Mapping[Any, str] = field(default_factory=dict)
    wbs: str = "#34495E"


@dataclass(frozen=True, slots=True)
class ColorConfig(_Config):
    mode: Literal["wbs", "uniform", "attribute"] = "wbs"
    wbs: Mapping[str, str] = field(default_factory=dict)
    uniform: UniformColors = field(default_factory=UniformColors)
    attribute: AttributeColors = field(default_factory=AttributeColors)

    def _validate(self) -> None:
        if self.mode == "attribute" and not self.attribute.column:
            raise ValueError("attribute.column is required for attribute color mode")


@dataclass(frozen=True, slots=True)
class WBSDisplay(_Config):
    show: bool = True
    show_labels: bool = True
    show_names_on_bars: bool = True


@dataclass(frozen=True, slots=True)
class ActivityDisplay(_Config):
    show: bool = True
    show_names_on_bars: bool = False


@dataclass(frozen=True, slots=True)
class MilestoneDisplay(_Config):
    hide_label_levels: tuple[int, ...] = ()

    def _validate(self) -> None:
        if any(level not in (1, 2) for level in self.hide_label_levels):
            raise ValueError("hide_label_levels may contain only 1 and 2")


@dataclass(frozen=True, slots=True)
class DisplayConfig(_Config):
    wbs: WBSDisplay = field(default_factory=WBSDisplay)
    activity: ActivityDisplay = field(default_factory=ActivityDisplay)
    milestone: MilestoneDisplay = field(default_factory=MilestoneDisplay)


@dataclass(frozen=True, slots=True)
class LabelTemplate(_Config):
    yaxis: str = "{name}"
    bar: str = "{name}"


@dataclass(frozen=True, slots=True)
class LabelConfig(_Config):
    wbs: LabelTemplate = field(default_factory=LabelTemplate)
    activity: LabelTemplate = field(default_factory=LabelTemplate)


@dataclass(frozen=True, slots=True)
class WBSBar(_Config):
    opacity: float = 0.3
    height: float = 0.3

    def _validate(self) -> None:
        _unit(self.opacity, "wbs.opacity")
        if not 0 < self.height <= 1:
            raise ValueError("wbs.height must be greater than 0 and at most 1")


@dataclass(frozen=True, slots=True)
class ActivityBar(_Config):
    opacity: float = 1.0
    height: float = 0.8
    dim_opacity: float = 0.3
    dim_past_activities: bool = False

    def _validate(self) -> None:
        _unit(self.opacity, "activity.opacity")
        _unit(self.dim_opacity, "activity.dim_opacity")
        if not 0 < self.height <= 1:
            raise ValueError("activity.height must be greater than 0 and at most 1")


@dataclass(frozen=True, slots=True)
class BarConfig(_Config):
    wbs: WBSBar = field(default_factory=WBSBar)
    activity: ActivityBar = field(default_factory=ActivityBar)


@dataclass(frozen=True, slots=True)
class LayoutConfig(_Config):
    buffer_days: int = 30
    indent_size: int = 2
    max_visible_rows: int = 20
    y_scroll_position: float | None = None
    yaxis_label_width: int = 300
    yaxis_label_max_chars: int | None = None
    hover_popup_max_chars: int = 50
    show_yaxis_labels: bool = True
    xaxis_position: Literal["bottom", "top", "both"] = "bottom"

    def _validate(self) -> None:
        if self.buffer_days < 0 or self.indent_size < 0:
            raise ValueError("buffer_days and indent_size must be nonnegative")
        if self.max_visible_rows < 1:
            raise ValueError("max_visible_rows must be at least 1")
        if self.yaxis_label_width < 20:
            raise ValueError("yaxis_label_width must be at least 20")
        if self.yaxis_label_max_chars is not None and self.yaxis_label_max_chars < 1:
            raise ValueError("yaxis_label_max_chars must be at least 1")
        if self.hover_popup_max_chars < 1:
            raise ValueError("hover_popup_max_chars must be at least 1")


TooltipFields = Sequence[str] | Mapping[str, str]


@dataclass(frozen=True, slots=True)
class TooltipConfig(_Config):
    wbs: TooltipFields = ()
    activity: TooltipFields = ()
    milestone: TooltipFields = ()


@dataclass(frozen=True, slots=True)
class ChartConfig(_Config):
    color: ColorConfig = field(default_factory=ColorConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    label: LabelConfig = field(default_factory=LabelConfig)
    bar: BarConfig = field(default_factory=BarConfig)
    layout: LayoutConfig = field(default_factory=LayoutConfig)
    tooltip: TooltipConfig = field(default_factory=TooltipConfig)

    @classmethod
    def from_configs(
        cls,
        *,
        color_config: ColorConfig | Mapping[str, Any] | None = None,
        display_config: DisplayConfig | Mapping[str, Any] | None = None,
        label_config: LabelConfig | Mapping[str, Any] | None = None,
        bar_config: BarConfig | Mapping[str, Any] | None = None,
        layout_config: LayoutConfig | Mapping[str, Any] | None = None,
        tooltip_config: TooltipConfig | Mapping[str, Any] | None = None,
    ) -> ChartConfig:
        """Merge supplied sections with defaults without mutating caller data."""
        supplied: dict[str, Any] = {
            "color": color_config,
            "display": display_config,
            "label": label_config,
            "bar": bar_config,
            "layout": layout_config,
            "tooltip": tooltip_config,
        }
        return cls(**{key: value for key, value in supplied.items() if value is not None})
