from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ANGLE_GRINDER_DATA_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "dewalt_angle_grinders.json"
)
CIRCULAR_SAW_DATA_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "dewalt_circular_saws.json"
)
CUT_OUT_TOOL_DATA_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "dewalt_cut_out_tools.json"
)
DRILL_DRIVER_DATA_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "dewalt_drill_drivers.json"
)
FINISH_BRAD_NAILER_DATA_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "dewalt_finish_brad_nailers.json"
)
HAMMER_DRILL_DATA_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "dewalt_hammer_drills.json"
)
IMPACT_DRIVER_DATA_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "dewalt_impact_drivers.json"
)
IMPACT_WRENCH_DATA_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "dewalt_impact_wrenches.json"
)
OSCILLATING_MULTI_TOOL_DATA_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "dewalt_oscillating_multi_tools.json"
)
MITER_SAW_DATA_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "dewalt_miter_saws.json"
)
RATCHET_DATA_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "dewalt_ratchets.json"
)
TABLE_SAW_DATA_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "dewalt_table_saws.json"
)
ROTARY_HAMMER_DATA_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "dewalt_rotary_hammers.json"
)
VACUUM_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "dewalt_vacuums.json"
REMOVED_COPY_FIELDS = frozenset(
    {
        "description",
        "features",
        "additional_features",
        "includes",
        "applications",
        "disclaimers",
    }
)


def normalize_power_source(value: str | None) -> str | None:
    """Normalize power source labels from the DEWALT snapshot.

    Args:
        value: Raw power source label from the snapshot.

    Returns:
        The normalized power source label, or ``None`` when the input is ``None``.
    """
    if value == "AC/DC Corded":
        return "Corded"
    return value


def sanitize_snapshot_row(row: dict[str, Any]) -> dict[str, Any]:
    """Remove copied long-form marketing text from one snapshot row."""
    sanitized_row = dict(row)
    for field_name in REMOVED_COPY_FIELDS:
        sanitized_row.pop(field_name, None)
    return sanitized_row


def sanitize_snapshot_payload(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of a snapshot payload without copied long-form text fields."""
    sanitized_snapshot = dict(snapshot)
    rows = sanitized_snapshot.get("rows")
    if isinstance(rows, list):
        sanitized_snapshot["rows"] = [
            sanitize_snapshot_row(row) if isinstance(row, dict) else row for row in rows
        ]
    return sanitized_snapshot


def load_snapshot(path: Path = ANGLE_GRINDER_DATA_PATH) -> dict[str, Any]:
    """Load a raw saved DEWALT snapshot from disk.

    Args:
        path: Filesystem path to the snapshot JSON file.

    Returns:
        The parsed snapshot payload as a dictionary.
    """
    if not path.exists():
        raise FileNotFoundError(f"Missing data snapshot at {path}.")
    return sanitize_snapshot_payload(json.loads(path.read_text()))


def load_angle_grinder_snapshot(path: Path = ANGLE_GRINDER_DATA_PATH) -> dict[str, Any]:
    """Load the saved angle-grinder snapshot from disk.

    Args:
        path: Filesystem path to the grinder snapshot JSON file.

    Returns:
        The parsed grinder snapshot payload as a dictionary.
    """
    return load_snapshot(path)


def load_angle_grinders(path: Path = ANGLE_GRINDER_DATA_PATH) -> list[dict[str, Any]]:
    """Load normalized grinder rows from the snapshot.

    Args:
        path: Filesystem path to the snapshot JSON file.

    Returns:
        A list of grinder row dictionaries with normalized power source labels.
    """
    snapshot = load_angle_grinder_snapshot(path)
    rows = []
    for row in snapshot.get("rows", []):
        normalized_row = dict(row)
        normalized_row["power_source"] = normalize_power_source(row.get("power_source"))
        rows.append(normalized_row)
    return rows


def load_circular_saw_snapshot(path: Path = CIRCULAR_SAW_DATA_PATH) -> dict[str, Any]:
    """Load the saved circular-saw snapshot from disk.

    Args:
        path: Filesystem path to the circular-saw snapshot JSON file.

    Returns:
        The parsed circular-saw snapshot payload as a dictionary.
    """
    return load_snapshot(path)


def load_circular_saws(path: Path = CIRCULAR_SAW_DATA_PATH) -> list[dict[str, Any]]:
    """Load normalized circular-saw rows from the snapshot.

    Args:
        path: Filesystem path to the snapshot JSON file.

    Returns:
        A list of circular-saw row dictionaries with normalized power-source labels.
    """
    snapshot = load_circular_saw_snapshot(path)
    rows = []
    for row in snapshot.get("rows", []):
        normalized_row = dict(row)
        normalized_row["power_source"] = normalize_power_source(row.get("power_source"))
        rows.append(normalized_row)
    return rows


def load_cut_out_tool_snapshot(path: Path = CUT_OUT_TOOL_DATA_PATH) -> dict[str, Any]:
    """Load the saved cut-out-tool snapshot from disk.

    Args:
        path: Filesystem path to the cut-out-tool snapshot JSON file.

    Returns:
        The parsed cut-out-tool snapshot payload as a dictionary.
    """
    return load_snapshot(path)


def load_cut_out_tools(path: Path = CUT_OUT_TOOL_DATA_PATH) -> list[dict[str, Any]]:
    """Load normalized cut-out-tool rows from the snapshot.

    Args:
        path: Filesystem path to the snapshot JSON file.

    Returns:
        A list of cut-out-tool row dictionaries with normalized power-source labels.
    """
    snapshot = load_cut_out_tool_snapshot(path)
    rows = []
    for row in snapshot.get("rows", []):
        normalized_row = dict(row)
        normalized_row["power_source"] = normalize_power_source(row.get("power_source"))
        rows.append(normalized_row)
    return rows


def load_finish_brad_nailer_snapshot(
    path: Path = FINISH_BRAD_NAILER_DATA_PATH,
) -> dict[str, Any]:
    """Load the saved finish/brad-nailer snapshot from disk.

    Args:
        path: Filesystem path to the finish/brad-nailer snapshot JSON file.

    Returns:
        The parsed finish/brad-nailer snapshot payload as a dictionary.
    """
    return load_snapshot(path)


def load_finish_brad_nailers(
    path: Path = FINISH_BRAD_NAILER_DATA_PATH,
) -> list[dict[str, Any]]:
    """Load normalized finish/brad-nailer rows from the snapshot.

    Args:
        path: Filesystem path to the snapshot JSON file.

    Returns:
        A list of finish/brad-nailer row dictionaries with normalized power-source labels.
    """
    snapshot = load_finish_brad_nailer_snapshot(path)
    rows = []
    for row in snapshot.get("rows", []):
        normalized_row = dict(row)
        normalized_row["power_source"] = normalize_power_source(row.get("power_source"))
        rows.append(normalized_row)
    return rows


def load_drill_driver_snapshot(path: Path = DRILL_DRIVER_DATA_PATH) -> dict[str, Any]:
    """Load the saved drill-driver snapshot from disk.

    Args:
        path: Filesystem path to the drill-driver snapshot JSON file.

    Returns:
        The parsed drill-driver snapshot payload as a dictionary.
    """
    return load_snapshot(path)


def load_drill_drivers(path: Path = DRILL_DRIVER_DATA_PATH) -> list[dict[str, Any]]:
    """Load normalized drill-driver rows from the snapshot.

    Args:
        path: Filesystem path to the snapshot JSON file.

    Returns:
        A list of drill-driver row dictionaries with normalized power source labels.
    """
    snapshot = load_drill_driver_snapshot(path)
    rows = []
    for row in snapshot.get("rows", []):
        normalized_row = dict(row)
        normalized_row["power_source"] = normalize_power_source(row.get("power_source"))
        rows.append(normalized_row)
    return rows


def load_miter_saw_snapshot(path: Path = MITER_SAW_DATA_PATH) -> dict[str, Any]:
    """Load the saved miter-saw snapshot from disk.

    Args:
        path: Filesystem path to the miter-saw snapshot JSON file.

    Returns:
        The parsed miter-saw snapshot payload as a dictionary.
    """
    return load_snapshot(path)


def load_miter_saws(path: Path = MITER_SAW_DATA_PATH) -> list[dict[str, Any]]:
    """Load normalized miter-saw rows from the snapshot.

    Args:
        path: Filesystem path to the snapshot JSON file.

    Returns:
        A list of miter-saw row dictionaries with normalized power-source labels.
    """
    snapshot = load_miter_saw_snapshot(path)
    rows = []
    for row in snapshot.get("rows", []):
        normalized_row = dict(row)
        normalized_row["power_source"] = normalize_power_source(row.get("power_source"))
        rows.append(normalized_row)
    return rows


def load_table_saw_snapshot(path: Path = TABLE_SAW_DATA_PATH) -> dict[str, Any]:
    """Load the saved table-saw snapshot from disk.

    Args:
        path: Filesystem path to the table-saw snapshot JSON file.

    Returns:
        The parsed table-saw snapshot payload as a dictionary.
    """
    return load_snapshot(path)


def load_table_saws(path: Path = TABLE_SAW_DATA_PATH) -> list[dict[str, Any]]:
    """Load normalized table-saw rows from the snapshot.

    Args:
        path: Filesystem path to the snapshot JSON file.

    Returns:
        A list of table-saw row dictionaries with normalized power-source labels.
    """
    snapshot = load_table_saw_snapshot(path)
    rows = []
    for row in snapshot.get("rows", []):
        normalized_row = dict(row)
        normalized_row["power_source"] = normalize_power_source(row.get("power_source"))
        rows.append(normalized_row)
    return rows


def load_vacuum_snapshot(path: Path = VACUUM_DATA_PATH) -> dict[str, Any]:
    """Load the saved vacuum snapshot from disk.

    Args:
        path: Filesystem path to the vacuum snapshot JSON file.

    Returns:
        The parsed vacuum snapshot payload as a dictionary.
    """
    return load_snapshot(path)


def load_vacuums(path: Path = VACUUM_DATA_PATH) -> list[dict[str, Any]]:
    """Load normalized vacuum rows from the snapshot.

    Args:
        path: Filesystem path to the snapshot JSON file.

    Returns:
        A list of vacuum row dictionaries with normalized power-source labels.
    """
    snapshot = load_vacuum_snapshot(path)
    rows = []
    for row in snapshot.get("rows", []):
        normalized_row = dict(row)
        normalized_row["power_source"] = normalize_power_source(row.get("power_source"))
        rows.append(normalized_row)
    return rows


def load_hammer_drill_snapshot(path: Path = HAMMER_DRILL_DATA_PATH) -> dict[str, Any]:
    """Load the saved hammer-drill snapshot from disk.

    Args:
        path: Filesystem path to the hammer-drill snapshot JSON file.

    Returns:
        The parsed hammer-drill snapshot payload as a dictionary.
    """
    return load_snapshot(path)


def load_hammer_drills(path: Path = HAMMER_DRILL_DATA_PATH) -> list[dict[str, Any]]:
    """Load normalized hammer-drill rows from the snapshot.

    Args:
        path: Filesystem path to the snapshot JSON file.

    Returns:
        A list of hammer-drill row dictionaries with normalized power source labels.
    """
    snapshot = load_hammer_drill_snapshot(path)
    rows = []
    for row in snapshot.get("rows", []):
        normalized_row = dict(row)
        normalized_row["power_source"] = normalize_power_source(row.get("power_source"))
        rows.append(normalized_row)
    return rows


def load_impact_driver_snapshot(path: Path = IMPACT_DRIVER_DATA_PATH) -> dict[str, Any]:
    """Load the saved impact-driver snapshot from disk.

    Args:
        path: Filesystem path to the impact-driver snapshot JSON file.

    Returns:
        The parsed impact-driver snapshot payload as a dictionary.
    """
    return load_snapshot(path)


def load_impact_drivers(path: Path = IMPACT_DRIVER_DATA_PATH) -> list[dict[str, Any]]:
    """Load normalized impact-driver rows from the snapshot.

    Args:
        path: Filesystem path to the snapshot JSON file.

    Returns:
        A list of impact-driver row dictionaries with normalized power-source labels.
    """
    snapshot = load_impact_driver_snapshot(path)
    rows = []
    for row in snapshot.get("rows", []):
        normalized_row = dict(row)
        normalized_row["power_source"] = normalize_power_source(row.get("power_source"))
        rows.append(normalized_row)
    return rows


def load_impact_wrench_snapshot(path: Path = IMPACT_WRENCH_DATA_PATH) -> dict[str, Any]:
    """Load the saved impact-wrench snapshot from disk.

    Args:
        path: Filesystem path to the impact-wrench snapshot JSON file.

    Returns:
        The parsed impact-wrench snapshot payload as a dictionary.
    """
    return load_snapshot(path)


def load_impact_wrenches(path: Path = IMPACT_WRENCH_DATA_PATH) -> list[dict[str, Any]]:
    """Load normalized impact-wrench rows from the snapshot.

    Args:
        path: Filesystem path to the snapshot JSON file.

    Returns:
        A list of impact-wrench row dictionaries with normalized power-source labels.
    """
    snapshot = load_impact_wrench_snapshot(path)
    rows = []
    for row in snapshot.get("rows", []):
        normalized_row = dict(row)
        normalized_row["power_source"] = normalize_power_source(row.get("power_source"))
        rows.append(normalized_row)
    return rows


def load_oscillating_multi_tool_snapshot(
    path: Path = OSCILLATING_MULTI_TOOL_DATA_PATH,
) -> dict[str, Any]:
    """Load the saved oscillating multi-tool snapshot from disk.

    Args:
        path: Filesystem path to the oscillating multi-tool snapshot JSON file.

    Returns:
        The parsed oscillating multi-tool snapshot payload as a dictionary.
    """
    return load_snapshot(path)


def load_oscillating_multi_tools(
    path: Path = OSCILLATING_MULTI_TOOL_DATA_PATH,
) -> list[dict[str, Any]]:
    """Load normalized oscillating multi-tool rows from the snapshot.

    Args:
        path: Filesystem path to the snapshot JSON file.

    Returns:
        A list of oscillating multi-tool row dictionaries with normalized power-source
        labels.
    """
    snapshot = load_oscillating_multi_tool_snapshot(path)
    rows = []
    for row in snapshot.get("rows", []):
        normalized_row = dict(row)
        normalized_row["power_source"] = normalize_power_source(row.get("power_source"))
        rows.append(normalized_row)
    return rows


def load_ratchet_snapshot(path: Path = RATCHET_DATA_PATH) -> dict[str, Any]:
    """Load the saved ratchet snapshot from disk.

    Args:
        path: Filesystem path to the ratchet snapshot JSON file.

    Returns:
        The parsed ratchet snapshot payload as a dictionary.
    """
    return load_snapshot(path)


def load_ratchets(path: Path = RATCHET_DATA_PATH) -> list[dict[str, Any]]:
    """Load normalized ratchet rows from the snapshot.

    Args:
        path: Filesystem path to the snapshot JSON file.

    Returns:
        A list of ratchet row dictionaries with normalized power-source labels.
    """
    snapshot = load_ratchet_snapshot(path)
    rows = []
    for row in snapshot.get("rows", []):
        normalized_row = dict(row)
        normalized_row["power_source"] = normalize_power_source(row.get("power_source"))
        rows.append(normalized_row)
    return rows


def load_rotary_hammer_snapshot(path: Path = ROTARY_HAMMER_DATA_PATH) -> dict[str, Any]:
    """Load the saved rotary-hammer snapshot from disk.

    Args:
        path: Filesystem path to the rotary-hammer snapshot JSON file.

    Returns:
        The parsed rotary-hammer snapshot payload as a dictionary.
    """
    return load_snapshot(path)


def load_rotary_hammers(path: Path = ROTARY_HAMMER_DATA_PATH) -> list[dict[str, Any]]:
    """Load normalized rotary-hammer rows from the snapshot.

    Args:
        path: Filesystem path to the snapshot JSON file.

    Returns:
        A list of rotary-hammer row dictionaries with normalized power-source labels.
    """
    snapshot = load_rotary_hammer_snapshot(path)
    rows = []
    for row in snapshot.get("rows", []):
        normalized_row = dict(row)
        normalized_row["power_source"] = normalize_power_source(row.get("power_source"))
        rows.append(normalized_row)
    return rows
