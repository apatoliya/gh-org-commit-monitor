import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd

from src.database import get_commits_df

dash.register_page(__name__, path="/repos", name="Repositories")

layout = html.Div([
    html.H3("Repository Breakdown", className="mb-4"),
    html.Div(id="repos-content"),
])


@callback(
    Output("repos-content", "children"),
    Input("filter-state", "data"),
    Input("refresh-btn", "n_clicks"),
    Input("auto-refresh", "n_intervals"),
)
def render_repos(filters, *_):
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

    if df.empty:
        return dbc.Alert("No commit data available.", color="info")

    # Per-repo stats
    stats = df.groupby("repo_name").apply(
        lambda g: pd.Series({
            "total_commits": len(g),
            "ai_commits": (g["classification"] != "human").sum(),
            "human_commits": (g["classification"] == "human").sum(),
            "lines_added": g["additions"].sum(),
            "lines_deleted": g["deletions"].sum(),
            "last_commit": g["committed_at"].max(),
        })
    ).reset_index()
    stats["ai_pct"] = (stats["ai_commits"] / stats["total_commits"] * 100).round(1)
    stats["repo_short"] = stats["repo_name"].str.split("/").str[-1]
    stats = stats.sort_values("total_commits", ascending=False)

    # Stacked bar chart: AI vs Human per repo (top 20)
    top20 = stats.head(20)
    bar_data = pd.melt(
        top20, id_vars=["repo_short"], value_vars=["human_commits", "ai_commits"],
        var_name="type", value_name="count",
    )
    bar_data["type"] = bar_data["type"].map({"human_commits": "Human", "ai_commits": "AI-Assisted"})
    bar_fig = px.bar(
        bar_data, x="repo_short", y="count", color="type",
        title="Top 20 Repos: Human vs AI-Assisted Commits",
        barmode="stack",
        color_discrete_map={"Human": "#636EFA", "AI-Assisted": "#EF553B"},
        labels={"repo_short": "Repository", "count": "Commits"},
    )
    bar_fig.update_layout(xaxis_tickangle=-45, legend=dict(orientation="h", y=-0.25))

    # Summary table
    table_df = stats[["repo_short", "total_commits", "ai_commits", "human_commits", "ai_pct", "lines_added", "lines_deleted"]].copy()
    table_df.columns = ["Repository", "Total", "AI", "Human", "AI %", "Lines +", "Lines -"]
    table = dbc.Table.from_dataframe(table_df, striped=True, bordered=True, hover=True, size="sm")

    return html.Div([
        dbc.Row([
            dbc.Col(dcc.Graph(figure=bar_fig), width=12),
        ], className="mb-4"),
        html.H5("All Repositories", className="mb-3"),
        html.Div(table, style={"maxHeight": "500px", "overflowY": "auto"}),
    ])
