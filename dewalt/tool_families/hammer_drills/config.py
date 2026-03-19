from __future__ import annotations

from dewalt.data import load_hammer_drill_snapshot, load_hammer_drills
from dewalt.tool_families.base import ToolFamilyDefinition, build_family_ids

from .formatting import build_display_rows, build_stat_cards, compare_display_value
from .grids import build_master_column_defs


HAMMER_DRILL_FAMILY = ToolFamilyDefinition(
    slug="hammer-drills",
    tab_label="Hammer Drills",
    hero_title="Hammer Drill Compare",
    hero_copy=(
        "Compare DEWALT hammer drills by power, chuck size, speed, weight, and key features. "
        "Use the list to sort through corded tools and bare-tool cordless models."
    ),
    selection_note="Pick up to 4 hammer drills to compare. Tap a row for full details.",
    no_selection_note=(
        "No hammer drills picked yet. Check a few models to start a side-by-side compare."
    ),
    compare_title="Side-by-Side Compare",
    compare_fields=(
        ("sku", "SKU"),
        ("title", "Model"),
        ("series", "Series"),
        ("power_source", "Power Source"),
        ("voltage_system", "Voltage System"),
        ("amp_rating", "Amp Rating"),
        ("chuck_size_display", "Chuck Size"),
        ("chuck_type", "Chuck Type"),
        ("speed_count", "Speed Settings"),
        ("clutch_positions", "Clutch Positions"),
        ("no_load_speed", "No Load Speed"),
        ("rpm_max", "Max RPM"),
        ("max_watts_out", "Max Watts Out"),
        ("power_output_watts", "Power Output"),
        ("tool_length_in", "Tool Length"),
        ("weight_lbs", "Weight"),
        ("brushless", "Brushless"),
        ("variable_speed", "Variable Speed"),
        ("led_light", "LED Light"),
        ("lock_on_switch", "Lock On Switch"),
        ("secondary_handle", "Secondary Handle"),
        ("tool_connect_ready", "Tool Connect Ready"),
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
            "secondary_handle",
            "tool_connect_ready",
        }
    ),
    detail_fields=(
        ("Series", "series_display"),
        ("Power Source", "power_source"),
        ("Voltage System", "voltage_system"),
        ("Chuck Size", "chuck_size_display"),
        ("Chuck Type", "chuck_type"),
        ("Speed Settings", "speed_count"),
        ("Clutch Positions", "clutch_positions"),
        ("No Load Speed", "no_load_speed"),
        ("Max RPM", "rpm_max"),
        ("Amp Rating", "amp_rating"),
        ("Max Watts Out", "max_watts_out"),
        ("Power Output", "power_output_watts"),
        ("Tool Length", "tool_length_in"),
        ("Weight", "weight_lbs"),
        ("Brushless", "brushless"),
        ("Variable Speed", "variable_speed"),
        ("LED Light", "led_light"),
        ("Lock On Switch", "lock_on_switch"),
        ("Secondary Handle", "secondary_handle"),
        ("Tool Connect Ready", "tool_connect_ready"),
    ),
    ids=build_family_ids("hammer-drills"),
    load_snapshot=load_hammer_drill_snapshot,
    load_rows=load_hammer_drills,
    build_display_rows=build_display_rows,
    compare_display_value=compare_display_value,
    build_master_column_defs=build_master_column_defs,
    build_stat_cards=build_stat_cards,
)
