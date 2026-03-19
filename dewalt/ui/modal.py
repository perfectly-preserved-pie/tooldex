from __future__ import annotations

from typing import Any

import dash_bootstrap_components as dbc
from dash import html

from dewalt.tool_families.base import RowData, ToolFamilyDefinition, ToolFamilyIds


def resolve_detail_value(
    row: RowData,
    field_name: str,
    family: ToolFamilyDefinition,
) -> str:
    """Resolve a modal detail value for a named family field.

    Args:
        row: Family row used to populate the modal.
        field_name: Internal field name to resolve.
        family: Tool family definition that owns formatting behavior.

    Returns:
        A formatted detail value string for the modal table.
    """
    return family.compare_display_value(row, field_name)


def build_detail_table(row: RowData, family: ToolFamilyDefinition) -> dbc.Table:
    """Build the modal's specification table for one selected model.

    Args:
        row: Family row used to populate the modal.
        family: Tool family definition that owns detail-field metadata.

    Returns:
        A Bootstrap table component containing labeled specification rows.
    """
    body_rows = []
    for label, field_name in family.detail_fields:
        value = resolve_detail_value(row, field_name, family)
        if value in (None, "", "-", []):
            continue
        body_rows.append(
            html.Tr(
                [
                    html.Th(label, className="modal-spec-label"),
                    html.Td(value, className="modal-spec-value"),
                ]
            )
        )

    return dbc.Table(body_rows, borderless=True, hover=False, className="modal-spec-table")


def build_detail_block(title: str, values: list[str] | None) -> html.Div | None:
    """Build a titled modal section for a list of bullet values.

    Args:
        title: Section heading shown above the bullet list.
        values: Optional list of string values to render.

    Returns:
        A section ``Div`` when values exist, otherwise ``None``.
    """
    if not values:
        return None
    return html.Div(
        [
            html.H4(title, className="modal-section-title"),
            html.Ul([html.Li(value) for value in values], className="modal-list"),
        ],
        className="modal-section",
    )


def build_modal_content(row: RowData, family: ToolFamilyDefinition) -> list[Any]:
    """Build the full modal body content for one selected model.

    Args:
        row: Family row used to populate the modal.
        family: Tool family definition that owns detail formatting.

    Returns:
        An ordered list of Dash components for the modal body.
    """
    content = [
        build_detail_table(row, family),
        html.P(
            "This view intentionally focuses on structured specs and omits copied product copy.",
            className="modal-note",
        ),
    ]

    return content


def build_modal_header(row: RowData) -> html.Div:
    """Build the modal header for one selected model.

    Args:
        row: Family row used to populate the modal header.

    Returns:
        A ``Div`` containing the SKU and model title.
    """
    return html.Div(
        [
            html.Div(row.get("sku", "Unknown SKU"), className="modal-sku"),
            html.H3(row.get("title", "Grinder Details"), className="modal-title"),
        ]
    )


def build_modal(ids: ToolFamilyIds) -> dbc.Modal:
    """Create the reusable detail modal component for a tool family.

    Args:
        ids: Tool-family-specific component ids.

    Returns:
        A configured Bootstrap modal component.
    """
    return dbc.Modal(
        [
            dbc.ModalHeader(id=ids.modal_header),
            dbc.ModalBody(id=ids.modal_content),
            dbc.ModalFooter(
                dbc.Button("Close", id=ids.modal_close, color="secondary", n_clicks=0)
            ),
        ],
        id=ids.modal,
        is_open=False,
        size="xl",
        scrollable=True,
    )
