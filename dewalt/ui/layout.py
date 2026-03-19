from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import dash_bootstrap_components as dbc
from dash import dcc, html
from dash_iconify import DashIconify

from dewalt.tool_families.base import StatCard

from .config import APP_LOCATION_ID
from .context import DashboardContext

GITHUB_REPO_URL = "https://github.com/perfectly-preserved-pie/dewalt"
CONTACT_EMAIL = "hello@example.com"


@dataclass(frozen=True)
class DashboardSection:
    """Component bundle for one tool-family tab.

    Attributes:
        context: Shared dashboard context for the tool family.
        master_grid: Dash AG Grid instance for the family master table.
        compare_grid: Dash AG Grid instance for the family comparison table.
        modal: Dash Bootstrap modal instance for the family detail popup.
    """

    context: DashboardContext
    master_grid: Any
    compare_grid: Any
    modal: Any


def build_stat_card(card: StatCard) -> html.Div:
    """Build one hero statistic card.

    Args:
        card: Stat-card metadata to render.

    Returns:
        A ``Div`` containing the stat label and value.
    """
    return html.Div(
        [
            html.Span(card.label, className="stat-label"),
            html.Strong(card.value, className=card.value_class_name),
        ],
        className=card.card_class_name,
    )


def format_snapshot_time(scraped_at: str) -> str:
    """Format an ISO snapshot timestamp for display in hero cards.

    Args:
        scraped_at: Raw ISO timestamp from a tool-family snapshot.

    Returns:
        Human-readable timestamp text for the dashboard.
    """
    return scraped_at.replace("T", " ").replace("+00:00", " UTC")


def format_family_list(labels: list[str]) -> str:
    """Format tool-family labels into natural-language copy.

    Args:
        labels: Ordered list of family labels.

    Returns:
        A human-readable string joining the family labels, sorted alphabetically.
    """
    labels = sorted(labels)
    if not labels:
        return "DEWALT tools"
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return f"{', '.join(labels[:-1])}, and {labels[-1]}"


def build_family_tab(section: DashboardSection) -> dcc.Tab:
    """Build the complete tab content for one tool family.

    Args:
        section: Tool-family component bundle to render.

    Returns:
        A populated Dash tab for the given family.
    """
    context = section.context
    family_stats = [build_stat_card(card) for card in context.stat_cards]

    return dcc.Tab(
        label=context.family.tab_label,
        value=context.family.slug,
        className="tool-tab",
        selected_className="tool-tab tool-tab-selected",
        children=[
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.H2(context.family.hero_title, className="section-title"),
                                    html.Div(
                                        [
                                            html.Span("Last Updated", className="stat-label"),
                                            html.Span(
                                                format_snapshot_time(context.snapshot["scraped_at"]),
                                                className="family-updated-time",
                                            ),
                                        ],
                                        className="family-updated",
                                    ),
                                ],
                                className="family-header",
                            ),
                            html.P(context.family.hero_copy, className="family-copy"),
                        ],
                        className="family-overview",
                    ),
                    html.Div(family_stats, className="stats-grid family-stats"),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        context.family.selection_note,
                                        className="panel-note",
                                    ),
                                    html.Div(
                                        id=context.family.ids.selection_summary,
                                        className="selection-summary",
                                    ),
                                ],
                                className="panel-header",
                            ),
                            section.master_grid,
                            section.modal,
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.H2(
                                                context.family.compare_title,
                                                className="section-title",
                                            ),
                                            html.Div(
                                                id=context.family.ids.compare_note,
                                                className="compare-note",
                                            ),
                                        ],
                                        className="compare-header",
                                    ),
                                    html.Div(
                                        [
                                            dcc.Checklist(
                                                id=context.family.ids.compare_options,
                                                options=[
                                                    {
                                                        "label": "Differences only",
                                                        "value": "differences",
                                                    }
                                                ],
                                                value=[],
                                                className="compare-options",
                                                inputClassName="compare-options-input",
                                                labelClassName="compare-options-label",
                                                persistence=f"{context.family.slug}-compare-options",
                                                persistence_type="local",
                                            ),
                                            html.A(
                                                "Share this shortlist",
                                                id=context.family.ids.compare_share_link,
                                                href=f"?family={context.family.slug}",
                                                className="compare-share-link",
                                            ),
                                        ],
                                        className="compare-toolbar",
                                    ),
                                    section.compare_grid,
                                    html.Div(
                                        id=context.family.ids.compare_cards,
                                        className="mobile-compare-cards",
                                    ),
                                ],
                                className="compare-shell",
                            ),
                        ],
                        className="family-panel",
                    ),
                ],
                className="tab-panel",
            )
        ],
    )


def build_layout(sections: Sequence[DashboardSection]) -> dbc.Container:
    """Assemble the top-level dashboard layout.

    Args:
        sections: Ordered component bundles for each tool-family tab.

    Returns:
        A Bootstrap container representing the full app layout.
    """
    if not sections:
        raise ValueError("At least one dashboard section is required.")

    sorted_sections = sorted(sections, key=lambda section: section.context.family.tab_label)
    family_labels = [section.context.family.tab_label for section in sorted_sections]
    total_models = sum(len(section.context.display_rows) for section in sorted_sections)

    stats = [
        build_stat_card(StatCard("Families", str(len(sections)))),
        build_stat_card(StatCard("Models", str(total_models))),
    ]

    return dbc.Container(
        [
            dcc.Location(id=APP_LOCATION_ID, refresh="callback-nav"),
            html.Div(
                [
                    html.Div(
                        [
                            html.P("Unofficial DEWALT TOOL INDEX", className="eyebrow"),
                            html.H1("DEWALT Compare", className="hero-title"),
                            html.P(
                                (
                                    f"Compare DEWALT {format_family_list(family_labels)} in one place. "
                                    "Filter the list, open any model for the details, and line up "
                                    "your top picks side by side."
                                ),
                                className="hero-copy",
                            ),
                            html.Div(
                                [
                                    html.Span(
                                        [
                                            DashIconify(icon="octicon:mark-github-16"),
                                            html.A(
                                                "GitHub",
                                                href=GITHUB_REPO_URL,
                                                target="_blank",
                                                rel="noopener noreferrer",
                                            ),
                                        ],
                                        style={
                                            "display": "inline-flex",
                                            "alignItems": "center",
                                            "gap": "5px",
                                        },
                                    ),
                                    html.Span(
                                        [
                                            DashIconify(icon="streamline-color:send-email"),
                                            html.A(
                                                CONTACT_EMAIL,
                                                href=f"mailto:{CONTACT_EMAIL}",
                                                target="_blank",
                                            ),
                                        ],
                                        style={
                                            "display": "inline-flex",
                                            "alignItems": "center",
                                            "gap": "5px",
                                        },
                                    ),
                                ],
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "columnGap": "15px",
                                    "rowGap": "8px",
                                    "flexWrap": "wrap",
                                    "marginTop": "1rem",
                                },
                            ),
                        ],
                        className="hero-copy-block",
                    ),
                    html.Div(stats, className="stats-grid"),
                ],
                className="hero-panel",
            ),
            dcc.Tabs(
                id="tool-tabs",
                value=sorted_sections[0].context.family.slug,
                className="tool-tabs",
                persistence=True,
                persistence_type="local",
                children=[build_family_tab(section) for section in sorted_sections],
            ),
            html.Footer(
                [
                    html.P(
                        "Independent project for browsing and comparing tool data.",
                        className="footer-kicker",
                    ),
                    html.P(
                        (
                            "This site is not affiliated with, endorsed by, or sponsored by "
                            "DEWALT, Stanley Black & Decker, or any of their affiliates."
                        ),
                        className="footer-legal",
                    ),
                    html.P(
                        (
                            "DEWALT and any other product names, logos, and marks shown here "
                            "are the property of their respective owners."
                        ),
                        className="footer-legal",
                    ),
                    html.P(
                        (
                            "Tool information is compiled from publicly available manufacturer "
                            "pages and may be incomplete, outdated, or inaccurate. Verify "
                            "specifications, safety information, and compatibility with the "
                            "official manufacturer before purchase or use."
                        ),
                        className="footer-legal",
                    ),
                ],
                className="app-footer",
            ),
        ],
        fluid=True,
        className="app-shell",
    )
