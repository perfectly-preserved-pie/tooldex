from __future__ import annotations


MAX_COMPARE = 4
APP_LOCATION_ID = "app-location"

AG_GRID_THEME = {
    "function": (
        "themeQuartz.withParams({"
        "accentColor: '#f0c534', "
        "backgroundColor: '#14181d', "
        "browserColorScheme: 'dark', "
        "foregroundColor: '#f5f6f8', "
        "headerBackgroundColor: '#0f1317', "
        "headerFontWeight: 700, "
        "oddRowBackgroundColor: 'rgba(255,255,255,0.03)'"
        "})"
    )
}

TEXT_FILTER = "agTextColumnFilter"
NUMBER_FILTER = "agNumberColumnFilter"
SET_FILTER = "agSetColumnFilter"
MULTI_FILTER = "agMultiColumnFilter"
BOOLEAN_FILTER = SET_FILTER
