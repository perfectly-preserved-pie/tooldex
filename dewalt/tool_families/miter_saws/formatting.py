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
    """Build a display string for the miter-saw blade size.

    Args:
        row: Miter-saw row dictionary.

    Returns:
        A formatted blade-size string, or ``"-"`` when unavailable.
    """
    label = row.get("blade_diameter_label")
    if label:
        return f"{label} in."
    return "-"


def build_display_rows(rows: list[RowData]) -> list[RowData]:
    """Prepare miter-saw rows with UI-friendly display fields.

    Args:
        rows: Raw miter-saw row dictionaries loaded from the snapshot.

    Returns:
        A new list of row dictionaries augmented with display-oriented fields.
    """
    display_rows = []
    for row in rows:
        prepared_row = dict(row)
        prepared_row["series_display"] = ", ".join(row.get("series", [])) or "-"
        prepared_row["blade_diameter_display"] = build_size_display(row)
        prepared_row["amp_rating_display"] = format_numeric(row.get("amp_rating"), " A")
        prepared_row["rpm_display"] = format_integer_display(row.get("rpm_max"))
        prepared_row["cross_cut_capacity_display"] = format_numeric(
            row.get("cross_cut_capacity_in"),
            " in.",
        )
        prepared_row["baseboard_capacity_display"] = format_numeric(
            row.get("baseboard_capacity_in"),
            " in.",
        )
        prepared_row["crown_capacity_display"] = format_numeric(
            row.get("crown_capacity_in"),
            " in.",
        )
        prepared_row["weight_display"] = format_numeric(row.get("weight_lbs"), " lbs")
        prepared_row["brushless_display"] = format_bool(row.get("brushless"))
        prepared_row["dust_extraction_display"] = format_bool(
            row.get("dust_extraction")
        )
        prepared_row["led_light_display"] = format_bool(row.get("led_light"))
        prepared_row["cutline_system_display"] = format_bool(
            row.get("cutline_system")
        )
        prepared_row["wireless_tool_control_display"] = format_bool(
            row.get("wireless_tool_control")
        )
        prepared_row["regenerative_braking_display"] = format_bool(
            row.get("regenerative_braking")
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
    """Format a miter-saw row value for comparison and detail display.

    Args:
        row: Miter-saw row dictionary.
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
    if field_name == "rpm_max":
        return format_integer_display(value)
    if field_name in {"cross_cut_capacity_in", "baseboard_capacity_in", "crown_capacity_in"}:
        return format_numeric(value, " in.")
    if field_name == "weight_lbs":
        return format_numeric(value, " lbs")
    if isinstance(value, bool):
        return format_bool(value)
    if value in (None, "", []):
        return "-"
    return str(value)


def build_stat_cards(rows: list[RowData]) -> tuple[StatCard, ...]:
    """Build the miter-saw summary cards shown in the family overview.

    Args:
        rows: Prepared miter-saw rows currently available to the dashboard.

    Returns:
        A tuple of hero statistic cards for the family.
    """
    return (
        StatCard("Miter Saws", str(len(rows))),
        StatCard("Cordless", str(sum(1 for row in rows if row["power_source"] == "Cordless"))),
        StatCard("Sliding", str(sum(1 for row in rows if row.get("saw_motion") == "Sliding"))),
        StatCard("Double Bevel", str(sum(1 for row in rows if row.get("bevel_type") == "Double Bevel"))),
    )
