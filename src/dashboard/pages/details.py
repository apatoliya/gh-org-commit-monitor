import dash
from dash import html, dcc, callback, Input, Output, dash_table
import dash_bootstrap_components as dbc
import pandas as pd

from src.database import get_commits_df
from src.dashboard.pages.overview import FRIENDLY_NAMES

dash.register_page(__name__, path="/details", name="Commit Details")

layout = html.Div([
    html.H3("Commit Details", className="mb-4"),
    dbc.Row([
        dbc.Col(
            dcc.Dropdown(
                id="details-classification-filter",
                options=[
                    {"label": "All", "value": "all"},
                    {"label": "Human Only", "value": "human"},
                    {"label": "AI-Assisted Only", "value": "ai"},
                ],
                value="all",
                clearable=False,
            ),
            width=3,
        ),
        dbc.Col(
            dbc.Button("Export CSV", id="export-csv-btn", color="secondary", size="sm"),
            width=2,
        ),
    ], className="mb-3"),
    dcc.Download(id="csv-download"),
    html.Div(id="details-content"),
])


@callback(
    Output("details-content", "children"),
    Input("filter-state", "data"),
    Input("details-classification-filter", "value"),
    Input("refresh-btn", "n_clicks"),
    Input("auto-refresh", "n_intervals"),
)
def render_details(filters, class_filter, *_):
    filters = filters or {}
    df = get_commits_df(
        start_date=filters.get("start_date"),
        end_date=filters.get("end_date"),
    )

    repos = filters.get("repos", [])
    authors = filters.get("authors", [])
    if repos:
        df = df[df["repo_name"].isin(repos)]
    if authors:
        df = df[df["author_login"].isin(authors)]

    if class_filter == "human":
        df = df[df["classification"] == "human"]
    elif class_filter == "ai":
        df = df[df["classification"] != "human"]

    if df.empty:
        return dbc.Alert("No commits match the current filters.", color="info")

    # Prepare display dataframe
    display = df[["sha", "repo_name", "author_login", "committed_at", "classification",
                   "confidence", "detection_method", "additions", "deletions", "files_changed", "message"]].copy()
    display["sha"] = display["sha"].str[:10]
    display["repo_name"] = display["repo_name"].str.split("/").str[-1]
    display["classification"] = display["classification"].map(FRIENDLY_NAMES)
    display["committed_at"] = display["committed_at"].dt.strftime("%Y-%m-%d %H:%M")
    display["message"] = display["message"].str.split("\n").str[0].str[:100]
    display["confidence"] = display["confidence"].round(2)

    display.columns = ["SHA", "Repo", "Author", "Date", "Classification",
                       "Confidence", "Detection", "Lines+", "Lines-", "Files", "Message"]

    table = dash_table.DataTable(
        data=display.to_dict("records"),
        columns=[{"name": c, "id": c} for c in display.columns],
        page_size=25,
        sort_action="native",
        filter_action="native",
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "left", "padding": "8px", "fontSize": "13px"},
        style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
        style_data_conditional=[
            {
                "if": {"filter_query": '{Classification} != "Human"'},
                "backgroundColor": "#fff3f3",
            },
        ],
    )

    return html.Div([
        html.P(f"Showing {len(display):,} commits", className="text-muted"),
        table,
    ])


@callback(
    Output("csv-download", "data"),
    Input("export-csv-btn", "n_clicks"),
    Input("filter-state", "data"),
    Input("details-classification-filter", "value"),
    prevent_initial_call=True,
)
def export_csv(n_clicks, filters, class_filter):
    if not n_clicks:
        return None

    filters = filters or {}
    df = get_commits_df(
        start_date=filters.get("start_date"),
        end_date=filters.get("end_date"),
    )

    repos = filters.get("repos", [])
    authors = filters.get("authors", [])
    if repos:
        df = df[df["repo_name"].isin(repos)]
    if authors:
        df = df[df["author_login"].isin(authors)]

    if class_filter == "human":
        df = df[df["classification"] == "human"]
    elif class_filter == "ai":
        df = df[df["classification"] != "human"]

    return dcc.send_data_frame(df.to_csv, "commits_export.csv", index=False)
