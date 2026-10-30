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


def test_nested_none_selects_defaults_for_every_configuration_family():
    cfg = ChartConfig.from_configs(
        color_config={
            "mode": None,
            "wbs": None,
            "uniform": {"wbs": None, "activity": None},
            "attribute": {"column": None, "mapping": None, "wbs": None},
        },
        display_config={
            "wbs": {"show": None, "show_labels": None, "show_names_on_bars": None},
            "activity": {"show": None, "show_names_on_bars": None},
            "milestone": {"hide_label_levels": None},
        },
        label_config={"wbs": None, "activity": {"yaxis": None, "bar": None}},
        bar_config={
            "wbs": {"opacity": None, "height": None},
            "activity": {
                "opacity": None,
                "height": None,
                "dim_opacity": None,
                "dim_past_activities": None,
            },
        },
        layout_config={
            "buffer_days": None,
            "indent_size": None,
            "max_visible_rows": None,
            "y_scroll_position": None,
            "yaxis_label_width": None,
            "yaxis_label_max_chars": None,
            "hover_popup_max_chars": None,
            "show_yaxis_labels": None,
            "xaxis_position": None,
        },
        tooltip_config={"wbs": None, "activity": None, "milestone": None},
    )
    assert cfg == ChartConfig()


def test_typed_configuration_none_uses_same_rules_as_dictionaries():
    from ganttify import AttributeColors, DisplayConfig, MilestoneDisplay

    assert ColorConfig(wbs=None, uniform=None, attribute=None) == ColorConfig()
    assert DisplayConfig(wbs=None, activity=None, milestone=None) == DisplayConfig()
    assert MilestoneDisplay(hide_label_levels=None).hide_label_levels == ()
    assert TooltipConfig(wbs=None, activity=None, milestone=None) == TooltipConfig()
    assert LayoutConfig(buffer_days=None, y_scroll_position=None).buffer_days == 30
    assert LayoutConfig(yaxis_label_max_chars=None).yaxis_label_max_chars is None
    assert AttributeColors(column=None, mapping=None).column is None


def test_none_does_not_bypass_required_attribute_column_validation():
    with pytest.raises(ValueError, match="attribute.column is required"):
        ChartConfig.from_configs(color_config={"mode": "attribute", "attribute": None})
