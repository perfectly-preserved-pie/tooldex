from __future__ import annotations

from dash import Dash
import dash_bootstrap_components as dbc

from dewalt.tool_families import (
    ANGLE_GRINDER_FAMILY,
    CIRCULAR_SAW_FAMILY,
    CUT_OUT_TOOL_FAMILY,
    DRILL_DRIVER_FAMILY,
    FINISH_BRAD_NAILER_FAMILY,
    HAMMER_DRILL_FAMILY,
    IMPACT_DRIVER_FAMILY,
    IMPACT_WRENCH_FAMILY,
    MITER_SAW_FAMILY,
    OSCILLATING_MULTI_TOOL_FAMILY,
    RATCHET_FAMILY,
    ROTARY_HAMMER_FAMILY,
    TABLE_SAW_FAMILY,
    VACUUM_FAMILY,
)
from dewalt.ui import (
    DashboardSection,
    build_compare_base_columns,
    build_compare_grid,
    build_layout,
    build_master_grid,
    build_modal,
    load_dashboard_context,
    register_app_state_callbacks,
    register_callbacks,
)


FAMILIES = (
    ANGLE_GRINDER_FAMILY,
    DRILL_DRIVER_FAMILY,
    IMPACT_DRIVER_FAMILY,
    IMPACT_WRENCH_FAMILY,
    RATCHET_FAMILY,
    HAMMER_DRILL_FAMILY,
    ROTARY_HAMMER_FAMILY,
    CIRCULAR_SAW_FAMILY,
    MITER_SAW_FAMILY,
    TABLE_SAW_FAMILY,
    OSCILLATING_MULTI_TOOL_FAMILY,
    CUT_OUT_TOOL_FAMILY,
    FINISH_BRAD_NAILER_FAMILY,
    VACUUM_FAMILY,
)
COMPARE_BASE_COLUMNS = build_compare_base_columns()
DASHBOARDS = [load_dashboard_context(family) for family in FAMILIES]
SECTIONS = [
    DashboardSection(
        context=dashboard,
        master_grid=build_master_grid(
            dashboard.display_rows,
            dashboard.family.build_master_column_defs(),
            dashboard.family.ids,
        ),
        compare_grid=build_compare_grid(dashboard.family.ids, COMPARE_BASE_COLUMNS),
        modal=build_modal(dashboard.family.ids),
    )
    for dashboard in DASHBOARDS
]

app = Dash(
    __name__,
    title="DEWALT Compare",
    description="An interactive website for browsing and comparing DEWALT tools across multiple categories.",
    external_stylesheets=[dbc.themes.BOOTSTRAP],
)
server = app.server

app.layout = build_layout(SECTIONS)

for dashboard in DASHBOARDS:
    register_callbacks(app, dashboard)

register_app_state_callbacks(app, DASHBOARDS)


if __name__ == "__main__":
    app.run(debug=True)
