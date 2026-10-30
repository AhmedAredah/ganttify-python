"""Validate that configuration errors fail at the public API boundary."""

import pytest

from ganttify import BarConfig, ChartConfig, ColorConfig, LayoutConfig, TooltipConfig


def test_nested_partial_options_and_no_mutation():
    options = {"activity": {"height": 0.6}}
    config = ChartConfig.from_configs(bar_config=options)
    options["activity"]["height"] = 0.2
    assert config.bar.activity.height == 0.6
    assert config.bar.activity.opacity == 1.0
    assert config.bar.wbs.height == 0.3


def test_mapping_options_are_frozen_copies():
    colors = {"W1": "red"}
    config = ColorConfig(wbs=colors)
    colors["W1"] = "blue"
    assert config.wbs["W1"] == "red"
    with pytest.raises(TypeError):
        config.wbs["W1"] = "blue"


@pytest.mark.parametrize(
    "options",
    [
        {"layout_config": {"max_visible_rows": 0}},
        {"layout_config": {"xaxis_position": "left"}},
        {"layout_config": {"max_visible_rows": True}},
        {"layout_config": {"typo": 10}},
        {"bar_config": {"activity": {"opacity": 1.1}}},
        {"bar_config": {"activity": {"height": 0}}},
        {"bar_config": {"activity": {"opacity": float("nan")}}},
        {"color_config": {"mode": "attribute"}},
        {"display_config": {"activity": {"show": "false"}}},
        {"tooltip_config": {"activity": "Status"}},
        {"display_config": {"milestone": {"hide_label_levels": [3]}}},
    ],
)
def test_invalid_options(options):
    with pytest.raises((ValueError, TypeError)):
        ChartConfig.from_configs(**options)


def test_typed_configs_and_tooltip_aliases():
    cfg = ChartConfig.from_configs(
        layout_config=LayoutConfig(xaxis_position="both"),
        bar_config=BarConfig(),
        tooltip_config=TooltipConfig(activity={"Status": "Current status"}),
    )
    assert cfg.layout.xaxis_position == "both"
    assert cfg.tooltip.activity["Status"] == "Current status"
