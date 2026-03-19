from __future__ import annotations

from dewalt.tool_families.base import ColumnDef
from dewalt.ui.grid_helpers import boolean_column, categorical_column, number_column, text_column


def build_master_column_defs() -> list[ColumnDef]:
    """Build the master-grid column definitions for miter saws.

    Args:
        None.

    Returns:
        A list of grouped AG Grid column definitions for miter saws.
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
            flex=2.9,
            minWidth=380,
            tooltipField="title",
            wrapText=True,
            autoHeight=True,
        ),
    ]

    spec_column_defs = [
        categorical_column("power_source", "Power", minWidth=120),
        categorical_column("series_display", "Series", minWidth=170),
        categorical_column("voltage_system", "Voltage", minWidth=130),
        categorical_column("saw_motion", "Motion", minWidth=130),
        categorical_column("bevel_type", "Bevel", minWidth=140),
        categorical_column("blade_diameter_display", "Blade", minWidth=125),
        number_column(
            "amp_rating",
            "Amps",
            "params.value == null ? '-' : `${params.value} A`",
            minWidth=110,
        ),
        number_column(
            "rpm_max",
            "Max RPM",
            "params.value == null ? '-' : params.value.toLocaleString()",
            minWidth=125,
        ),
        number_column(
            "cross_cut_capacity_in",
            "Cross-Cut",
            "params.value == null ? '-' : `${params.value} in.`",
            minWidth=130,
        ),
        number_column(
            "baseboard_capacity_in",
            "Baseboard",
            "params.value == null ? '-' : `${params.value} in.`",
            minWidth=130,
        ),
        number_column(
            "crown_capacity_in",
            "Crown",
            "params.value == null ? '-' : `${params.value} in.`",
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
        boolean_column("brushless", "Brushless", minWidth=120),
        boolean_column("dust_extraction", "Dust Extraction", minWidth=155),
        boolean_column("led_light", "LED Light", minWidth=120),
        boolean_column("cutline_system", "Cutline", minWidth=120),
        boolean_column(
            "wireless_tool_control",
            "Wireless Tool Control",
            minWidth=185,
        ),
        boolean_column(
            "regenerative_braking",
            "Regenerative Braking",
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
