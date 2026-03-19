from __future__ import annotations

from dewalt.tool_families.base import ColumnDef
from dewalt.ui.grid_helpers import boolean_column, categorical_column, number_column, text_column


def build_master_column_defs() -> list[ColumnDef]:
    """Build the master-grid column definitions for vacuums.

    Args:
        None.

    Returns:
        A list of grouped AG Grid column definitions for vacuums.
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
            flex=2.6,
            minWidth=340,
            tooltipField="title",
            wrapText=True,
            autoHeight=True,
        ),
    ]

    spec_column_defs = [
        categorical_column("power_source", "Power", minWidth=135),
        categorical_column("series_display", "Series", minWidth=170),
        categorical_column("voltage_system", "Voltage", minWidth=140),
        categorical_column("vacuum_type", "Type", minWidth=165),
        categorical_column("tank_capacity_display", "Tank", minWidth=135),
        number_column(
            "peak_hp",
            "Peak HP",
            "params.value == null ? '-' : `${params.value} HP`",
            minWidth=120,
        ),
        number_column(
            "airflow_cfm",
            "Airflow",
            "params.value == null ? '-' : `${params.value.toLocaleString()} CFM`",
            minWidth=130,
        ),
        categorical_column("hose_diameter_display", "Hose Dia", minWidth=135),
        number_column(
            "hose_length_ft",
            "Hose L",
            "params.value == null ? '-' : `${params.value} ft`",
            minWidth=120,
        ),
        number_column(
            "cord_length_ft",
            "Cord L",
            "params.value == null ? '-' : `${params.value} ft`",
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
        boolean_column("hepa_filter", "HEPA", minWidth=115),
        boolean_column("wet_dry", "Wet/Dry", minWidth=120),
        boolean_column("quiet_operation", "Quiet", minWidth=120),
        boolean_column("wireless_tool_control", "Wireless Control", minWidth=155),
        boolean_column("blower_port", "Blower Port", minWidth=135),
        boolean_column(
            "automatic_filter_cleaning",
            "Auto Filter Cleaning",
            minWidth=175,
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
