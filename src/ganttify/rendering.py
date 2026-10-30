"""Plotly adapter for the validated, renderer-independent schedule model."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

import plotly.graph_objects as go

from .colors import ColorResolver
from .config import ChartConfig
from .formatting import (
    custom_tooltip,
    format_label,
    interval_tooltip,
    row_tooltip,
    safe_text,
    wrap_text,
)
from .models import Milestone, Project, Row

DAY_MS = 86_400_000


def _utc(value: date) -> datetime:
    return datetime.combine(value, time(), tzinfo=UTC)


def _safe_date_offset(value: date, days: int) -> date:
    ordinal = min(date.max.toordinal(), max(date.min.toordinal(), value.toordinal() + days))
    return date.fromordinal(ordinal)


def _bounds(
    project: Project,
    rows: Sequence[Row],
    config: ChartConfig,
    x_range: tuple[date, date] | None,
    as_of: date,
) -> tuple[date, date]:
    if x_range is not None:
        return x_range
    starts = [row.start for row in rows if row.start is not None]
    ends = [row.end for row in rows if row.end is not None]
    for row in rows:
        if row.activity is not None:
            if row.activity.start_actual is not None:
                starts.append(row.activity.start_actual)
            if row.activity.end_actual is not None:
                ends.append(row.activity.end_actual)
    for milestone in project.milestones:
        starts.append(milestone.start)
        ends.append(milestone.end)
    if not starts or not ends:
        upper = _safe_date_offset(as_of, 365)
        return (as_of, upper) if upper > as_of else (_safe_date_offset(as_of, -365), as_of)
    lower = _safe_date_offset(min(starts), -config.layout.buffer_days)
    upper = _safe_date_offset(max(ends), config.layout.buffer_days)
    if lower == upper:
        lower, upper = _safe_date_offset(lower, -1), _safe_date_offset(upper, 1)
    return lower, upper


def _viewport(count: int, config: ChartConfig) -> tuple[float, float]:
    visible = min(max(count, 1), config.layout.max_visible_rows)
    bottom = max(0.5, count - visible + 0.5)
    if config.layout.y_scroll_position is not None:
        bottom = max(
            0.5, min(float(config.layout.y_scroll_position) - 0.5, max(0.5, count - visible + 0.5))
        )
    return bottom, bottom + visible


def _truncate_label(value: str, max_chars: int | None) -> str:
    if max_chars is None:
        return value
    body = value.lstrip(" \t\u00a0")
    indent = value[: len(value) - len(body)]
    if len(body) <= max_chars:
        return value
    return indent + body[: max(0, max_chars - 1)] + "\u2026"


def _bar_trace(
    row: Row,
    *,
    start: date,
    end: date,
    position: float,
    height: float,
    color: str,
    opacity: float,
    role: str,
    hover: str,
    bounds: tuple[date, date],
) -> go.Bar:
    elapsed = (end - start).days * DAY_MS
    minimum = (bounds[1] - bounds[0]).days * DAY_MS * 0.003
    width = max(float(elapsed), minimum)
    # A marker on date.min cannot be centered before the calendar boundary.
    padding = timedelta(milliseconds=(width - elapsed) / 2)
    origin = _utc(start)
    base = origin - min(padding, origin - _utc(date.min))
    marker: dict[str, Any] = {"color": color, "line": {"width": 0}}
    if role == "actual":
        marker["pattern"] = {
            "shape": "/",
            "fillmode": "overlay",
            "solidity": 0.25,
            "fgcolor": color,
            "bgcolor": "rgba(255,255,255,0.7)",
        }
    has_actuals = (
        row.activity is not None
        and row.activity.start_actual is not None
        and row.activity.end_actual is not None
    )
    customdata = {
        "type": "wbs"
        if role == "wbs"
        else (
            "activity_actual"
            if role == "actual"
            else ("activity_planned" if has_actuals else "activity")
        ),
        "original_start": start.isoformat(),
        "original_end": end.isoformat(),
    }
    if row.kind == "activity":
        customdata["activity_id"] = row.id
    return go.Bar(
        x=[width],
        y=[position],
        base=[base.isoformat()],
        width=height,
        orientation="h",
        marker=marker,
        opacity=opacity,
        name={"planned": "Planned", "actual": "Actual", "wbs": "WBS"}[role],
        showlegend=False,
        hovertext=[hover],
        customdata=[customdata],
        hovertemplate="%{hovertext}<extra></extra>",
        meta={
            "ganttify": {
                "kind": "bar",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "row_kind": row.kind,
                "id": row.id,
                "role": role,
            }
        },
    )


def _milestone_hover(milestone: Milestone, config: ChartConfig) -> str:
    width = config.layout.hover_popup_max_chars
    lines = [f"<b>{wrap_text(milestone.label, width)}</b>"]
    if milestone.is_area:
        lines.extend(interval_tooltip(milestone.start, milestone.end))
    else:
        lines.append(f"<b>Date:</b> {milestone.start.isoformat()}")
    lines.extend(custom_tooltip(milestone.fields, config.tooltip.milestone, width))
    return "<br>".join(lines)


def _add_milestone(
    figure: go.Figure,
    milestone: Milestone,
    config: ChartConfig,
    bounds: tuple[date, date],
    count: int,
) -> None:
    if milestone.end < bounds[0] or milestone.start > bounds[1]:
        return
    midpoint = _utc(milestone.start) + (milestone.end - milestone.start) / 2
    narrow = (milestone.end - milestone.start).days < (bounds[1] - bounds[0]).days * 0.003
    is_area = milestone.is_area and not narrow
    hover = _milestone_hover(milestone, config)
    common_shape = {
        "name": "ganttify-milestone",
        "xref": "x",
        "yref": "paper",
        "y0": 0,
        "y1": 1,
        "layer": "below",
    }
    if is_area:
        figure.add_shape(
            type="rect",
            x0=milestone.start.isoformat(),
            x1=milestone.end.isoformat(),
            fillcolor=milestone.color,
            opacity=milestone.fill_opacity,
            line={"color": milestone.color, "width": 1},
            **common_shape,
        )
        # Hover belongs to the label edge rather than the shaded fill: an
        # invisible fill covering the whole area would swallow activity hovers.
        # Cap samples so a multi-decade milestone cannot inflate the document.
        samples = min(400, max(2, (milestone.end - milestone.start).days + 1))
        duration = milestone.end - milestone.start
        x_points = [
            (_utc(milestone.start) + duration * index / (samples - 1)).isoformat()
            for index in range(samples)
        ]
        lower, upper = _viewport(count, config)
        label_y = {"top": upper, "middle": (lower + upper) / 2, "bottom": lower}[
            milestone.label_position
        ]
        figure.add_trace(
            go.Scatter(
                x=x_points,
                y=[label_y] * samples,
                mode="markers",
                marker={"color": "rgba(0,0,0,0)", "size": 10},
                hovertext=[hover] * samples,
                hovertemplate="%{hovertext}<extra></extra>",
                showlegend=False,
                name=milestone.label,
                meta={
                    "ganttify": {
                        "kind": "milestone-area",
                        "label": milestone.label,
                        "label_position": milestone.label_position,
                    }
                },
            )
        )
    else:
        x = midpoint.isoformat()
        figure.add_shape(
            type="line",
            x0=x,
            x1=x,
            line={"color": milestone.color, "width": milestone.width, "dash": milestone.dash},
            **common_shape,
        )
        points = [index + 0.5 for index in range(max(count, 1) + 1)]
        figure.add_trace(
            go.Scatter(
                x=[x] * len(points),
                y=points,
                mode="markers",
                marker={"color": "rgba(0,0,0,0)", "size": 10},
                hovertext=[hover] * len(points),
                hovertemplate="%{hovertext}<extra></extra>",
                showlegend=False,
                name=milestone.label,
                meta={"ganttify": {"kind": "milestone", "label": milestone.label}},
            )
        )
    if milestone.label_level in config.display.milestone.hide_label_levels:
        return
    position = milestone.label_position
    y = {"top": 1, "middle": 0.5, "bottom": 0}[position]
    anchor = {"top": "bottom", "middle": "middle", "bottom": "top"}[position]
    shifts = {"top": (25, 5), "middle": (15, -5), "bottom": (-25, -5)}
    figure.add_annotation(
        x=midpoint.isoformat(),
        y=y,
        xref="x",
        yref="paper",
        text=safe_text(milestone.label),
        showarrow=False,
        xanchor="center",
        yanchor=anchor,
        yshift=shifts[position][milestone.label_level - 1],
        font={"size": 10, "color": milestone.color, "family": "Arial, sans-serif"},
        bgcolor="rgba(255,255,255,0.8)",
        bordercolor=milestone.color,
        borderwidth=1,
        borderpad=3,
    )


class PlotlyRenderer:
    """Render a prepared project without owning validation or persistence."""

    def render(
        self,
        project: Project,
        rows: Sequence[Row],
        config: ChartConfig,
        *,
        chart_title: str,
        x_range: tuple[date, date] | None,
        as_of: date,
    ) -> go.Figure:
        """Return a standard Plotly figure with browser runtime metadata."""
        figure = go.Figure()
        resolver = ColorResolver(project, config.color)
        bounds = _bounds(project, rows, config, x_range, as_of)
        count = len(rows)
        positions = list(range(count, 0, -1))
        full_labels: list[str] = []
        ticktext: list[str] = []
        for row, position in zip(rows, positions, strict=True):
            labels = config.label.wbs if row.kind == "wbs" else config.label.activity
            name = format_label(labels.yaxis, row)
            indent = "\u00a0" * (row.level * config.layout.indent_size)
            label = indent + ("" if row.kind == "wbs" else "\u2022 ") + name
            visible = (
                config.display.wbs.show_labels
                if row.kind == "wbs"
                else config.layout.show_yaxis_labels
            )
            full_labels.append(label if visible else "")
            shortened = safe_text(_truncate_label(label, config.layout.yaxis_label_max_chars))
            ticktext.append(
                (f"<b>{shortened}</b>" if row.kind == "wbs" else shortened) if visible else ""
            )
            if row.start is None or row.end is None:
                continue
            color = resolver.resolve(row)
            fields = config.tooltip.wbs if row.kind == "wbs" else config.tooltip.activity
            hover = row_tooltip(row, name, fields, config.layout.hover_popup_max_chars)
            bar = config.bar.wbs if row.kind == "wbs" else config.bar.activity
            opacity = bar.opacity
            if (
                row.kind == "activity"
                and config.bar.activity.dim_past_activities
                and row.end < as_of
            ):
                opacity = config.bar.activity.dim_opacity
            activity = row.activity
            actual = (
                activity is not None
                and activity.start_actual is not None
                and activity.end_actual is not None
            )
            planned_y = position + bar.height / 4 if actual else position
            figure.add_trace(
                _bar_trace(
                    row,
                    start=row.start,
                    end=row.end,
                    position=planned_y,
                    height=bar.height / 2 if actual else bar.height,
                    color=color,
                    opacity=opacity,
                    role="wbs" if row.kind == "wbs" else "planned",
                    hover=hover,
                    bounds=bounds,
                )
            )
            if (
                actual
                and activity is not None
                and activity.start_actual is not None
                and activity.end_actual is not None
            ):
                figure.add_trace(
                    _bar_trace(
                        row,
                        start=activity.start_actual,
                        end=activity.end_actual,
                        position=position - bar.height / 4,
                        height=bar.height / 2,
                        color=color,
                        opacity=opacity,
                        role="actual",
                        hover=hover,
                        bounds=bounds,
                    )
                )
            display = config.display.wbs if row.kind == "wbs" else config.display.activity
            if display.show_names_on_bars:
                annotation_end = (
                    max(row.end, activity.end_actual)
                    if actual and activity and activity.end_actual
                    else row.end
                )
                figure.add_annotation(
                    x=annotation_end.isoformat(),
                    y=position,
                    text=safe_text(format_label(labels.bar, row)),
                    showarrow=False,
                    xanchor="left",
                    xshift=5,
                    font={"size": 9, "color": "black"},
                )
        for milestone in project.milestones:
            _add_milestone(figure, milestone, config, bounds, count)
        gutter = config.layout.yaxis_label_width if any(full_labels) else 50
        if any(full_labels) and not config.layout.show_yaxis_labels:
            longest = max((len(label) for label in full_labels), default=0)
            gutter = min(gutter, max(100, longest * 7 + 20))
        top_axis = config.layout.xaxis_position in {"top", "both"}
        top_margin, bottom_margin = (
            (110 if top_axis else 90),
            (45 if config.layout.xaxis_position == "top" else 80),
        )
        visible_rows = min(max(count, 1), config.layout.max_visible_rows)
        axis = {
            "title": "Timeline",
            "type": "date",
            "tickformat": "%Y-%m-%d",
            "showgrid": False,
            "range": [value.isoformat() for value in bounds],
            "fixedrange": False,
            "side": "top" if config.layout.xaxis_position == "top" else "bottom",
        }
        figure.update_layout(
            title={"text": safe_text(chart_title), "font": {"size": 16}},
            xaxis=axis,
            yaxis={
                "title": "",
                "tickmode": "array",
                "tickvals": positions,
                "ticktext": ticktext,
                "range": list(_viewport(count, config)),
                "showgrid": True,
                "autorange": False,
                "automargin": False,
                "tickfont": {"family": "Courier New, monospace", "size": 11},
                "side": "left",
                "tickangle": 0,
                "fixedrange": False,
            },
            barmode="overlay",
            bargap=0,
            hovermode="closest",
            hoverdistance=10,
            plot_bgcolor="white",
            paper_bgcolor="white",
            showlegend=False,
            margin={"l": gutter, "r": 50, "t": top_margin, "b": bottom_margin},
            dragmode="pan",
            height=max(350, visible_rows * 28 + top_margin + bottom_margin),
            meta={
                "ganttify": {
                    "total_rows": count,
                    "max_visible_rows": config.layout.max_visible_rows,
                    "label_max_chars": config.layout.yaxis_label_max_chars,
                    "full_labels": full_labels,
                    "row_kinds": [row.kind for row in rows],
                    "gutter_width": gutter,
                }
            },
        )
        if config.layout.xaxis_position == "both":
            figure.add_trace(
                go.Scatter(
                    x=[bounds[0].isoformat()],
                    y=[0],
                    xaxis="x2",
                    mode="markers",
                    marker={"size": 0.1, "opacity": 0},
                    hoverinfo="skip",
                    showlegend=False,
                )
            )
            figure.update_layout(
                xaxis2={
                    "type": "date",
                    "overlaying": "x",
                    "side": "top",
                    "matches": "x",
                    "showgrid": False,
                    "tickformat": "%Y-%m-%d",
                    "range": [value.isoformat() for value in bounds],
                }
            )
        return figure
