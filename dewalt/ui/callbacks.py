from __future__ import annotations

from typing import Any, Sequence
from urllib.parse import parse_qs, urlencode

from dash import Dash, Input, Output, State, callback_context, html, no_update
from dash.exceptions import PreventUpdate

from .config import APP_LOCATION_ID
from .context import DashboardContext
from .formatting import MISSING_DATA_LABEL, is_missing_display_value, normalize_compare_value
from .grids import LONG_FORM_COMPARE_FIELDS, build_compare_base_columns, build_compare_columns, build_compare_rows
from .modal import build_modal_content, build_modal_header


COMPARE_DIFFERENCES_OPTION = "differences"
IDENTITY_COMPARE_FIELDS = frozenset({"sku", "title"})
MOBILE_CORE_SPEC_LIMIT = 8


def _resolve_selected_rows(
    selected_rows: list[dict[str, Any]] | dict[str, Any] | None,
    context: DashboardContext,
) -> list[dict[str, Any]]:
    """Resolve selected rows into full display-row dictionaries."""
    if not selected_rows:
        return []
    if isinstance(selected_rows, dict):
        row_ids = [str(row_id) for row_id in selected_rows.get("ids", [])]
        return [context.row_lookup[row_id] for row_id in row_ids if row_id in context.row_lookup]

    resolved_rows = []
    for row in selected_rows:
        sku = row.get("sku")
        if sku and sku in context.row_lookup:
            resolved_rows.append(context.row_lookup[sku])
            continue
        resolved_rows.append(row)
    return resolved_rows


def _selected_sku_ids(selected_rows: list[dict[str, Any]] | dict[str, Any] | None) -> list[str]:
    """Extract selected SKU ids from a grid selection payload."""
    if not selected_rows:
        return []
    if isinstance(selected_rows, dict):
        return [str(row_id) for row_id in selected_rows.get("ids", []) if row_id]
    return [str(row["sku"]) for row in selected_rows if row.get("sku")]


def _differences_only_enabled(compare_options: list[str] | None) -> bool:
    """Return whether the compare view should hide matching rows."""
    return COMPARE_DIFFERENCES_OPTION in (compare_options or [])


def _format_mobile_compare_value(compare_row: dict[str, Any], value: Any) -> str:
    """Render one comparison value for the stacked mobile cards."""
    if compare_row["value_type"] == "boolean":
        if value is True:
            return "Yes"
        if value is False:
            return "No"
        return MISSING_DATA_LABEL
    return str(normalize_compare_value(value))


def _build_mobile_compare_field(
    label: str,
    value: str,
) -> html.Div:
    """Render one labeled spec row inside a mobile comparison card."""
    value_class_name = "mobile-compare-value"
    if value == MISSING_DATA_LABEL:
        value_class_name += " mobile-compare-value-missing"
    return html.Div(
        [
            html.Span(label, className="mobile-compare-label"),
            html.Span(value, className=value_class_name),
        ],
        className="mobile-compare-row",
    )


def _build_mobile_detail_section(label: str, value: str) -> html.Details | None:
    """Render a collapsible long-form comparison section on mobile."""
    if is_missing_display_value(value):
        return None

    lines = [line.strip() for line in value.splitlines() if line.strip()]
    if len(lines) <= 1:
        body = html.P(value, className="mobile-compare-detail-copy")
    else:
        body = html.Ul([html.Li(line) for line in lines], className="mobile-compare-detail-list")

    return html.Details(
        [
            html.Summary(label, className="mobile-compare-summary"),
            body,
        ],
        className="mobile-compare-disclosure",
    )


def _build_mobile_compare_cards(
    selected_rows: list[dict[str, Any]],
    compare_rows: list[dict[str, Any]],
    context: DashboardContext,
) -> list[Any]:
    """Build simplified stacked comparison cards for narrow screens."""
    if not selected_rows:
        return [
            html.Div(
                context.family.no_selection_note,
                className="placeholder-card mobile-compare-placeholder",
            )
        ]

    cards = []
    for index, row in enumerate(selected_rows, start=1):
        core_rows = []
        extra_rows = []
        disclosures = []

        for compare_row in compare_rows:
            field_name = str(compare_row["field_name"])
            if field_name in IDENTITY_COMPARE_FIELDS:
                continue

            display_value = _format_mobile_compare_value(compare_row, compare_row.get(f"model_{index}"))
            if field_name in LONG_FORM_COMPARE_FIELDS:
                disclosure = _build_mobile_detail_section(compare_row["field_label"], display_value)
                if disclosure:
                    disclosures.append(disclosure)
                continue

            if display_value == MISSING_DATA_LABEL and compare_row["row_state"] != "differs":
                continue

            spec_row = _build_mobile_compare_field(compare_row["field_label"], display_value)
            if len(core_rows) < MOBILE_CORE_SPEC_LIMIT:
                core_rows.append(spec_row)
            else:
                extra_rows.append(spec_row)

        card_children: list[Any] = [
            html.Div(
                [
                    html.Span(row["sku"], className="mobile-compare-sku"),
                    html.H3(row.get("title") or row["sku"], className="mobile-compare-title"),
                ],
                className="mobile-compare-card-head",
            )
        ]

        if core_rows:
            card_children.append(html.Div(core_rows, className="mobile-compare-table"))

        if extra_rows:
            card_children.append(
                html.Details(
                    [
                        html.Summary("More specs", className="mobile-compare-summary"),
                        html.Div(extra_rows, className="mobile-compare-table mobile-compare-table-extra"),
                    ],
                    className="mobile-compare-disclosure",
                )
            )

        card_children.extend(disclosures)
        cards.append(html.Article(card_children, className="mobile-compare-card"))
    return cards


def _parse_location_state(search: str | None) -> dict[str, Any]:
    """Parse app-specific state from the browser query string."""
    params = parse_qs((search or "").lstrip("?"), keep_blank_values=True)
    state: dict[str, Any] = {}

    family = params.get("family", [None])[0]
    if family:
        state["family"] = family

    if "compare" in params:
        state["compare"] = [sku for sku in params.get("compare", [""])[0].split(",") if sku]

    if "diff" in params:
        state["diff"] = params.get("diff", ["0"])[0] == "1"

    return state


def _build_location_search(
    active_family: str,
    selected_rows: list[dict[str, Any]] | dict[str, Any] | None,
    differences_only: bool,
) -> str:
    """Serialize the active shortlist state into a shareable query string."""
    params = {"family": active_family}
    selected_ids = _selected_sku_ids(selected_rows)
    if selected_ids:
        params["compare"] = ",".join(selected_ids)
    if differences_only:
        params["diff"] = "1"
    return f"?{urlencode(params)}"


def register_callbacks(app: Dash, context: DashboardContext) -> None:
    """Register all dashboard callbacks on the Dash application."""
    ids = context.family.ids

    @app.callback(
        Output(ids.selection_summary, "children"),
        Input(ids.grid, "virtualRowData"),
        Input(ids.grid, "selectedRows"),
    )
    def update_selection_summary(
        visible_rows: list[dict[str, Any]] | None,
        selected_rows: list[dict[str, Any]] | dict[str, Any] | None,
    ) -> list[html.Span]:
        """Update the selection summary pills above the master grid."""
        visible_count = len(visible_rows) if visible_rows is not None else len(context.display_rows)
        selected_count = len(_resolve_selected_rows(selected_rows, context))
        return [
            html.Span(f"{visible_count} visible", className="summary-pill"),
            html.Span(f"{selected_count} selected", className="summary-pill"),
            html.Span(
                f"{context.max_compare} max compare",
                className="summary-pill summary-pill-accent",
            ),
        ]

    @app.callback(
        Output(ids.compare_note, "children"),
        Output(ids.compare_grid, "rowData"),
        Output(ids.compare_grid, "columnDefs"),
        Output(ids.compare_cards, "children"),
        Input(ids.grid, "selectedRows"),
        Input(ids.compare_options, "value"),
    )
    def update_compare_grid(
        selected_rows: list[dict[str, Any]] | dict[str, Any] | None,
        compare_options: list[str] | None,
    ) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]], list[Any]]:
        """Update the comparison views based on the current master-grid selection."""
        rows = _resolve_selected_rows(selected_rows, context)
        if not rows:
            return (
                context.family.no_selection_note,
                [],
                build_compare_base_columns(),
                _build_mobile_compare_cards([], [], context),
            )

        compare_rows = rows[: context.max_compare]
        all_compare_rows = build_compare_rows(compare_rows, context.family)
        differences_only = _differences_only_enabled(compare_options) and len(compare_rows) > 1
        visible_compare_rows = build_compare_rows(
            compare_rows,
            context.family,
            differences_only=differences_only,
        )

        note = f"Comparing {len(compare_rows)} model(s)."
        if differences_only:
            hidden_rows = len(all_compare_rows) - len(visible_compare_rows)
            note += f" Showing {len(visible_compare_rows)} differing row(s)."
            if hidden_rows:
                note += f" Hiding {hidden_rows} matching or unlisted row(s)."
        elif _differences_only_enabled(compare_options):
            note += " Differences only activates once you select 2+ models."
        else:
            note += f" {len(all_compare_rows)} spec row(s)."

        if len(rows) > context.max_compare:
            note += f" Showing the first {context.max_compare} selected rows."

        return (
            note,
            visible_compare_rows,
            build_compare_columns(compare_rows),
            _build_mobile_compare_cards(compare_rows, visible_compare_rows, context),
        )

    @app.callback(
        Output(ids.modal, "is_open"),
        Output(ids.modal_header, "children"),
        Output(ids.modal_content, "children"),
        Input(ids.grid, "cellClicked"),
        Input(ids.modal_close, "n_clicks"),
        State(ids.modal, "is_open"),
        State(ids.grid, "virtualRowData"),
        prevent_initial_call=True,
    )
    def open_family_modal(
        cell_clicked_data: dict[str, Any] | None,
        close_clicks: int | None,
        is_open: bool,
        virtual_row_data: list[dict[str, Any]] | None,
    ) -> tuple[bool, Any, Any]:
        """Open or close the family detail modal from grid interactions."""
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if trigger_id == ids.modal_close:
            return False, no_update, no_update

        if trigger_id != ids.grid or not cell_clicked_data:
            raise PreventUpdate

        if cell_clicked_data.get("colId") not in context.grid_row_fields:
            raise PreventUpdate

        selected_row = cell_clicked_data.get("data")
        row_index = cell_clicked_data.get("rowIndex")
        if (
            selected_row is None
            and isinstance(row_index, int)
            and virtual_row_data
            and 0 <= row_index < len(virtual_row_data)
        ):
            selected_row = virtual_row_data[row_index]

        if not selected_row:
            raise PreventUpdate

        return (
            True,
            build_modal_header(selected_row),
            build_modal_content(selected_row, context.family),
        )

    @app.callback(
        Output(ids.compare_share_link, "href"),
        Output(ids.compare_share_link, "children"),
        Input("tool-tabs", "value"),
        Input(ids.grid, "selectedRows"),
        Input(ids.compare_options, "value"),
    )
    def update_compare_share_link(
        active_family: str | None,
        selected_rows: list[dict[str, Any]] | dict[str, Any] | None,
        compare_options: list[str] | None,
    ) -> tuple[str, str]:
        """Update the family-specific share link."""
        if active_family != context.family.slug:
            return (f"?family={context.family.slug}", "Share this shortlist")

        selected_count = len(_selected_sku_ids(selected_rows))
        label = "Share this shortlist" if selected_count else "Share this family view"
        return (
            _build_location_search(
                context.family.slug,
                selected_rows,
                _differences_only_enabled(compare_options),
            ),
            label,
        )


def register_app_state_callbacks(app: Dash, dashboards: Sequence[DashboardContext]) -> None:
    """Register app-level callbacks for URL hydration and shareable shortlist state."""
    dashboard_list = list(dashboards)
    dashboard_by_slug = {dashboard.family.slug: dashboard for dashboard in dashboard_list}
    selection_outputs = [Output(dashboard.family.ids.grid, "selectedRows") for dashboard in dashboard_list]
    compare_option_outputs = [
        Output(dashboard.family.ids.compare_options, "value") for dashboard in dashboard_list
    ]

    @app.callback(
        Output("tool-tabs", "value"),
        *selection_outputs,
        *compare_option_outputs,
        Input(APP_LOCATION_ID, "search"),
    )
    def hydrate_state_from_location(search: str | None) -> tuple[Any, ...]:
        """Apply active-family state from the URL when the page loads or the URL changes."""
        parsed_state = _parse_location_state(search)
        if not parsed_state:
            return (
                no_update,
                *(no_update for _ in selection_outputs),
                *(no_update for _ in compare_option_outputs),
            )

        active_family = parsed_state.get("family")
        if active_family not in dashboard_by_slug:
            return (
                no_update,
                *(no_update for _ in selection_outputs),
                *(no_update for _ in compare_option_outputs),
            )

        selected_rows_outputs = []
        selected_ids = parsed_state.get("compare")
        for dashboard in dashboard_list:
            if dashboard.family.slug != active_family or selected_ids is None:
                selected_rows_outputs.append(no_update)
                continue
            valid_ids = [row_id for row_id in selected_ids if row_id in dashboard.row_lookup]
            selected_rows_outputs.append({"ids": valid_ids} if valid_ids else [])

        compare_options_outputs = []
        diff_enabled = parsed_state.get("diff")
        for dashboard in dashboard_list:
            if dashboard.family.slug != active_family or diff_enabled is None:
                compare_options_outputs.append(no_update)
                continue
            compare_options_outputs.append(
                [COMPARE_DIFFERENCES_OPTION] if diff_enabled else []
            )

        return (
            active_family,
            *selected_rows_outputs,
            *compare_options_outputs,
        )
