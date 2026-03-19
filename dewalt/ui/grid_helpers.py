from __future__ import annotations

from typing import Any

from dewalt.tool_families.base import ColumnDef

from .config import BOOLEAN_FILTER, MULTI_FILTER, NUMBER_FILTER, SET_FILTER, TEXT_FILTER


def text_column(field: str, header_name: str, **kwargs: Any) -> ColumnDef:
    """Build a text-filtered AG Grid column definition.

    Args:
        field: Data field name for the column.
        header_name: Visible header label.
        **kwargs: Additional AG Grid column properties to merge in.

    Returns:
        An AG Grid column definition configured with a text filter.
    """
    column = {"field": field, "headerName": header_name, "filter": TEXT_FILTER}
    column.update(kwargs)
    return column


def categorical_column(field: str, header_name: str, **kwargs: Any) -> ColumnDef:
    """Build a set-filtered AG Grid column definition.

    Args:
        field: Data field name for the column.
        header_name: Visible header label.
        **kwargs: Additional AG Grid column properties to merge in.

    Returns:
        An AG Grid column definition configured with a set filter.
    """
    column = {"field": field, "headerName": header_name, "filter": SET_FILTER}
    column.update(kwargs)
    return column


def number_column(
    field: str,
    header_name: str,
    formatter: str | None = None,
    **kwargs: Any,
) -> ColumnDef:
    """Build a numeric AG Grid column with both value-list and range filters.

    Args:
        field: Data field name for the column.
        header_name: Visible header label.
        formatter: Optional JavaScript formatter function string.
        **kwargs: Additional AG Grid column properties to merge in.

    Returns:
        An AG Grid column definition configured for numeric values.
    """
    column = {
        "field": field,
        "headerName": header_name,
        "filter": MULTI_FILTER,
        "type": "numericColumn",
        "filterParams": {
            "filters": [
                {
                    "filter": SET_FILTER,
                    "title": "Values",
                },
                {
                    "filter": NUMBER_FILTER,
                    "title": "Range",
                },
            ]
        },
    }
    if formatter:
        formatter_config = {"function": formatter}
        column["valueFormatter"] = formatter_config
        column["filterParams"]["filters"][0]["filterParams"] = {
            "valueFormatter": formatter_config
        }
    column.update(kwargs)
    return column


def boolean_column(field: str, header_name: str, **kwargs: Any) -> ColumnDef:
    """Build a boolean AG Grid column definition.

    Args:
        field: Data field name for the column.
        header_name: Visible header label.
        **kwargs: Additional AG Grid column properties to merge in.

    Returns:
        An AG Grid column definition configured for boolean data.
    """
    column = {
        "field": field,
        "headerName": header_name,
        "filter": BOOLEAN_FILTER,
        "cellDataType": "boolean",
        "valueFormatter": {
            "function": (
                "params.value === true ? 'Yes' : "
                "params.value === false ? 'No' : '-'"
            )
        },
        "filterParams": {
            "valueFormatter": {
                "function": (
                    "params.value === true ? 'Yes' : "
                    "params.value === false ? 'No' : '-'"
                )
            }
        },
    }
    column.update(kwargs)
    return column
