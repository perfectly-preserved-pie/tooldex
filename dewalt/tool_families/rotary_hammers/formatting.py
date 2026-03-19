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


def build_chuck_size_display(row: RowData) -> str:
    """Build a display string for the rotary-hammer chuck size.

    Args:
        row: Rotary-hammer row dictionary.

    Returns:
        A formatted chuck-size string, or ``"-"`` when unavailable.
    """
    label = row.get("chuck_size_label")
    if label:
        return f"{label} in."
    return "-"


def build_display_rows(rows: list[RowData]) -> list[RowData]:
    """Prepare rotary-hammer rows with UI-friendly display fields.

    Args:
        rows: Raw rotary-hammer row dictionaries loaded from the snapshot.

    Returns:
        A new list of row dictionaries augmented with display-oriented fields.
    """
    display_rows = []
    for row in rows:
        prepared_row = dict(row)
        prepared_row["series_display"] = ", ".join(row.get("series", [])) or "-"
        prepared_row["chuck_size_display"] = build_chuck_size_display(row)
        prepared_row["amp_rating_display"] = format_numeric(row.get("amp_rating"), " A")
        prepared_row["rpm_display"] = format_integer_display(row.get("rpm_max"))
        prepared_row["impact_rate_display"] = format_integer_display(
            row.get("impact_rate_bpm"),
            " BPM",
        )
        prepared_row["impact_energy_display"] = format_numeric(
            row.get("impact_energy_j"),
            " J",
        )
        prepared_row["tool_length_display"] = format_numeric(
            row.get("tool_length_in"),
            " in.",
        )
        prepared_row["weight_display"] = format_numeric(row.get("weight_lbs"), " lbs")
        prepared_row["brushless_display"] = format_bool(row.get("brushless"))
        prepared_row["led_light_display"] = format_bool(row.get("led_light"))
        prepared_row["anti_rotation_display"] = format_bool(row.get("anti_rotation"))
        prepared_row["active_vibration_control_display"] = format_bool(
            row.get("active_vibration_control")
        )
        prepared_row["shocks_system_display"] = format_bool(row.get("shocks_system"))
        prepared_row["used_for_chipping_display"] = format_bool(
            row.get("used_for_chipping")
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
    """Format a rotary-hammer row value for comparison and detail display.

    Args:
        row: Rotary-hammer row dictionary.
        field_name: Field name to resolve from the row.

    Returns:
        A string representation suitable for comparison and detail display.
    """
    value = row.get(field_name)
    if field_name in LINE_LIST_FIELDS:
        return format_lines(value)
    if field_name == "series":
        return ", ".join(value or []) or "-"
    if field_name == "chuck_size_display":
        return row.get("chuck_size_display", "-")
    if field_name == "amp_rating":
        return format_numeric(value, " A")
    if field_name in {"rpm_max", "impact_rate_bpm"}:
        suffix = " BPM" if field_name == "impact_rate_bpm" else ""
        return format_integer_display(value, suffix)
    if field_name == "impact_energy_j":
        return format_numeric(value, " J")
    if field_name == "tool_length_in":
        return format_numeric(value, " in.")
    if field_name == "weight_lbs":
        return format_numeric(value, " lbs")
    if isinstance(value, bool):
        return format_bool(value)
    if value in (None, "", []):
        return "-"
    return str(value)


def build_stat_cards(rows: list[RowData]) -> tuple[StatCard, ...]:
    """Build the rotary-hammer summary cards shown in the family overview.

    Args:
        rows: Prepared rotary-hammer rows currently available to the dashboard.

    Returns:
        A tuple of hero statistic cards for the family.
    """
    return (
        StatCard("Rotary Hammers", str(len(rows))),
        StatCard("Cordless", str(sum(1 for row in rows if row["power_source"] == "Cordless"))),
        StatCard("Corded", str(sum(1 for row in rows if row["power_source"] == "Corded"))),
        StatCard("Combination", str(sum(1 for row in rows if row.get("hammer_type") == "Combination"))),
    )
