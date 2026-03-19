from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dewalt.tool_families.base import RowData, StatCard, ToolFamilyDefinition

from .config import MAX_COMPARE


@dataclass(frozen=True)
class DashboardContext:
    """Precomputed dashboard state shared across layout and callbacks."""

    family: ToolFamilyDefinition
    snapshot: dict[str, Any]
    raw_rows: list[RowData]
    display_rows: list[RowData]
    row_lookup: dict[str, RowData]
    grid_row_fields: frozenset[str]
    stat_cards: tuple[StatCard, ...]
    max_compare: int = MAX_COMPARE


def load_dashboard_context(
    family: ToolFamilyDefinition,
    snapshot: dict[str, Any] | None = None,
    raw_rows: list[RowData] | None = None,
    max_compare: int = MAX_COMPARE,
) -> DashboardContext:
    """Build the shared dashboard context from snapshot data.

    Args:
        family: Tool family definition that supplies formatting and layout metadata.
        snapshot: Optional snapshot payload to reuse instead of loading from disk.
        raw_rows: Optional raw grinder rows to reuse instead of loading from disk.
        max_compare: Maximum number of selected rows shown in the comparison grid.

    Returns:
        A populated :class:`DashboardContext` instance for the current dashboard state.
    """
    snapshot_data = snapshot or family.load_snapshot()
    source_rows = raw_rows or family.load_rows()
    display_rows = family.build_display_rows(source_rows)

    return DashboardContext(
        family=family,
        snapshot=snapshot_data,
        raw_rows=source_rows,
        display_rows=display_rows,
        row_lookup={row["sku"]: row for row in display_rows if row.get("sku")},
        grid_row_fields=frozenset(display_rows[0].keys()) if display_rows else frozenset(),
        stat_cards=family.build_stat_cards(display_rows),
        max_compare=max_compare,
    )
