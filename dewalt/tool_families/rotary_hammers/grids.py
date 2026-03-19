from __future__ import annotations

from dewalt.tool_families.base import ColumnDef
from dewalt.ui.grid_helpers import boolean_column, categorical_column, number_column, text_column


def build_master_column_defs() -> list[ColumnDef]:
    """Build the master-grid column definitions for rotary hammers.

    Args:
        None.

    Returns:
        A list of grouped AG Grid column definitions for rotary hammers.
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
        categorical_column("hammer_type", "Type", minWidth=135),
        categorical_column("chuck_size_display", "Chuck Size", minWidth=130),
        categorical_column("chuck_type", "Chuck Type", minWidth=130),
        categorical_column("handle_style", "Handle", minWidth=130),
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
            "impact_rate_bpm",
            "BPM",
            "params.value == null ? '-' : params.value.toLocaleString()",
            minWidth=125,
        ),
        number_column(
            "impact_energy_j",
            "Impact E",
            "params.value == null ? '-' : `${params.value} J`",
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
        boolean_column("anti_rotation", "Anti-Rotation", minWidth=145),
        boolean_column(
            "active_vibration_control",
            "Vibration Control",
            minWidth=165,
        ),
        boolean_column("shocks_system", "SHOCKS", minWidth=125),
        boolean_column("used_for_chipping", "Chipping", minWidth=125),
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
