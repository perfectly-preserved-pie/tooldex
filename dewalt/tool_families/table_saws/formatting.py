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


def build_size_display(row: RowData) -> str:
    """Build a display string for the table-saw blade size.

    Args:
        row: Table-saw row dictionary.

    Returns:
        A formatted blade-size string, or ``"-"`` when unavailable.
    """
    label = row.get("blade_diameter_label")
    if label:
        return f"{label} in."
    return "-"


def build_display_rows(rows: list[RowData]) -> list[RowData]:
    """Prepare table-saw rows with UI-friendly display fields.

    Args:
        rows: Raw table-saw row dictionaries loaded from the snapshot.

    Returns:
        A new list of row dictionaries augmented with display-oriented fields.
    """
    display_rows = []
    for row in rows:
        prepared_row = dict(row)
        prepared_row["series_display"] = ", ".join(row.get("series", [])) or "-"
        prepared_row["blade_diameter_display"] = build_size_display(row)
        prepared_row["amp_rating_display"] = format_numeric(row.get("amp_rating"), " A")
        prepared_row["bevel_capacity_display"] = format_numeric(
            row.get("bevel_capacity_deg"),
            " degrees",
        )
        prepared_row["rip_capacity_display"] = format_numeric(
            row.get("rip_capacity_right_in"),
            " in.",
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
        prepared_row["weight_display"] = format_numeric(row.get("weight_lbs"), " lbs")
        prepared_row["dust_extraction_display"] = format_bool(
            row.get("dust_extraction")
        )
        prepared_row["rack_and_pinion_fence_display"] = format_bool(
            row.get("rack_and_pinion_fence")
        )
        prepared_row["blade_brake_display"] = format_bool(row.get("blade_brake"))
        prepared_row["onboard_storage_display"] = format_bool(
            row.get("onboard_storage")
        )
        prepared_row["power_loss_reset_display"] = format_bool(
            row.get("power_loss_reset")
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
    """Format a table-saw row value for comparison and detail display.

    Args:
        row: Table-saw row dictionary.
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
    if field_name == "amp_rating":
        return format_numeric(value, " A")
    if field_name == "bevel_capacity_deg":
        return format_numeric(value, " degrees")
    if field_name in {"rip_capacity_right_in", "depth_cut_90_in", "depth_cut_45_in"}:
        return format_numeric(value, " in.")
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
    """Build the table-saw summary cards shown in the family overview.

    Args:
        rows: Prepared table-saw rows currently available to the dashboard.

    Returns:
        A tuple of hero statistic cards for the family.
    """
    return (
        StatCard("Table Saws", str(len(rows))),
        StatCard("Cordless", str(sum(1 for row in rows if row["power_source"] == "Cordless"))),
        StatCard("Stand Models", str(sum(1 for row in rows if row.get("stand_type") != "None"))),
        StatCard("Rack & Pinion", str(sum(1 for row in rows if row.get("rack_and_pinion_fence")))),
    )
