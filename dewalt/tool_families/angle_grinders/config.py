from __future__ import annotations

from dewalt.data import load_angle_grinders, load_snapshot
from dewalt.tool_families.base import ToolFamilyDefinition, build_family_ids

from .formatting import build_display_rows, build_stat_cards, compare_display_value
from .grids import build_master_column_defs


ANGLE_GRINDER_FAMILY = ToolFamilyDefinition(
    slug="angle-grinders",
    tab_label="Angle Grinders",
    hero_title="Angle Grinder Compare",
    hero_copy=(
        "Compare DEWALT angle grinders by power, wheel size, speed, and key safety features. "
        "Use the list to sort through corded models and bare-tool cordless options."
    ),
    selection_note="Pick up to 4 grinders to compare. Tap a row for full details.",
    no_selection_note="No grinders picked yet. Check a few models to start a side-by-side compare.",
    compare_title="Side-by-Side Compare",
    compare_fields=(
        ("sku", "SKU"),
        ("title", "Model"),
        ("series", "Series"),
        ("power_source", "Power Source"),
        ("voltage_system", "Voltage System"),
        ("amp_rating", "Amp Rating"),
        ("horsepower_hp", "Horsepower"),
        ("max_watts_out", "Max Watts Out"),
        ("power_input_watts", "Power Input"),
        ("wheel_size_display", "Wheel Size"),
        ("switch_type", "Switch Type"),
        ("rpm_max", "Max RPM"),
        ("brushless", "Brushless"),
        ("variable_speed", "Variable Speed"),
        ("anti_rotation_system", "Anti-Rotation"),
        ("e_clutch", "E-CLUTCH"),
        ("kickback_brake", "Kickback Brake"),
        ("wireless_tool_control", "Wireless Tool Control"),
        ("tool_connect_ready", "Tool Connect Ready"),
        ("power_loss_reset", "Power Loss Reset"),
        ("no_volt_switch", "No-Volt Switch"),
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
            "anti_rotation_system",
            "e_clutch",
            "kickback_brake",
            "wireless_tool_control",
            "tool_connect_ready",
            "power_loss_reset",
            "no_volt_switch",
            "lanyard_ready",
        }
    ),
    detail_fields=(
        ("Series", "series_display"),
        ("Power Source", "power_source"),
        ("Voltage System", "voltage_system"),
        ("Wheel Size", "wheel_size_display"),
        ("Switch Type", "switch_type"),
        ("Max RPM", "rpm_max"),
        ("Amp Rating", "amp_rating"),
        ("Horsepower", "horsepower_hp"),
        ("Max Watts Out", "max_watts_out"),
        ("Power Input", "power_input_watts"),
        ("Brushless", "brushless"),
        ("Variable Speed", "variable_speed"),
        ("Anti-Rotation", "anti_rotation_system"),
        ("E-CLUTCH", "e_clutch"),
        ("Kickback Brake", "kickback_brake"),
        ("Tool Connect Ready", "tool_connect_ready"),
        ("Wireless Tool Control", "wireless_tool_control"),
        ("Power Loss Reset", "power_loss_reset"),
        ("No-Volt Switch", "no_volt_switch"),
        ("Lanyard Ready", "lanyard_ready"),
    ),
    ids=build_family_ids("angle-grinders"),
    load_snapshot=load_snapshot,
    load_rows=load_angle_grinders,
    build_display_rows=build_display_rows,
    compare_display_value=compare_display_value,
    build_master_column_defs=build_master_column_defs,
    build_stat_cards=build_stat_cards,
)
