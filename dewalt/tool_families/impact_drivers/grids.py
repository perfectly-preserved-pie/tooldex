from __future__ import annotations

from dewalt.tool_families.base import ColumnDef
from dewalt.ui.grid_helpers import boolean_column, categorical_column, number_column, text_column


def build_master_column_defs() -> list[ColumnDef]:
    """Build the master-grid column definitions for impact drivers."""
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
        categorical_column("power_source", "Power", minWidth=120),
        categorical_column("series_display", "Series", minWidth=180),
        categorical_column("voltage_system", "Voltage", minWidth=130),
        categorical_column("chuck_size_display", "Drive", minWidth=120),
        number_column(
            "speed_count",
            "Speeds",
            "params.value == null ? '-' : params.value",
            minWidth=110,
        ),
        number_column(
            "rpm_max",
            "Max RPM",
            "params.value == null ? '-' : params.value.toLocaleString()",
            minWidth=125,
        ),
        number_column(
            "impact_rate_bpm",
            "IPM",
            "params.value == null ? '-' : params.value.toLocaleString()",
            minWidth=120,
        ),
        number_column(
            "max_torque_in_lbs",
            "Torque",
            "params.value == null ? '-' : `${params.value.toLocaleString()} in-lbs`",
            minWidth=140,
        ),
        number_column(
            "power_watts",
            "Power",
            "params.value == null ? '-' : `${params.value.toLocaleString()} W`",
            minWidth=120,
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
        boolean_column("led_light", "LED Light", minWidth=120),
        boolean_column("hydraulic", "Hydraulic", minWidth=120),
        boolean_column("high_torque", "High Torque", minWidth=135),
        boolean_column("tool_connect_ready", "Tool Connect", minWidth=140),
        boolean_column("lanyard_ready", "Lanyard Ready", minWidth=145),
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
