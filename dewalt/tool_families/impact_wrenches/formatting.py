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


def build_drive_size_display(row: RowData) -> str:
    """Build a display string for the wrench drive size."""
    label = row.get("drive_size_label")
    if label:
        return f"{label} in."
    return "-"


def build_display_rows(rows: list[RowData]) -> list[RowData]:
    """Prepare impact-wrench rows with UI-friendly display fields."""
    display_rows = []
    for row in rows:
        prepared_row = dict(row)
        prepared_row["series_display"] = ", ".join(row.get("series", [])) or "-"
        prepared_row["drive_size_display"] = build_drive_size_display(row)
        prepared_row["rpm_display"] = row.get("no_load_speed") or (
            f"{row['rpm_max']:,}" if row.get("rpm_max") else "-"
        )
        prepared_row["impact_rate_display"] = format_numeric(
            row.get("impact_rate_bpm"), " IPM"
        )
        prepared_row["fastening_torque_display"] = format_numeric(
            row.get("max_fastening_torque_ft_lbs"), " ft-lbs"
        )
        prepared_row["breakaway_torque_display"] = format_numeric(
            row.get("max_breakaway_torque_ft_lbs"), " ft-lbs"
        )
        prepared_row["tool_length_display"] = format_numeric(
            row.get("tool_length_in"), " in."
        )
        prepared_row["weight_display"] = format_numeric(row.get("weight_lbs"), " lbs")
        prepared_row["brushless_display"] = format_bool(row.get("brushless"))
        prepared_row["variable_speed_display"] = format_bool(row.get("variable_speed"))
        prepared_row["led_light_display"] = format_bool(row.get("led_light"))
        prepared_row["precision_wrench_display"] = format_bool(
            row.get("precision_wrench")
        )
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
    """Format an impact-wrench row value for comparison and detail display."""
    value = row.get(field_name)
    if field_name in LINE_LIST_FIELDS:
        return format_lines(value)
    if field_name == "series":
        return ", ".join(value or []) or "-"
    if field_name == "drive_size_display":
        return row.get("drive_size_display", "-")
    if field_name == "impact_rate_bpm":
        return format_numeric(value, " IPM")
    if field_name in {"max_fastening_torque_ft_lbs", "max_breakaway_torque_ft_lbs"}:
        return format_numeric(value, " ft-lbs")
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
    """Build the impact-wrench summary cards shown in the family overview."""
    return (
        StatCard("Impact Wrenches", str(len(rows))),
        StatCard("Cordless", str(sum(1 for row in rows if row["power_source"] == "Cordless"))),
        StatCard("Corded", str(sum(1 for row in rows if row["power_source"] == "Corded"))),
        StatCard("High Torque", str(sum(1 for row in rows if row.get("torque_class") == "High Torque"))),
    )
