from __future__ import annotations

from dewalt.data import load_table_saw_snapshot, load_table_saws
from dewalt.tool_families.base import ToolFamilyDefinition, build_family_ids

from .formatting import build_display_rows, build_stat_cards, compare_display_value
from .grids import build_master_column_defs


TABLE_SAW_FAMILY = ToolFamilyDefinition(
    slug="table-saws",
    tab_label="Table Saws",
    hero_title="Table Saw Compare",
    hero_copy=(
        "Compare DEWALT table saws by blade size, rip capacity, cut depth, stand setup, and jobsite features. "
        "Use the list to sort through corded saws and bare-tool cordless models."
    ),
    selection_note="Pick up to 4 table saws to compare. Tap a row for full details.",
    no_selection_note=(
        "No table saws picked yet. Check a few models to start a side-by-side compare."
    ),
    compare_title="Side-by-Side Compare",
    compare_fields=(
        ("sku", "SKU"),
        ("title", "Model"),
        ("series", "Series"),
        ("power_source", "Power Source"),
        ("voltage_system", "Voltage System"),
        ("stand_type", "Stand Type"),
        ("blade_diameter_display", "Blade Diameter"),
        ("amp_rating", "Amp Rating"),
        ("bevel_capacity_deg", "Bevel Capacity"),
        ("rip_capacity_right_in", "Rip Capacity"),
        ("depth_cut_90_in", "Depth @ 90°"),
        ("depth_cut_45_in", "Depth @ 45°"),
        ("rpm_max", "Max RPM"),
        ("weight_lbs", "Weight"),
        ("dust_extraction", "Dust Extraction"),
        ("rack_and_pinion_fence", "Rack & Pinion Fence"),
        ("blade_brake", "Blade Brake"),
        ("onboard_storage", "Onboard Storage"),
        ("power_loss_reset", "Power-Loss Reset"),
        ("description", "Overview"),
        ("features", "Primary Features"),
        ("additional_features", "Additional Features"),
        ("includes", "Includes"),
        ("applications", "Applications"),
        ("disclaimers", "Disclaimers"),
    ),
    compare_boolean_fields=frozenset(
        {
            "dust_extraction",
            "rack_and_pinion_fence",
            "blade_brake",
            "onboard_storage",
            "power_loss_reset",
        }
    ),
    detail_fields=(
        ("Series", "series_display"),
        ("Power Source", "power_source"),
        ("Voltage System", "voltage_system"),
        ("Stand Type", "stand_type"),
        ("Blade Diameter", "blade_diameter_display"),
        ("Amp Rating", "amp_rating"),
        ("Bevel Capacity", "bevel_capacity_deg"),
        ("Rip Capacity", "rip_capacity_right_in"),
        ("Depth @ 90°", "depth_cut_90_in"),
        ("Depth @ 45°", "depth_cut_45_in"),
        ("Max RPM", "rpm_max"),
        ("Weight", "weight_lbs"),
        ("Dust Extraction", "dust_extraction"),
        ("Rack & Pinion Fence", "rack_and_pinion_fence"),
        ("Blade Brake", "blade_brake"),
        ("Onboard Storage", "onboard_storage"),
        ("Power-Loss Reset", "power_loss_reset"),
    ),
    ids=build_family_ids("table-saws"),
    load_snapshot=load_table_saw_snapshot,
    load_rows=load_table_saws,
    build_display_rows=build_display_rows,
    compare_display_value=compare_display_value,
    build_master_column_defs=build_master_column_defs,
    build_stat_cards=build_stat_cards,
)
