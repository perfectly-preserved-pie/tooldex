from __future__ import annotations

from dewalt.tool_families.base import RowData, StatCard
from dewalt.ui.formatting import format_bool, format_lines, format_numeric


LINE_LIST_FIELDS = {
    "features",
    "additional_features",
    "includes",
    "applications",
    "disclaimers",
}


def build_chuck_size_display(row: RowData) -> str:
    """Build a display string for the impact-driver drive size."""
    label = row.get("chuck_size_label")
    if label:
        return f"{label} in."
    return "-"


def build_display_rows(rows: list[RowData]) -> list[RowData]:
    """Prepare impact-driver rows with UI-friendly display fields."""
    display_rows = []
    for row in rows:
        prepared_row = dict(row)
        prepared_row["series_display"] = ", ".join(row.get("series", [])) or "-"
        prepared_row["chuck_size_display"] = build_chuck_size_display(row)
        prepared_row["rpm_display"] = row.get("no_load_speed") or (
            f"{row['rpm_max']:,}" if row.get("rpm_max") else "-"
        )
        prepared_row["impact_rate_display"] = format_numeric(
            row.get("impact_rate_bpm"), " IPM"
        )
        prepared_row["torque_display"] = format_numeric(
            row.get("max_torque_in_lbs"), " in-lbs"
        )
        prepared_row["power_display"] = format_numeric(row.get("power_watts"), " W")
        prepared_row["tool_length_display"] = format_numeric(
            row.get("tool_length_in"), " in."
        )
        prepared_row["weight_display"] = format_numeric(row.get("weight_lbs"), " lbs")
        prepared_row["brushless_display"] = format_bool(row.get("brushless"))
        prepared_row["led_light_display"] = format_bool(row.get("led_light"))
        prepared_row["hydraulic_display"] = format_bool(row.get("hydraulic"))
        prepared_row["high_torque_display"] = format_bool(row.get("high_torque"))
        prepared_row["tool_connect_display"] = format_bool(
            row.get("tool_connect_ready")
        )
        prepared_row["lanyard_ready_display"] = format_bool(
            row.get("lanyard_ready")
        )
        prepared_row["features_display"] = format_lines(row.get("features"))
        prepared_row["additional_features_display"] = format_lines(
            row.get("additional_features")
        )
        prepared_row["includes_display"] = format_lines(row.get("includes"))
        prepared_row["applications_display"] = format_lines(row.get("applications"))
        prepared_row["disclaimers_display"] = format_lines(row.get("disclaimers"))
        display_rows.append(prepared_row)
    return display_rows


def compare_display_value(row: RowData, field_name: str) -> str:
    """Format an impact-driver row value for comparison and detail display."""
    value = row.get(field_name)
    if field_name in LINE_LIST_FIELDS:
        return format_lines(value)
    if field_name == "series":
        return ", ".join(value or []) or "-"
    if field_name == "chuck_size_display":
        return row.get("chuck_size_display", "-")
    if field_name == "impact_rate_bpm":
        return format_numeric(value, " IPM")
    if field_name == "max_torque_in_lbs":
        return format_numeric(value, " in-lbs")
    if field_name == "power_watts":
        return format_numeric(value, " W")
    if field_name == "tool_length_in":
        return format_numeric(value, " in.")
    if field_name == "weight_lbs":
        return format_numeric(value, " lbs")
    if field_name == "rpm_max":
        return f"{value:,}" if value else "-"
    if field_name == "no_load_speed":
        return value or "-"
    if isinstance(value, bool):
        return format_bool(value)
    if value in (None, "", []):
        return "-"
    return str(value)


def build_stat_cards(rows: list[RowData]) -> tuple[StatCard, ...]:
    """Build the impact-driver summary cards shown in the family overview."""
    return (
        StatCard("Impact Drivers", str(len(rows))),
        StatCard("3-Speed", str(sum(1 for row in rows if row.get("speed_count") == 3))),
        StatCard("High Torque", str(sum(1 for row in rows if row.get("high_torque")))),
        StatCard("Brushless", str(sum(1 for row in rows if row.get("brushless")))),
    )
