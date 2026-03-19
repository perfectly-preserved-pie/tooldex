from __future__ import annotations

from dewalt.tool_families.base import RowData, StatCard
from dewalt.tool_families.drill_drivers.formatting import (
    build_display_rows,
    compare_display_value,
)


def build_stat_cards(rows: list[RowData]) -> tuple[StatCard, ...]:
    """Build the hammer-drill summary cards shown in the family overview.

    Args:
        rows: Prepared hammer-drill rows currently available to the dashboard.

    Returns:
        A tuple of hero statistic cards for the family.
    """
    return (
        StatCard("Hammer Drills", str(len(rows))),
        StatCard("Cordless", str(sum(1 for row in rows if row["power_source"] == "Cordless"))),
        StatCard("Corded", str(sum(1 for row in rows if row["power_source"] != "Cordless"))),
        StatCard("Brushless", str(sum(1 for row in rows if row["brushless"]))),
    )


__all__ = [
    "build_display_rows",
    "build_stat_cards",
    "compare_display_value",
]
