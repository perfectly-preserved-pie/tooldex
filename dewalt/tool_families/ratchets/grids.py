from __future__ import annotations

from dewalt.tool_families.base import ColumnDef
from dewalt.ui.grid_helpers import boolean_column, categorical_column, number_column, text_column


def build_master_column_defs() -> list[ColumnDef]:
    """Build the master-grid column definitions for ratchets.

    Args:
        None.

    Returns:
        A list of grouped AG Grid column definitions for ratchets.
    """
    identity_column_defs = [
        text_column(
            "sku",
            "SKU",
            pinned="left",
            minWidth=130,
        ),
        text_column(
            "title",
            "Model",
            flex=2.6,
            minWidth=360,
            tooltipField="title",
            wrapText=True,
            autoHeight=True,
        ),
    ]

    spec_column_defs = [
        categorical_column("power_source", "Power", minWidth=120),
        categorical_column("series_display", "Series", minWidth=170),
        categorical_column("voltage_system", "Voltage", minWidth=130),
        categorical_column("drive_size_display", "Drive", minWidth=160),
        categorical_column("head_type", "Head", minWidth=145),
        number_column(
            "rpm_max",
            "Max RPM",
            "params.value == null ? '-' : params.value.toLocaleString()",
            minWidth=125,
        ),
        number_column(
            "max_torque_ft_lbs",
            "Torque",
            "params.value == null ? '-' : `${params.value.toLocaleString()} ft-lbs`",
            minWidth=135,
        ),
        number_column(
            "tool_length_in",
            "Tool L",
            "params.value == null ? '-' : `${params.value} in.`",
            minWidth=120,
        ),
        number_column(
            "weight_lbs",
            "Weight",
            "params.value == null ? '-' : `${params.value} lbs`",
            minWidth=120,
        ),
    ]

    feature_column_defs = [
        boolean_column("brushless", "Brushless", minWidth=120),
        boolean_column("variable_speed", "Variable Speed", minWidth=145),
        boolean_column("led_light", "LED Light", minWidth=120),
        boolean_column("fw_rev_switch", "FW / REV", minWidth=125),
        boolean_column("extended_reach", "Extended Reach", minWidth=150),
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
