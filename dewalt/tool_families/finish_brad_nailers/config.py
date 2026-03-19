from __future__ import annotations

from dewalt.data import (
    load_finish_brad_nailer_snapshot,
    load_finish_brad_nailers,
)
from dewalt.tool_families.base import ToolFamilyDefinition, build_family_ids

from .formatting import build_display_rows, build_stat_cards, compare_display_value
from .grids import build_master_column_defs


FINISH_BRAD_NAILER_FAMILY = ToolFamilyDefinition(
    slug="finish-brad-nailers",
    tab_label="Finish/Brad Nailers",
    hero_title="Finish & Brad Nailer Compare",
    hero_copy=(
        "Compare DEWALT finish, brad, and pin nailers by gauge, magazine setup, fastener length, and jobsite features. "
        "Use the list to sort through pneumatic models and bare-tool cordless options."
    ),
    selection_note=(
        "Pick up to 4 finish or brad nailers to compare. Tap a row for full details."
    ),
    no_selection_note=(
        "No finish or brad nailers picked yet. Check a few models to start a side-by-side compare."
    ),
    compare_title="Side-by-Side Compare",
    compare_fields=(
        ("sku", "SKU"),
        ("title", "Model"),
        ("series", "Series"),
        ("power_source", "Power Source"),
        ("voltage_system", "Voltage System"),
        ("nailer_type", "Nailer Type"),
        ("gauge", "Gauge"),
        ("magazine_angle_deg", "Magazine Angle"),
        ("magazine_loading", "Magazine Loading"),
        ("magazine_capacity", "Magazine Capacity"),
        ("fastener_max_length_in", "Max Fastener Length"),
        ("weight_lbs", "Weight"),
        ("brushless", "Brushless"),
        ("led_light", "LED Light"),
        ("jam_clearing", "Jam Clearing"),
        ("tool_free_depth_adjust", "Tool-Free Depth"),
        ("low_nail_lockout", "Low Nail Lockout"),
        ("selectable_trigger", "Selectable Trigger"),
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
            "jam_clearing",
            "tool_free_depth_adjust",
            "low_nail_lockout",
            "selectable_trigger",
        }
    ),
    detail_fields=(
        ("Series", "series_display"),
        ("Power Source", "power_source"),
        ("Voltage System", "voltage_system"),
        ("Nailer Type", "nailer_type"),
        ("Gauge", "gauge"),
        ("Magazine Angle", "magazine_angle_deg"),
        ("Magazine Loading", "magazine_loading"),
        ("Magazine Capacity", "magazine_capacity"),
        ("Max Fastener Length", "fastener_max_length_in"),
        ("Weight", "weight_lbs"),
        ("Brushless", "brushless"),
        ("LED Light", "led_light"),
        ("Jam Clearing", "jam_clearing"),
        ("Tool-Free Depth", "tool_free_depth_adjust"),
        ("Low Nail Lockout", "low_nail_lockout"),
        ("Selectable Trigger", "selectable_trigger"),
    ),
    ids=build_family_ids("finish-brad-nailers"),
    load_snapshot=load_finish_brad_nailer_snapshot,
    load_rows=load_finish_brad_nailers,
    build_display_rows=build_display_rows,
    compare_display_value=compare_display_value,
    build_master_column_defs=build_master_column_defs,
    build_stat_cards=build_stat_cards,
)
