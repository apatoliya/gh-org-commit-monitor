import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc

from src.database import init_db, get_repo_names, get_author_logins
from src.dashboard.pages.home import layout as overview_layout
from src.dashboard.pages.repos import layout as repos_layout
from src.dashboard.pages.authors import layout as authors_layout
from src.dashboard.pages.details import layout as details_layout

init_db()

app = dash.Dash(
    __name__,
    use_pages=False,
    external_stylesheets=[dbc.themes.CYBORG],
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
            dbc.Button("Refresh", id="refresh-btn", className="btn-cyber", size="sm"),
            width=2,
            className="d-flex align-items-center",
        ),
    ],
    className="p-3 filters-bar",
)

PAGE_MAP = {
    "/": overview_layout,
    "/repos": repos_layout,
    "/authors": authors_layout,
    "/details": details_layout,
}

app.layout = dbc.Container(
    [
        dcc.Location(id="url", refresh=False),
        # Background animations
        html.Div(className="bg-grid"),
        html.Div(
            [html.Div(className="particle") for _ in range(20)],
            className="bg-particles",
        ),
        # Hero banner
        html.Div([
            html.Div([
                html.H4("GitHub Org Commit Monitor", className="hero-title"),
                html.P("Real-time AI Code Detection & Analytics", className="hero-tagline"),
            ], className="hero-banner"),
            html.Div(className="hero-banner-border"),
        ]),
        filters_bar,
        dbc.Row(
            [
                dbc.Col(sidebar, width=2, className="sidebar-col min-vh-100"),
                dbc.Col(html.Div(id="page-content"), width=10, className="p-4 content-area"),
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
    Output("page-content", "children"),
    Input("url", "pathname"),
)
def display_page(pathname):
    return PAGE_MAP.get(pathname, overview_layout)


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
