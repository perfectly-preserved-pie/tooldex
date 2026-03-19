from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, TypeAlias


RowData: TypeAlias = dict[str, Any]
ColumnDef: TypeAlias = dict[str, Any]


@dataclass(frozen=True)
class StatCard:
    """Display metadata for a single hero statistic card."""

    label: str
    value: str
    card_class_name: str = "stat-card"
    value_class_name: str = "stat-value"


@dataclass(frozen=True)
class ToolFamilyIds:
    """Component ids reserved for one tool family dashboard."""

    grid: str
    selection_summary: str
    compare_note: str
    compare_options: str
    compare_share_link: str
    compare_grid: str
    compare_cards: str
    modal: str
    modal_header: str
    modal_content: str
    modal_close: str


def build_family_ids(slug: str) -> ToolFamilyIds:
    """Build the component ids for a tool family.

    Args:
        slug: Stable family slug used to namespace component ids.

    Returns:
        A populated id bundle for all family-scoped components.
    """
    return ToolFamilyIds(
        grid=f"{slug}-grid",
        selection_summary=f"{slug}-selection-summary",
        compare_note=f"{slug}-compare-note",
        compare_options=f"{slug}-compare-options",
        compare_share_link=f"{slug}-compare-share-link",
        compare_grid=f"{slug}-compare-grid",
        compare_cards=f"{slug}-compare-cards",
        modal=f"{slug}-modal",
        modal_header=f"{slug}-modal-header",
        modal_content=f"{slug}-modal-content",
        modal_close=f"{slug}-modal-close",
    )


@dataclass(frozen=True)
class ToolFamilyDefinition:
    """Definition object for one tool family in the dashboard."""

    slug: str
    tab_label: str
    hero_title: str
    hero_copy: str
    selection_note: str
    no_selection_note: str
    compare_title: str
    compare_fields: tuple[tuple[str, str], ...]
    compare_boolean_fields: frozenset[str]
    detail_fields: tuple[tuple[str, str], ...]
    ids: ToolFamilyIds
    load_snapshot: Callable[[], dict[str, Any]]
    load_rows: Callable[[], list[RowData]]
    build_display_rows: Callable[[list[RowData]], list[RowData]]
    compare_display_value: Callable[[RowData, str], str]
    build_master_column_defs: Callable[[], list[ColumnDef]]
    build_stat_cards: Callable[[list[RowData]], tuple[StatCard, ...]]
