from __future__ import annotations

from dewalt.tool_families.base import ColumnDef
from dewalt.ui.grid_helpers import boolean_column, categorical_column, number_column, text_column


def build_master_column_defs() -> list[ColumnDef]:
    """Build the master-grid column definitions for table saws.

    Args:
        None.

    Returns:
        A list of grouped AG Grid column definitions for table saws.
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
        categorical_column("stand_type", "Stand", minWidth=130),
        categorical_column("blade_diameter_display", "Blade", minWidth=120),
        number_column(
            "amp_rating",
            "Amps",
            "params.value == null ? '-' : `${params.value} A`",
            minWidth=110,
        ),
        number_column(
            "bevel_capacity_deg",
            "Bevel",
            "params.value == null ? '-' : `${params.value} degrees`",
            minWidth=120,
        ),
        number_column(
            "rip_capacity_right_in",
            "Rip Cap",
            "params.value == null ? '-' : `${params.value} in.`",
            minWidth=125,
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
            "weight_lbs",
            "Weight",
            "params.value == null ? '-' : `${params.value} lbs`",
            minWidth=120,
        ),
    ]

    feature_column_defs = [
        boolean_column("dust_extraction", "Dust Extraction", minWidth=155),
        boolean_column("rack_and_pinion_fence", "Rack & Pinion", minWidth=150),
        boolean_column("blade_brake", "Blade Brake", minWidth=130),
        boolean_column("onboard_storage", "Onboard Storage", minWidth=150),
        boolean_column("power_loss_reset", "Power-Loss Reset", minWidth=150),
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
