from __future__ import annotations

from dewalt.tool_families.base import ColumnDef
from dewalt.ui.grid_helpers import boolean_column, categorical_column, number_column, text_column


def build_master_column_defs() -> list[ColumnDef]:
    """Build the master-grid column definitions for circular saws.

    Args:
        None.

    Returns:
        A list of grouped AG Grid column definitions for circular saws.
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
            flex=2.8,
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
        categorical_column("saw_type", "Type", minWidth=145),
        categorical_column("blade_diameter_display", "Blade", minWidth=125),
        categorical_column("arbor_size_display", "Arbor", minWidth=120),
        number_column(
            "bevel_capacity_deg",
            "Bevel",
            "params.value == null ? '-' : `${params.value} degrees`",
            minWidth=120,
        ),
        number_column(
            "depth_cut_90_in",
            "Depth 90",
            "params.value == null ? '-' : `${params.value} in.`",
            minWidth=120,
        ),
        number_column(
            "depth_cut_45_in",
            "Depth 45",
            "params.value == null ? '-' : `${params.value} in.`",
            minWidth=120,
        ),
        number_column(
            "rpm_max",
            "Max RPM",
            "params.value == null ? '-' : params.value.toLocaleString()",
            minWidth=125,
        ),
        number_column(
            "max_watts_out",
            "MWO",
            "params.value == null ? '-' : `${params.value.toLocaleString()} W`",
            minWidth=125,
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
        boolean_column("electric_brake", "Electric Brake", minWidth=145),
        boolean_column("dust_extraction", "Dust Extraction", minWidth=155),
        boolean_column("rafter_hook", "Rafter Hook", minWidth=135),
        boolean_column("tool_connect_ready", "Tool Connect", minWidth=145),
        boolean_column("power_detect", "POWER DETECT", minWidth=150),
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
