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


def format_integer_display(value: int | None, suffix: str = "") -> str:
    """Format an integer value with separators for UI display.

    Args:
        value: Integer value or ``None``.
        suffix: Optional suffix appended to the formatted value.

    Returns:
        A comma-formatted string, or ``"-"`` when the value is missing.
    """
    if value is None:
        return "-"
    return f"{value:,}{suffix}"


def build_size_display(row: RowData, field_name: str) -> str:
    """Build a display string for a saw-size field.

    Args:
        row: Circular-saw row dictionary.
        field_name: Name of the size-label field to resolve.

    Returns:
        A formatted size string, or ``"-"`` when unavailable.
    """
    label = row.get(field_name)
    if label:
        return f"{label} in."
    return "-"


def build_display_rows(rows: list[RowData]) -> list[RowData]:
    """Prepare circular-saw rows with UI-friendly display fields.

    Args:
        rows: Raw circular-saw row dictionaries loaded from the snapshot.

    Returns:
        A new list of row dictionaries augmented with display-oriented fields.
    """
    display_rows = []
    for row in rows:
        prepared_row = dict(row)
        prepared_row["series_display"] = ", ".join(row.get("series", [])) or "-"
        prepared_row["blade_diameter_display"] = build_size_display(
            row,
            "blade_diameter_label",
        )
        prepared_row["arbor_size_display"] = build_size_display(row, "arbor_size_label")
        prepared_row["bevel_capacity_display"] = format_numeric(
            row.get("bevel_capacity_deg"),
            " degrees",
        )
        prepared_row["depth_cut_90_display"] = format_numeric(
            row.get("depth_cut_90_in"),
            " in.",
        )
        prepared_row["depth_cut_45_display"] = format_numeric(
            row.get("depth_cut_45_in"),
            " in.",
        )
        prepared_row["rpm_display"] = format_integer_display(row.get("rpm_max"))
        prepared_row["max_watts_out_display"] = format_integer_display(
            row.get("max_watts_out"),
            " W",
        )
        prepared_row["tool_length_display"] = format_numeric(
            row.get("tool_length_in"),
            " in.",
        )
        prepared_row["weight_display"] = format_numeric(row.get("weight_lbs"), " lbs")
        prepared_row["brushless_display"] = format_bool(row.get("brushless"))
        prepared_row["led_light_display"] = format_bool(row.get("led_light"))
        prepared_row["electric_brake_display"] = format_bool(row.get("electric_brake"))
        prepared_row["dust_extraction_display"] = format_bool(
            row.get("dust_extraction")
        )
        prepared_row["rafter_hook_display"] = format_bool(row.get("rafter_hook"))
        prepared_row["tool_connect_display"] = format_bool(
            row.get("tool_connect_ready")
        )
        prepared_row["power_detect_display"] = format_bool(row.get("power_detect"))
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
    """Format a circular-saw row value for comparison and detail display.

    Args:
        row: Circular-saw row dictionary.
        field_name: Field name to resolve from the row.

    Returns:
        A string representation suitable for comparison and detail display.
    """
    value = row.get(field_name)
    if field_name in LINE_LIST_FIELDS:
        return format_lines(value)
    if field_name == "series":
        return ", ".join(value or []) or "-"
    if field_name == "blade_diameter_display":
        return row.get("blade_diameter_display", "-")
    if field_name == "arbor_size_display":
        return row.get("arbor_size_display", "-")
    if field_name == "bevel_capacity_deg":
        return format_numeric(value, " degrees")
    if field_name in {"depth_cut_90_in", "depth_cut_45_in", "tool_length_in"}:
        return format_numeric(value, " in.")
    if field_name == "max_watts_out":
        return format_integer_display(value, " W")
    if field_name == "rpm_max":
        return format_integer_display(value)
    if field_name == "weight_lbs":
        return format_numeric(value, " lbs")
    if isinstance(value, bool):
        return format_bool(value)
    if value in (None, "", []):
        return "-"
    return str(value)


def build_stat_cards(rows: list[RowData]) -> tuple[StatCard, ...]:
    """Build the circular-saw summary cards shown in the family overview.

    Args:
        rows: Prepared circular-saw rows currently available to the dashboard.

    Returns:
        A tuple of hero statistic cards for the family.
    """
    return (
        StatCard("Circular Saws", str(len(rows))),
        StatCard("Brushless", str(sum(1 for row in rows if row.get("brushless")))),
        StatCard("Worm Drive", str(sum(1 for row in rows if row.get("saw_type") == "Worm Drive"))),
        StatCard("Metal Cutting", str(sum(1 for row in rows if row.get("saw_type") == "Metal Cutting"))),
    )
