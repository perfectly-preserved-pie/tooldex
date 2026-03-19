from __future__ import annotations


MISSING_DATA_LABEL = "Not listed"


def is_missing_display_value(value: object) -> bool:
    """Return whether a rendered comparison value should be treated as missing."""
    return value in (None, "", [], "-", MISSING_DATA_LABEL)


def normalize_compare_value(value: object) -> object:
    """Normalize placeholder values used in compare/detail views."""
    if is_missing_display_value(value):
        return MISSING_DATA_LABEL
    return value


def format_bool(value: bool | None) -> str:
    """Convert a boolean value to the dashboard's text representation.

    Args:
        value: Raw boolean value or ``None``.

    Returns:
        ``"Yes"``, ``"No"``, or ``"-"`` when no value is available.
    """
    if value is None:
        return "-"
    return "Yes" if value else "No"


def format_numeric(value: float | int | None, suffix: str = "") -> str:
    """Format a numeric value for display.

    Args:
        value: Numeric value or ``None``.
        suffix: Optional suffix appended directly to the formatted value.

    Returns:
        A string representation of the value, or ``"-"`` when no value is available.
    """
    if value is None:
        return "-"
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return f"{value}{suffix}"


def format_wheel_size(min_value: float | None, max_value: float | None) -> str:
    """Format a grinder wheel size or wheel size range.

    Args:
        min_value: Minimum supported wheel size in inches.
        max_value: Maximum supported wheel size in inches.

    Returns:
        A formatted wheel size string, or ``"-"`` when no wheel size exists.
    """
    if min_value is None:
        return "-"
    if max_value is None or min_value == max_value:
        return f"{format_numeric(min_value)} in."
    return f"{format_numeric(min_value)} - {format_numeric(max_value)} in."


def format_lines(values: list[str] | None) -> str:
    """Join a list of strings into a newline-delimited block.

    Args:
        values: Ordered list of strings, or ``None``.

    Returns:
        A newline-delimited string, or ``"-"`` when no values are present.
    """
    if not values:
        return "-"
    return "\n".join(values)
