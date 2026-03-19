"""UI helpers for the DEWALT comparison dashboard."""

from .callbacks import register_app_state_callbacks, register_callbacks
from .config import MAX_COMPARE
from .context import DashboardContext, load_dashboard_context
from .grids import (
    build_compare_base_columns,
    build_compare_columns,
    build_compare_grid,
    build_compare_rows,
    build_master_grid,
)
from .layout import DashboardSection, build_layout
from .modal import build_modal, build_modal_content, build_modal_header

__all__ = [
    "DashboardSection",
    "DashboardContext",
    "MAX_COMPARE",
    "build_compare_base_columns",
    "build_compare_columns",
    "build_compare_grid",
    "build_compare_rows",
    "build_layout",
    "build_master_grid",
    "build_modal",
    "build_modal_content",
    "build_modal_header",
    "load_dashboard_context",
    "register_app_state_callbacks",
    "register_callbacks",
]
