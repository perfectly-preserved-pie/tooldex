from __future__ import annotations

from dewalt.data import (
    load_oscillating_multi_tool_snapshot,
    load_oscillating_multi_tools,
)
from dewalt.tool_families.base import ToolFamilyDefinition, build_family_ids

from .formatting import build_display_rows, build_stat_cards, compare_display_value
from .grids import build_master_column_defs


OSCILLATING_MULTI_TOOL_FAMILY = ToolFamilyDefinition(
    slug="oscillating-multi-tools",
    tab_label="Oscillating Multi-Tools",
    hero_title="Oscillating Multi-Tool Compare",
    hero_copy=(
        "Compare DEWALT oscillating multi-tools by speed, size, weight, and key features. "
        "Use the list to sort through corded tools and bare-tool cordless models."
    ),
    selection_note=(
        "Pick up to 4 oscillating multi-tools to compare. Tap a row for full details."
    ),
    no_selection_note=(
        "No oscillating multi-tools picked yet. Check a few models to start a side-by-side compare."
    ),
    compare_title="Side-by-Side Compare",
    compare_fields=(
        ("sku", "SKU"),
        ("title", "Model"),
        ("series", "Series"),
        ("power_source", "Power Source"),
        ("voltage_system", "Voltage System"),
        ("speed_count", "Speed Settings"),
        ("oscillations_per_min", "Max OPM"),
        ("tool_length_in", "Tool Length"),
        ("weight_lbs", "Weight"),
        ("brushless", "Brushless"),
        ("variable_speed", "Variable Speed"),
        ("led_light", "LED Light"),
        ("lock_on_switch", "Lock On Switch"),
        ("tool_free_accessory_change", "Tool-Free Accessory Change"),
        ("description", "Overview"),
        ("features", "Primary Features"),
        ("additional_features", "Additional Features"),
        ("includes", "Includes"),
        ("applications", "Applications"),
        ("disclaimers", "Disclaimers"),
    ),
    compare_boolean_fields=frozenset(
        {
            "brushless",
            "variable_speed",
            "led_light",
            "lock_on_switch",
            "tool_free_accessory_change",
        }
    ),
    detail_fields=(
        ("Series", "series_display"),
        ("Power Source", "power_source"),
        ("Voltage System", "voltage_system"),
        ("Speed Settings", "speed_count"),
        ("Max OPM", "oscillations_per_min"),
        ("Tool Length", "tool_length_in"),
        ("Weight", "weight_lbs"),
        ("Brushless", "brushless"),
        ("Variable Speed", "variable_speed"),
        ("LED Light", "led_light"),
        ("Lock On Switch", "lock_on_switch"),
        ("Tool-Free Accessory Change", "tool_free_accessory_change"),
    ),
    ids=build_family_ids("oscillating-multi-tools"),
    load_snapshot=load_oscillating_multi_tool_snapshot,
    load_rows=load_oscillating_multi_tools,
    build_display_rows=build_display_rows,
    compare_display_value=compare_display_value,
    build_master_column_defs=build_master_column_defs,
    build_stat_cards=build_stat_cards,
)
