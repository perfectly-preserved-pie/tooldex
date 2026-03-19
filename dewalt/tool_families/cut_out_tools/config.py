from __future__ import annotations

from dewalt.data import load_cut_out_tool_snapshot, load_cut_out_tools
from dewalt.tool_families.base import ToolFamilyDefinition, build_family_ids

from .formatting import build_display_rows, build_stat_cards, compare_display_value
from .grids import build_master_column_defs


CUT_OUT_TOOL_FAMILY = ToolFamilyDefinition(
    slug="cut-out-tools",
    tab_label="Cut-Out Tools",
    hero_title="Cut-Out Tool Compare",
    hero_copy=(
        "Compare DEWALT cut-out tools by size, speed, and the features that matter for light cutting work. "
        "Use the list to sort through corded models and bare-tool cordless options."
    ),
    selection_note="Pick up to 4 cut-out tools to compare. Tap a row for full details.",
    no_selection_note=(
        "No cut-out tools picked yet. Check a few models to start a side-by-side compare."
    ),
    compare_title="Side-by-Side Compare",
    compare_fields=(
        ("sku", "SKU"),
        ("title", "Model"),
        ("series", "Series"),
        ("power_source", "Power Source"),
        ("voltage_system", "Voltage System"),
        ("tool_type", "Tool Type"),
        ("collet_size_display", "Collet Size"),
        ("wheel_diameter_display", "Wheel Diameter"),
        ("max_cut_depth_in", "Max Cut Depth"),
        ("rpm_max", "Max RPM"),
        ("max_watts_out", "Max Watts Out"),
        ("tool_length_in", "Tool Length"),
        ("weight_lbs", "Weight"),
        ("brushless", "Brushless"),
        ("led_light", "LED Light"),
        ("tool_free_bit_change", "Tool-Free Bit Change"),
        ("axis_lock", "Axis Lock"),
        ("dust_extraction", "Dust Extraction"),
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
            "led_light",
            "tool_free_bit_change",
            "axis_lock",
            "dust_extraction",
            "tool_connect_ready",
        }
    ),
    detail_fields=(
        ("Series", "series_display"),
        ("Power Source", "power_source"),
        ("Voltage System", "voltage_system"),
        ("Tool Type", "tool_type"),
        ("Collet Size", "collet_size_display"),
        ("Wheel Diameter", "wheel_diameter_display"),
        ("Max Cut Depth", "max_cut_depth_in"),
        ("Max RPM", "rpm_max"),
        ("Max Watts Out", "max_watts_out"),
        ("Tool Length", "tool_length_in"),
        ("Weight", "weight_lbs"),
        ("Brushless", "brushless"),
        ("LED Light", "led_light"),
        ("Tool-Free Bit Change", "tool_free_bit_change"),
        ("Axis Lock", "axis_lock"),
        ("Dust Extraction", "dust_extraction"),
        ("Tool Connect Ready", "tool_connect_ready"),
    ),
    ids=build_family_ids("cut-out-tools"),
    load_snapshot=load_cut_out_tool_snapshot,
    load_rows=load_cut_out_tools,
    build_display_rows=build_display_rows,
    compare_display_value=compare_display_value,
    build_master_column_defs=build_master_column_defs,
    build_stat_cards=build_stat_cards,
)
