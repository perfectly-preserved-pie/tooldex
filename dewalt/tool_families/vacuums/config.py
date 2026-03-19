from __future__ import annotations

from dewalt.data import load_vacuum_snapshot, load_vacuums
from dewalt.tool_families.base import ToolFamilyDefinition, build_family_ids

from .formatting import build_display_rows, build_stat_cards, compare_display_value
from .grids import build_master_column_defs


VACUUM_FAMILY = ToolFamilyDefinition(
    slug="vacuums",
    tab_label="Vacuums",
    hero_title="Vacuum Compare",
    hero_copy=(
        "Compare DEWALT vacuums and dust extractors by tank size, suction, hose setup, and cleanup features. "
        "Use the list to sort through corded models and tool-only cordless options."
    ),
    selection_note="Pick up to 4 vacuums to compare. Tap a row for full details.",
    no_selection_note=(
        "No vacuums picked yet. Check a few models to start a side-by-side compare."
    ),
    compare_title="Side-by-Side Compare",
    compare_fields=(
        ("sku", "SKU"),
        ("title", "Model"),
        ("series", "Series"),
        ("power_source", "Power Source"),
        ("voltage_system", "Voltage System"),
        ("vacuum_type", "Type"),
        ("tank_capacity_display", "Tank Capacity"),
        ("peak_hp", "Peak HP"),
        ("airflow_cfm", "Airflow"),
        ("air_watts", "Air Watts"),
        ("max_watts_out", "Max Watts Out"),
        ("hose_diameter_display", "Hose Diameter"),
        ("hose_length_ft", "Hose Length"),
        ("cord_length_ft", "Cord Length"),
        ("weight_lbs", "Weight"),
        ("hepa_filter", "HEPA Filter"),
        ("wet_dry", "Wet/Dry"),
        ("quiet_operation", "Quiet Operation"),
        ("wireless_tool_control", "Wireless Control"),
        ("blower_port", "Blower Port"),
        ("automatic_filter_cleaning", "Auto Filter Cleaning"),
        ("description", "Overview"),
        ("features", "Primary Features"),
        ("additional_features", "Additional Features"),
        ("includes", "Includes"),
        ("applications", "Applications"),
        ("disclaimers", "Disclaimers"),
    ),
    compare_boolean_fields=frozenset(
        {
            "hepa_filter",
            "wet_dry",
            "quiet_operation",
            "wireless_tool_control",
            "blower_port",
            "automatic_filter_cleaning",
        }
    ),
    detail_fields=(
        ("Series", "series_display"),
        ("Power Source", "power_source"),
        ("Voltage System", "voltage_system"),
        ("Type", "vacuum_type"),
        ("Tank Capacity", "tank_capacity_display"),
        ("Peak HP", "peak_hp"),
        ("Airflow", "airflow_cfm"),
        ("Air Watts", "air_watts"),
        ("Max Watts Out", "max_watts_out"),
        ("Hose Diameter", "hose_diameter_display"),
        ("Hose Length", "hose_length_ft"),
        ("Cord Length", "cord_length_ft"),
        ("Weight", "weight_lbs"),
        ("HEPA Filter", "hepa_filter"),
        ("Wet/Dry", "wet_dry"),
        ("Quiet Operation", "quiet_operation"),
        ("Wireless Control", "wireless_tool_control"),
        ("Blower Port", "blower_port"),
        ("Auto Filter Cleaning", "automatic_filter_cleaning"),
    ),
    ids=build_family_ids("vacuums"),
    load_snapshot=load_vacuum_snapshot,
    load_rows=load_vacuums,
    build_display_rows=build_display_rows,
    compare_display_value=compare_display_value,
    build_master_column_defs=build_master_column_defs,
    build_stat_cards=build_stat_cards,
)
