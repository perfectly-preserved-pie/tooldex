from __future__ import annotations

from dewalt.data import load_miter_saw_snapshot, load_miter_saws
from dewalt.tool_families.base import ToolFamilyDefinition, build_family_ids

from .formatting import build_display_rows, build_stat_cards, compare_display_value
from .grids import build_master_column_defs


MITER_SAW_FAMILY = ToolFamilyDefinition(
    slug="miter-saws",
    tab_label="Miter Saws",
    hero_title="Miter Saw Compare",
    hero_copy=(
        "Compare DEWALT miter saws by blade size, slide style, cut capacity, and jobsite features. "
        "Use the list to sort through corded saws and bare-tool cordless models."
    ),
    selection_note="Pick up to 4 miter saws to compare. Tap a row for full details.",
    no_selection_note=(
        "No miter saws picked yet. Check a few models to start a side-by-side compare."
    ),
    compare_title="Side-by-Side Compare",
    compare_fields=(
        ("sku", "SKU"),
        ("title", "Model"),
        ("series", "Series"),
        ("power_source", "Power Source"),
        ("voltage_system", "Voltage System"),
        ("saw_motion", "Saw Motion"),
        ("bevel_type", "Bevel Type"),
        ("blade_diameter_display", "Blade Diameter"),
        ("amp_rating", "Amp Rating"),
        ("rpm_max", "Max RPM"),
        ("cross_cut_capacity_in", "Cross-Cut Capacity"),
        ("baseboard_capacity_in", "Baseboard Capacity"),
        ("crown_capacity_in", "Crown Capacity"),
        ("weight_lbs", "Weight"),
        ("brushless", "Brushless"),
        ("dust_extraction", "Dust Extraction"),
        ("led_light", "LED Light"),
        ("cutline_system", "Cutline System"),
        ("wireless_tool_control", "Wireless Tool Control"),
        ("regenerative_braking", "Regenerative Braking"),
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
            "dust_extraction",
            "led_light",
            "cutline_system",
            "wireless_tool_control",
            "regenerative_braking",
        }
    ),
    detail_fields=(
        ("Series", "series_display"),
        ("Power Source", "power_source"),
        ("Voltage System", "voltage_system"),
        ("Saw Motion", "saw_motion"),
        ("Bevel Type", "bevel_type"),
        ("Blade Diameter", "blade_diameter_display"),
        ("Amp Rating", "amp_rating"),
        ("Max RPM", "rpm_max"),
        ("Cross-Cut Capacity", "cross_cut_capacity_in"),
        ("Baseboard Capacity", "baseboard_capacity_in"),
        ("Crown Capacity", "crown_capacity_in"),
        ("Weight", "weight_lbs"),
        ("Brushless", "brushless"),
        ("Dust Extraction", "dust_extraction"),
        ("LED Light", "led_light"),
        ("Cutline System", "cutline_system"),
        ("Wireless Tool Control", "wireless_tool_control"),
        ("Regenerative Braking", "regenerative_braking"),
    ),
    ids=build_family_ids("miter-saws"),
    load_snapshot=load_miter_saw_snapshot,
    load_rows=load_miter_saws,
    build_display_rows=build_display_rows,
    compare_display_value=compare_display_value,
    build_master_column_defs=build_master_column_defs,
    build_stat_cards=build_stat_cards,
)
