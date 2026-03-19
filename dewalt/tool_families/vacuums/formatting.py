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


def build_display_rows(rows: list[RowData]) -> list[RowData]:
    """Prepare vacuum rows with UI-friendly display fields.

    Args:
        rows: Raw vacuum row dictionaries loaded from the snapshot.

    Returns:
        A new list of row dictionaries augmented with display-oriented fields.
    """
    display_rows = []
    for row in rows:
        prepared_row = dict(row)
        prepared_row["series_display"] = ", ".join(row.get("series", [])) or "-"
        prepared_row["tank_capacity_display"] = row.get("tank_capacity_display") or "-"
        prepared_row["hose_diameter_display"] = row.get("hose_diameter_display") or "-"
        prepared_row["peak_hp_display"] = format_numeric(row.get("peak_hp"), " HP")
        prepared_row["airflow_display"] = format_integer_display(
            row.get("airflow_cfm"),
            " CFM",
        )
        prepared_row["air_watts_display"] = format_integer_display(
            row.get("air_watts"),
            " AW",
        )
        prepared_row["max_watts_out_display"] = format_integer_display(
            row.get("max_watts_out"),
            " W",
        )
        prepared_row["hose_length_display"] = format_numeric(
            row.get("hose_length_ft"),
            " ft",
        )
        prepared_row["cord_length_display"] = format_numeric(
            row.get("cord_length_ft"),
            " ft",
        )
        prepared_row["weight_display"] = format_numeric(row.get("weight_lbs"), " lbs")
        prepared_row["hepa_filter_display"] = format_bool(row.get("hepa_filter"))
        prepared_row["wet_dry_display"] = format_bool(row.get("wet_dry"))
        prepared_row["quiet_operation_display"] = format_bool(
            row.get("quiet_operation")
        )
        prepared_row["wireless_tool_control_display"] = format_bool(
            row.get("wireless_tool_control")
        )
        prepared_row["blower_port_display"] = format_bool(row.get("blower_port"))
        prepared_row["automatic_filter_cleaning_display"] = format_bool(
            row.get("automatic_filter_cleaning")
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
    """Format a vacuum row value for comparison and detail display.

    Args:
        row: Vacuum row dictionary.
        field_name: Field name to resolve from the row.

    Returns:
        A string representation suitable for comparison and detail display.
    """
    value = row.get(field_name)
    if field_name in LINE_LIST_FIELDS:
        return format_lines(value)
    if field_name == "series":
        return ", ".join(value or []) or "-"
    if field_name in {"tank_capacity_display", "hose_diameter_display"}:
        return str(value or "-")
    if field_name == "peak_hp":
        return format_numeric(value, " HP")
    if field_name == "airflow_cfm":
        return format_integer_display(value, " CFM")
    if field_name == "air_watts":
        return format_integer_display(value, " AW")
    if field_name == "max_watts_out":
        return format_integer_display(value, " W")
    if field_name in {"hose_length_ft", "cord_length_ft"}:
        return format_numeric(value, " ft")
    if field_name == "weight_lbs":
        return format_numeric(value, " lbs")
    if isinstance(value, bool):
        return format_bool(value)
    if value in (None, "", []):
        return "-"
    return str(value)


def build_stat_cards(rows: list[RowData]) -> tuple[StatCard, ...]:
    """Build the vacuum summary cards shown in the family overview.

    Args:
        rows: Prepared vacuum rows currently available to the dashboard.

    Returns:
        A tuple of hero statistic cards for the family.
    """
    return (
        StatCard("Vacuums", str(len(rows))),
        StatCard("Cordless", str(sum(1 for row in rows if row["power_source"] == "Cordless"))),
        StatCard("Corded", str(sum(1 for row in rows if row["power_source"] == "Corded"))),
        StatCard(
            "Hybrid",
            str(sum(1 for row in rows if row["power_source"] == "Corded/Cordless")),
        ),
    )
