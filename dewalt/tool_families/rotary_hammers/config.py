from __future__ import annotations

from dewalt.data import load_rotary_hammer_snapshot, load_rotary_hammers
from dewalt.tool_families.base import ToolFamilyDefinition, build_family_ids

from .formatting import build_display_rows, build_stat_cards, compare_display_value
from .grids import build_master_column_defs


ROTARY_HAMMER_FAMILY = ToolFamilyDefinition(
    slug="rotary-hammers",
    tab_label="Rotary Hammers",
    hero_title="Rotary Hammer Compare",
    hero_copy=(
        "Compare DEWALT rotary hammers by hammer type, impact energy, speed, and jobsite features. "
        "Use the list to sort through corded tools and bare-tool cordless models."
    ),
    selection_note="Pick up to 4 rotary hammers to compare. Tap a row for full details.",
    no_selection_note=(
        "No rotary hammers picked yet. Check a few models to start a side-by-side compare."
    ),
    compare_title="Side-by-Side Compare",
    compare_fields=(
        ("sku", "SKU"),
        ("title", "Model"),
        ("series", "Series"),
        ("power_source", "Power Source"),
        ("voltage_system", "Voltage System"),
        ("hammer_type", "Hammer Type"),
        ("chuck_size_display", "Chuck Size"),
        ("chuck_type", "Chuck Type"),
        ("handle_style", "Handle Style"),
        ("amp_rating", "Amp Rating"),
        ("rpm_max", "Max RPM"),
        ("impact_rate_bpm", "Impact Rate"),
        ("impact_energy_j", "Impact Energy"),
        ("tool_length_in", "Tool Length"),
        ("weight_lbs", "Weight"),
        ("brushless", "Brushless"),
        ("led_light", "LED Light"),
        ("anti_rotation", "Anti-Rotation"),
        ("active_vibration_control", "Vibration Control"),
        ("shocks_system", "SHOCKS System"),
        ("used_for_chipping", "Chipping Mode"),
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
            "anti_rotation",
            "active_vibration_control",
            "shocks_system",
            "used_for_chipping",
        }
    ),
    detail_fields=(
        ("Series", "series_display"),
        ("Power Source", "power_source"),
        ("Voltage System", "voltage_system"),
        ("Hammer Type", "hammer_type"),
        ("Chuck Size", "chuck_size_display"),
        ("Chuck Type", "chuck_type"),
        ("Handle Style", "handle_style"),
        ("Amp Rating", "amp_rating"),
        ("Max RPM", "rpm_max"),
        ("Impact Rate", "impact_rate_bpm"),
        ("Impact Energy", "impact_energy_j"),
        ("Tool Length", "tool_length_in"),
        ("Weight", "weight_lbs"),
        ("Brushless", "brushless"),
        ("LED Light", "led_light"),
        ("Anti-Rotation", "anti_rotation"),
        ("Vibration Control", "active_vibration_control"),
        ("SHOCKS System", "shocks_system"),
        ("Chipping Mode", "used_for_chipping"),
    ),
    ids=build_family_ids("rotary-hammers"),
    load_snapshot=load_rotary_hammer_snapshot,
    load_rows=load_rotary_hammers,
    build_display_rows=build_display_rows,
    compare_display_value=compare_display_value,
    build_master_column_defs=build_master_column_defs,
    build_stat_cards=build_stat_cards,
)
