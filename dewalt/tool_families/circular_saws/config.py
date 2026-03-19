from __future__ import annotations

from dewalt.data import load_circular_saw_snapshot, load_circular_saws
from dewalt.tool_families.base import ToolFamilyDefinition, build_family_ids

from .formatting import build_display_rows, build_stat_cards, compare_display_value
from .grids import build_master_column_defs


CIRCULAR_SAW_FAMILY = ToolFamilyDefinition(
    slug="circular-saws",
    tab_label="Circular Saws",
    hero_title="Circular Saw Compare",
    hero_copy=(
        "Compare DEWALT circular saws by blade size, cut depth, bevel range, and jobsite features. "
        "Use the list to sort through corded saws and bare-tool cordless models."
    ),
    selection_note="Pick up to 4 circular saws to compare. Tap a row for full details.",
    no_selection_note=(
        "No circular saws picked yet. Check a few models to start a side-by-side compare."
    ),
    compare_title="Side-by-Side Compare",
    compare_fields=(
        ("sku", "SKU"),
        ("title", "Model"),
        ("series", "Series"),
        ("power_source", "Power Source"),
        ("voltage_system", "Voltage System"),
        ("saw_type", "Saw Type"),
        ("blade_diameter_display", "Blade Diameter"),
        ("arbor_size_display", "Arbor Size"),
        ("bevel_capacity_deg", "Bevel Capacity"),
        ("depth_cut_90_in", "Depth @ 90°"),
        ("depth_cut_45_in", "Depth @ 45°"),
        ("rpm_max", "Max RPM"),
        ("max_watts_out", "Max Watts Out"),
        ("tool_length_in", "Tool Length"),
        ("weight_lbs", "Weight"),
        ("brushless", "Brushless"),
        ("led_light", "LED Light"),
        ("electric_brake", "Electric Brake"),
        ("dust_extraction", "Dust Extraction"),
        ("rafter_hook", "Rafter Hook"),
        ("tool_connect_ready", "Tool Connect Ready"),
        ("power_detect", "POWER DETECT"),
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
            "led_light",
            "electric_brake",
            "dust_extraction",
            "rafter_hook",
            "tool_connect_ready",
            "power_detect",
        }
    ),
    detail_fields=(
        ("Series", "series_display"),
        ("Power Source", "power_source"),
        ("Voltage System", "voltage_system"),
        ("Saw Type", "saw_type"),
        ("Blade Diameter", "blade_diameter_display"),
        ("Arbor Size", "arbor_size_display"),
        ("Bevel Capacity", "bevel_capacity_deg"),
        ("Depth @ 90°", "depth_cut_90_in"),
        ("Depth @ 45°", "depth_cut_45_in"),
        ("Max RPM", "rpm_max"),
        ("Max Watts Out", "max_watts_out"),
        ("Tool Length", "tool_length_in"),
        ("Weight", "weight_lbs"),
        ("Brushless", "brushless"),
        ("LED Light", "led_light"),
        ("Electric Brake", "electric_brake"),
        ("Dust Extraction", "dust_extraction"),
        ("Rafter Hook", "rafter_hook"),
        ("Tool Connect Ready", "tool_connect_ready"),
        ("POWER DETECT", "power_detect"),
    ),
    ids=build_family_ids("circular-saws"),
    load_snapshot=load_circular_saw_snapshot,
    load_rows=load_circular_saws,
    build_display_rows=build_display_rows,
    compare_display_value=compare_display_value,
    build_master_column_defs=build_master_column_defs,
    build_stat_cards=build_stat_cards,
)
