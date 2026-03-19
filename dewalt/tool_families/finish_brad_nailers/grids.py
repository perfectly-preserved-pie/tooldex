from __future__ import annotations

from dewalt.tool_families.base import ColumnDef
from dewalt.ui.grid_helpers import boolean_column, categorical_column, number_column, text_column


def build_master_column_defs() -> list[ColumnDef]:
    """Build the master-grid column definitions for finish/brad nailers.

    Args:
        None.

    Returns:
        A list of grouped AG Grid column definitions for finish/brad nailers.
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
            flex=2.7,
            minWidth=350,
            tooltipField="title",
            wrapText=True,
            autoHeight=True,
        ),
    ]

    spec_column_defs = [
        categorical_column("power_source", "Power", minWidth=120),
        categorical_column("series_display", "Series", minWidth=160),
        categorical_column("voltage_system", "Voltage", minWidth=130),
        categorical_column("nailer_type", "Type", minWidth=140),
        number_column(
            "gauge",
            "Gauge",
            "params.value == null ? '-' : `${params.value} ga`",
            minWidth=110,
        ),
        number_column(
            "magazine_angle_deg",
            "Mag Angle",
            "params.value == null ? '-' : `${params.value} degrees`",
            minWidth=130,
        ),
        categorical_column("magazine_loading", "Mag Load", minWidth=130),
        number_column(
            "magazine_capacity",
            "Mag Cap",
            "params.value == null ? '-' : params.value.toLocaleString()",
            minWidth=120,
        ),
        number_column(
            "fastener_max_length_in",
            "Fastener Max",
            "params.value == null ? '-' : `${params.value} in.`",
            minWidth=140,
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
        boolean_column("jam_clearing", "Jam Clearing", minWidth=135),
        boolean_column("tool_free_depth_adjust", "Tool-Free Depth", minWidth=150),
        boolean_column("low_nail_lockout", "Low Nail Lockout", minWidth=150),
        boolean_column("selectable_trigger", "Selectable Trigger", minWidth=150),
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
