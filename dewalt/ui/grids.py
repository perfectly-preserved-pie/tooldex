from __future__ import annotations

from typing import Any

import dash_ag_grid as dag

from dewalt.tool_families.base import ColumnDef, RowData, ToolFamilyDefinition, ToolFamilyIds

from .config import AG_GRID_THEME
from .formatting import is_missing_display_value, normalize_compare_value


LONG_FORM_COMPARE_FIELDS = frozenset(
    {
        "includes",
        "applications",
        "disclaimers",
    }
)
REMOVED_COPY_FIELDS = frozenset(
    {
        "description",
        "features",
        "additional_features",
        "includes",
        "applications",
        "disclaimers",
    }
)


def _is_missing_compare_cell(value: object, value_type: str) -> bool:
    """Return whether a compare-grid cell should be treated as missing."""
    if value_type == "boolean":
        return value is None
    return is_missing_display_value(value)


def _build_compare_row_state(compare_row: RowData, selected_count: int) -> str:
    """Classify a compare row as identical, different, or entirely missing."""
    values = [compare_row.get(f"model_{index}") for index in range(1, selected_count + 1)]
    value_type = str(compare_row["value_type"])
    if all(_is_missing_compare_cell(value, value_type) for value in values):
        return "all-missing"
    unique_values = {value for value in values}
    if len(unique_values) == 1:
        return "same"
    return "differs"


def build_compare_base_columns() -> list[ColumnDef]:
    """Build the fixed leading column for the comparison grid.

    Args:
        None.

    Returns:
        A list containing the pinned specification-label column definition.
    """
    return [
        {
            "field": "field_label",
            "headerName": "Specification",
            "pinned": "left",
            "minWidth": 230,
            "wrapText": True,
            "autoHeight": True,
        }
    ]


def build_master_grid(
    rows: list[RowData],
    column_defs: list[ColumnDef],
    ids: ToolFamilyIds,
) -> dag.AgGrid:
    """Create the master AG Grid for a tool family.

    Args:
        rows: Prepared row data for the master grid.
        column_defs: Prebuilt master column definitions.
        ids: Tool-family-specific component ids.

    Returns:
        A configured Dash AG Grid component for the master table.
    """
    return dag.AgGrid(
        id=ids.grid,
        rowData=rows,
        columnDefs=column_defs,
        getRowId="params.data.sku",
        persisted_props=["filterModel", "selectedRows", "columnState"],
        persistence=ids.grid,
        persistence_type="local",
        defaultColDef={
            "sortable": True,
            "resizable": True,
            "floatingFilter": True,
            "minWidth": 110,
        },
        style={"width": "100%", "height": "620px"},
        dashGridOptions={
            "animateRows": False,
            "pagination": True,
            "paginationPageSize": 12,
            "paginationPageSizeSelector": [12, 24, 48],
            "rowSelection": {
                "mode": "multiRow",
                "checkboxes": True,
                "headerCheckbox": True,
                "enableClickSelection": True,
            },
            "selectionColumnDef": {
                "pinned": "left",
                "minWidth": 56,
                "width": 56,
                "maxWidth": 56,
                "resizable": False,
                "sortable": False,
                "filter": False,
            },
            "theme": AG_GRID_THEME,
        },
        className="grid-shell",
        enableEnterpriseModules=True,
    )


def build_compare_grid(
    ids: ToolFamilyIds,
    column_defs: list[ColumnDef] | None = None,
) -> dag.AgGrid:
    """Create the transposed comparison AG Grid.

    Args:
        ids: Tool-family-specific component ids.
        column_defs: Optional prebuilt column definitions for the comparison grid.

    Returns:
        A configured Dash AG Grid component for model comparison rows.
    """
    return dag.AgGrid(
        id=ids.compare_grid,
        rowData=[],
        columnDefs=column_defs or build_compare_base_columns(),
        defaultColDef={
            "sortable": False,
            "resizable": True,
            "wrapText": True,
            "autoHeight": True,
            "minWidth": 180,
        },
        style={"width": "100%", "height": "620px"},
        dashGridOptions={
            "animateRows": False,
            "theme": AG_GRID_THEME,
        },
        rowClassRules={
            "compare-row-all-missing": "params.data.row_state === 'all-missing'",
        },
        className="grid-shell compare-grid",
    )


def build_compare_columns(
    selected_rows: list[RowData],
    base_columns: list[ColumnDef] | None = None,
) -> list[ColumnDef]:
    """Build dynamic comparison-grid columns for the selected models.

    Args:
        selected_rows: Family rows chosen for comparison.
        base_columns: Optional base comparison columns to reuse.

    Returns:
        A complete list of comparison-grid column definitions.
    """
    columns = [dict(column) for column in (base_columns or build_compare_base_columns())]
    for index, row in enumerate(selected_rows, start=1):
        columns.append(
            {
                "field": f"model_{index}",
                "headerName": row["sku"],
                "minWidth": 280,
                "tooltipField": f"model_{index}",
                "valueFormatter": {
                    "function": (
                        "params.data.value_type === 'boolean' "
                        "? (params.value === true ? 'Yes' : "
                        "params.value === false ? 'No' : 'Not listed') "
                        ": (params.value == null || params.value === '' ? 'Not listed' : params.value)"
                    )
                },
                "cellRendererSelector": {
                    "function": (
                        "params.data.value_type === 'boolean' && params.value != null "
                        "? {component: 'agCheckboxCellRenderer', params: {disabled: true}} : undefined"
                    )
                },
                "cellClassRules": {
                    "compare-cell-missing": {
                        "function": (
                            "params.data.value_type === 'boolean' "
                            "? params.value == null "
                            ": params.value === 'Not listed'"
                        )
                    }
                },
                "cellStyle": {
                    "function": (
                        "params.data.value_type === 'boolean' "
                        "? ({display: 'flex', alignItems: 'center', justifyContent: 'flex-start', paddingLeft: '12px'}) "
                        ": null"
                    )
                },
                "tooltipValueGetter": {
                    "function": (
                        "params.data.value_type === 'boolean' "
                        "? (params.value === true ? 'Yes' : params.value === false ? 'No' : 'Not listed') "
                        ": (params.value == null || params.value === '' ? 'Not listed' : params.value)"
                    )
                },
            }
        )
    return columns


def build_compare_rows(
    selected_rows: list[RowData],
    family: ToolFamilyDefinition,
    differences_only: bool = False,
) -> list[RowData]:
    """Transpose selected family rows into comparison-grid rows.

    Args:
        selected_rows: Family rows chosen for comparison.
        family: Tool family definition that owns compare-field metadata.

    Returns:
        A list of row dictionaries keyed by specification label and model columns.
    """
    rows = []
    selected_count = len(selected_rows)
    for field_name, label in family.compare_fields:
        if field_name in REMOVED_COPY_FIELDS:
            continue
        value_type = "boolean" if field_name in family.compare_boolean_fields else "text"
        compare_row: RowData = {
            "field_label": label,
            "field_name": field_name,
            "value_type": value_type,
            "is_long_form": field_name in LONG_FORM_COMPARE_FIELDS,
        }
        for index, product_row in enumerate(selected_rows, start=1):
            if value_type == "boolean":
                compare_row[f"model_{index}"] = product_row.get(field_name)
            else:
                compare_row[f"model_{index}"] = normalize_compare_value(
                    family.compare_display_value(product_row, field_name)
                )
        compare_row["row_state"] = _build_compare_row_state(compare_row, selected_count)
        if differences_only and compare_row["row_state"] != "differs":
            continue
        rows.append(compare_row)
    return rows
