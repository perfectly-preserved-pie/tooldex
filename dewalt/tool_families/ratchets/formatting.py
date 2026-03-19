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


def build_display_rows(rows: list[RowData]) -> list[RowData]:
    """Prepare ratchet rows with UI-friendly display fields.

    Args:
        rows: Raw ratchet row dictionaries loaded from the snapshot.

    Returns:
        A new list of row dictionaries augmented with display-oriented fields.
    """
    display_rows = []
    for row in rows:
        prepared_row = dict(row)
        prepared_row["series_display"] = ", ".join(row.get("series", [])) or "-"
        prepared_row["rpm_display"] = row.get("no_load_speed") or (
            f"{row['rpm_max']:,}" if row.get("rpm_max") else "-"
        )
        prepared_row["torque_display"] = format_numeric(
            row.get("max_torque_ft_lbs"),
            " ft-lbs",
        )
        prepared_row["tool_length_display"] = format_numeric(
            row.get("tool_length_in"),
            " in.",
        )
        prepared_row["weight_display"] = format_numeric(row.get("weight_lbs"), " lbs")
        prepared_row["brushless_display"] = format_bool(row.get("brushless"))
        prepared_row["variable_speed_display"] = format_bool(row.get("variable_speed"))
        prepared_row["led_light_display"] = format_bool(row.get("led_light"))
        prepared_row["fw_rev_switch_display"] = format_bool(row.get("fw_rev_switch"))
        prepared_row["extended_reach_display"] = format_bool(row.get("extended_reach"))
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
    """Format a ratchet row value for comparison and detail display.

    Args:
        row: Ratchet row dictionary.
        field_name: Field name to resolve from the row.

    Returns:
        A string representation suitable for comparison and detail display.
    """
    value = row.get(field_name)
    if field_name in LINE_LIST_FIELDS:
        return format_lines(value)
    if field_name == "series":
        return ", ".join(value or []) or "-"
    if field_name in {"max_torque_ft_lbs"}:
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
    """Build the ratchet summary cards shown in the family overview.

    Args:
        rows: Prepared ratchet rows currently available to the dashboard.

    Returns:
        A tuple of hero statistic cards for the family.
    """
    return (
        StatCard("Ratchets", str(len(rows))),
        StatCard("Cordless", str(sum(1 for row in rows if row["power_source"] == "Cordless"))),
        StatCard("Sealed Head", str(sum(1 for row in rows if row.get("head_type") == "Sealed Head"))),
        StatCard("Extended Reach", str(sum(1 for row in rows if row.get("extended_reach")))),
    )
