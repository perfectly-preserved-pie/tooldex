from __future__ import annotations

from dewalt.tool_families.base import RowData, StatCard
from dewalt.ui.formatting import format_bool, format_lines, format_wheel_size


LINE_LIST_FIELDS = {
    "series",
    "features",
    "additional_features",
    "includes",
    "applications",
    "disclaimers",
}


def build_display_rows(rows: list[RowData]) -> list[RowData]:
    """Prepare angle grinder rows with UI-friendly display fields.

    Args:
        rows: Raw grinder row dictionaries loaded from the snapshot.

    Returns:
        A new list of row dictionaries augmented with display-oriented fields.
    """
    display_rows = []
    for row in rows:
        prepared_row = dict(row)
        prepared_row["series_display"] = ", ".join(row.get("series", [])) or "-"
        prepared_row["wheel_size_display"] = format_wheel_size(
            row.get("wheel_min_in"), row.get("wheel_max_in")
        )
        prepared_row["amp_rating_display"] = (
            f"{row['amp_rating']} A" if row.get("amp_rating") else "-"
        )
        prepared_row["horsepower_display"] = (
            f"{row['horsepower_hp']} HP" if row.get("horsepower_hp") else "-"
        )
        prepared_row["max_watts_out_display"] = (
            f"{row['max_watts_out']} W" if row.get("max_watts_out") else "-"
        )
        prepared_row["power_input_display"] = (
            f"{row['power_input_watts']} W" if row.get("power_input_watts") else "-"
        )
        prepared_row["rpm_display"] = f"{row['rpm_max']:,}" if row.get("rpm_max") else "-"
        prepared_row["brushless_display"] = format_bool(row.get("brushless"))
        prepared_row["variable_speed_display"] = format_bool(row.get("variable_speed"))
        prepared_row["anti_rotation_display"] = format_bool(row.get("anti_rotation_system"))
        prepared_row["e_clutch_display"] = format_bool(row.get("e_clutch"))
        prepared_row["kickback_brake_display"] = format_bool(row.get("kickback_brake"))
        prepared_row["tool_connect_display"] = format_bool(row.get("tool_connect_ready"))
        prepared_row["wireless_tool_control_display"] = format_bool(
            row.get("wireless_tool_control")
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
    """Format an angle grinder row value for the comparison grid or modal.

    Args:
        row: Grinder row dictionary.
        field_name: Field name to resolve from the row.

    Returns:
        A string representation suitable for comparison and detail display.
    """
    value = row.get(field_name)
    if field_name in LINE_LIST_FIELDS:
        return format_lines(value)
    if field_name == "amp_rating":
        return f"{value} A" if value else "-"
    if field_name == "horsepower_hp":
        return f"{value} HP" if value else "-"
    if field_name == "max_watts_out":
        return f"{value} W" if value else "-"
    if field_name == "power_input_watts":
        return f"{value} W" if value else "-"
    if field_name == "wheel_size_display":
        return row.get("wheel_size_display", "-")
    if field_name == "rpm_max":
        return f"{value:,}" if value else "-"
    if isinstance(value, bool):
        return format_bool(value)
    if value in (None, "", []):
        return "-"
    return str(value)


def build_stat_cards(rows: list[RowData]) -> tuple[StatCard, ...]:
    """Build the angle grinder summary cards shown in the hero section.

    Args:
        rows: Prepared angle grinder rows currently available to the dashboard.

    Returns:
        A tuple of hero statistic cards for the family.
    """
    return (
        StatCard("Grinders", str(len(rows))),
        StatCard("Cordless", str(sum(1 for row in rows if row["power_source"] == "Cordless"))),
        StatCard("Corded", str(sum(1 for row in rows if row["power_source"] != "Cordless"))),
        StatCard("Brushless", str(sum(1 for row in rows if row["brushless"]))),
    )
