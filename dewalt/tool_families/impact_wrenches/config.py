from __future__ import annotations

from dewalt.data import load_impact_wrench_snapshot, load_impact_wrenches
from dewalt.tool_families.base import ToolFamilyDefinition, build_family_ids

from .formatting import build_display_rows, build_stat_cards, compare_display_value
from .grids import build_master_column_defs


IMPACT_WRENCH_FAMILY = ToolFamilyDefinition(
    slug="impact-wrenches",
    tab_label="Impact Wrenches",
    hero_title="Impact Wrench Compare",
    hero_copy=(
        "Compare DEWALT impact wrenches by drive size, torque, retention style, and tool size. "
        "Use the list to sort through corded tools and bare-tool cordless models."
    ),
    selection_note="Pick up to 4 impact wrenches to compare. Tap a row for full details.",
    no_selection_note=(
        "No impact wrenches picked yet. Check a few models to start a side-by-side compare."
    ),
    compare_title="Side-by-Side Compare",
    compare_fields=(
        ("sku", "SKU"),
        ("title", "Model"),
        ("series", "Series"),
        ("power_source", "Power Source"),
        ("voltage_system", "Voltage System"),
        ("torque_class", "Class"),
        ("drive_size_display", "Drive Size"),
        ("anvil_type", "Retention"),
        ("no_load_speed", "No Load Speed"),
        ("rpm_max", "Max RPM"),
        ("impact_rate_bpm", "Impact Rate"),
        ("max_fastening_torque_ft_lbs", "Max Fastening Torque"),
        ("max_breakaway_torque_ft_lbs", "Max Breakaway Torque"),
        ("tool_length_in", "Tool Length"),
        ("weight_lbs", "Weight"),
        ("brushless", "Brushless"),
        ("variable_speed", "Variable Speed"),
        ("led_light", "LED Light"),
        ("precision_wrench", "Precision Wrench"),
        ("tool_connect_ready", "Tool Connect Ready"),
        ("lanyard_ready", "Lanyard Ready"),
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
            "precision_wrench",
            "tool_connect_ready",
            "lanyard_ready",
        }
    ),
    detail_fields=(
        ("Series", "series_display"),
        ("Power Source", "power_source"),
        ("Voltage System", "voltage_system"),
        ("Class", "torque_class"),
        ("Drive Size", "drive_size_display"),
        ("Retention", "anvil_type"),
        ("No Load Speed", "no_load_speed"),
        ("Max RPM", "rpm_max"),
        ("Impact Rate", "impact_rate_bpm"),
        ("Max Fastening Torque", "max_fastening_torque_ft_lbs"),
        ("Max Breakaway Torque", "max_breakaway_torque_ft_lbs"),
        ("Tool Length", "tool_length_in"),
        ("Weight", "weight_lbs"),
        ("Brushless", "brushless"),
        ("Variable Speed", "variable_speed"),
        ("LED Light", "led_light"),
        ("Precision Wrench", "precision_wrench"),
        ("Tool Connect Ready", "tool_connect_ready"),
        ("Lanyard Ready", "lanyard_ready"),
    ),
    ids=build_family_ids("impact-wrenches"),
    load_snapshot=load_impact_wrench_snapshot,
    load_rows=load_impact_wrenches,
    build_display_rows=build_display_rows,
    compare_display_value=compare_display_value,
    build_master_column_defs=build_master_column_defs,
    build_stat_cards=build_stat_cards,
)
