import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc

from src.database import init_db, get_repo_names, get_author_logins

init_db()

app = dash.Dash(
    __name__,
    use_pages=True,
    pages_folder="pages",
    external_stylesheets=[dbc.themes.FLATLY],
    suppress_callback_exceptions=True,
    title="GitHub Org Commit Monitor",
)

# Sidebar navigation
sidebar = dbc.Nav(
    [
        dbc.NavLink("Overview", href="/", active="exact", className="mb-1"),
        dbc.NavLink("Repositories", href="/repos", active="exact", className="mb-1"),
        dbc.NavLink("Authors", href="/authors", active="exact", className="mb-1"),
        dbc.NavLink("Commit Details", href="/details", active="exact", className="mb-1"),
    ],
    vertical=True,
    pills=True,
    className="p-3",
)

# Global filters bar
filters_bar = dbc.Row(
    [
        dbc.Col(
            dcc.DatePickerRange(
                id="date-range",
                start_date_placeholder_text="Start Date",
                end_date_placeholder_text="End Date",
                className="w-100",
            ),
            width=3,
        ),
        dbc.Col(
            dcc.Dropdown(
                id="repo-filter",
                placeholder="Filter by repo...",
                multi=True,
                className="w-100",
            ),
            width=4,
        ),
        dbc.Col(
            dcc.Dropdown(
                id="author-filter",
                placeholder="Filter by author...",
                multi=True,
                className="w-100",
            ),
            width=3,
        ),
        dbc.Col(
            dbc.Button("Refresh", id="refresh-btn", color="primary", size="sm"),
            width=2,
            className="d-flex align-items-center",
        ),
    ],
    className="p-3 bg-light border-bottom",
)

app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    html.H4("GitHub Org Commit Monitor", className="text-white mb-0"),
                    className="bg-dark p-3",
                )
            ]
        ),
        filters_bar,
        dbc.Row(
            [
                dbc.Col(sidebar, width=2, className="bg-light border-end min-vh-100"),
                dbc.Col(dash.page_container, width=10, className="p-4"),
            ]
        ),
        # Auto-refresh every 5 minutes
        dcc.Interval(id="auto-refresh", interval=5 * 60 * 1000, n_intervals=0),
        # Stores for filter state
        dcc.Store(id="filter-state"),
    ],
    fluid=True,
    className="p-0",
)


@callback(
    Output("repo-filter", "options"),
    Output("author-filter", "options"),
    Input("refresh-btn", "n_clicks"),
    Input("auto-refresh", "n_intervals"),
)
def update_filter_options(*_):
    repos = get_repo_names()
    authors = get_author_logins()
    return (
        [{"label": r.split("/")[-1], "value": r} for r in repos],
        [{"label": a, "value": a} for a in authors],
    )


@callback(
    Output("filter-state", "data"),
    Input("date-range", "start_date"),
    Input("date-range", "end_date"),
    Input("repo-filter", "value"),
    Input("author-filter", "value"),
)
def store_filters(start_date, end_date, repos, authors):
    return {
        "start_date": start_date,
        "end_date": end_date,
        "repos": repos or [],
        "authors": authors or [],
    }
