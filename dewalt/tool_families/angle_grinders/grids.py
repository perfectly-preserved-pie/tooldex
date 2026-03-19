from __future__ import annotations

from dewalt.tool_families.base import ColumnDef
from dewalt.ui.grid_helpers import boolean_column, categorical_column, number_column, text_column


def build_master_column_defs() -> list[ColumnDef]:
    """Build the master-grid column definitions for angle grinders.

    Args:
        None.

    Returns:
        A list of grouped AG Grid column definitions for angle grinders.
    """
    identity_column_defs = [
        text_column(
            "sku",
            "SKU",
            pinned="left",
            minWidth=120,
        ),
        text_column(
            "title",
            "Model",
            flex=2.4,
            minWidth=340,
            tooltipField="title",
            wrapText=True,
            autoHeight=True,
        ),
    ]

    spec_column_defs = [
        categorical_column("power_source", "Power", minWidth=130),
        categorical_column("series_display", "Series", minWidth=170),
        categorical_column("voltage_system", "Voltage", minWidth=130),
        categorical_column("wheel_size_display", "Wheel Size", minWidth=140),
        categorical_column("switch_type", "Switch", minWidth=150),
        number_column(
            "rpm_max",
            "RPM",
            "params.value == null ? '-' : params.value.toLocaleString()",
            minWidth=110,
        ),
        number_column(
            "amp_rating",
            "Amp",
            "params.value == null ? '-' : `${params.value} A`",
            minWidth=110,
        ),
        number_column(
            "horsepower_hp",
            "HP",
            "params.value == null ? '-' : `${params.value} HP`",
            minWidth=110,
        ),
        number_column(
            "max_watts_out",
            "MWO",
            "params.value == null ? '-' : `${params.value.toLocaleString()} W`",
            minWidth=120,
        ),
        number_column(
            "power_input_watts",
            "Power Input",
            "params.value == null ? '-' : `${params.value.toLocaleString()} W`",
            minWidth=135,
        ),
    ]

    feature_column_defs = [
        boolean_column("brushless", "Brushless", minWidth=120),
        boolean_column("variable_speed", "Variable Speed", minWidth=145),
        boolean_column("anti_rotation_system", "Anti-Rotation", minWidth=140),
        boolean_column("e_clutch", "E-CLUTCH", minWidth=120),
        boolean_column("kickback_brake", "Kickback Brake", minWidth=145),
        boolean_column("tool_connect_ready", "Tool Connect", minWidth=135),
        boolean_column(
            "wireless_tool_control",
            "Wireless Tool Control",
            minWidth=185,
        ),
    ]

    return [
        *identity_column_defs,
        {
            "headerName": "Specs",
            "marryChildren": True,
            "children": spec_column_defs,
        },
        {
            "headerName": "Features",
            "marryChildren": True,
            "children": feature_column_defs,
        },
    ]
