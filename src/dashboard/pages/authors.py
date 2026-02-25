import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd

from src.database import get_commits_df
from src.dashboard.theme import FRIENDLY_NAMES, apply_dark_layout


layout = html.Div([
    html.H3("Author Breakdown", className="mb-4"),
    html.Div(id="authors-content"),
])


@callback(
    Output("authors-content", "children"),
    Input("filter-state", "data"),
    Input("refresh-btn", "n_clicks"),
    Input("auto-refresh", "n_intervals"),
)
def render_authors(filters, *_):
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

    # Per-author stats
    author_stats = df.groupby("author_login").apply(
        lambda g: pd.Series({
            "total_commits": len(g),
            "ai_commits": (g["classification"] != "human").sum(),
            "repos_count": g["repo_name"].nunique(),
            "tools_used": ", ".join(
                sorted(set(
                    FRIENDLY_NAMES.get(c, c)
                    for c in g[g["classification"] != "human"]["classification"].unique()
                ))
            ) or "None",
        })
    ).reset_index()
    author_stats["ai_pct"] = (author_stats["ai_commits"] / author_stats["total_commits"] * 100).round(1)
    author_stats = author_stats.sort_values("total_commits", ascending=False)

    # Bar chart: top 20 authors by AI usage
    top20 = author_stats.head(20)
    bar_fig = px.bar(
        top20, x="author_login", y="ai_pct",
        title="Top 20 Authors by AI-Assisted Code %",
        labels={"author_login": "Author", "ai_pct": "AI-Assisted %"},
        color="ai_pct",
        color_continuous_scale=[[0, "#0a0a1a"], [0.5, "#b34dff"], [1, "#ff00e5"]],
    )
    apply_dark_layout(bar_fig)
    bar_fig.update_layout(xaxis_tickangle=-45)

    # AI adoption trend per author over time
    ai_df = df[df["classification"] != "human"].copy()
    if not ai_df.empty:
        ai_df["month"] = ai_df["committed_at"].dt.to_period("M").dt.start_time
        # Show top 5 AI users
        top5_authors = author_stats.head(5)["author_login"].tolist()
        trend_df = ai_df[ai_df["author_login"].isin(top5_authors)]
        trend_agg = trend_df.groupby(["month", "author_login"]).size().reset_index(name="ai_commits")
        trend_fig = px.line(
            trend_agg, x="month", y="ai_commits", color="author_login",
            title="AI-Assisted Commits Over Time (Top 5 Authors)",
            labels={"month": "Month", "ai_commits": "AI Commits", "author_login": "Author"},
        )
        apply_dark_layout(trend_fig)
        trend_chart = dcc.Graph(figure=trend_fig)
    else:
        trend_chart = dbc.Alert("No AI-assisted commits found.", color="info")

    # Table
    table_df = author_stats[["author_login", "total_commits", "ai_commits", "ai_pct", "repos_count", "tools_used"]].copy()
    table_df.columns = ["Author", "Total Commits", "AI Commits", "AI %", "Repos", "AI Tools Used"]
    table = dbc.Table.from_dataframe(table_df, striped=True, bordered=True, hover=True, size="sm")

    return html.Div([
        dbc.Row([
            dbc.Col(dcc.Graph(figure=bar_fig), width=6),
            dbc.Col(trend_chart, width=6),
        ], className="mb-4"),
        html.H5("All Authors", className="mb-3"),
        html.Div(table, style={"maxHeight": "500px", "overflowY": "auto"}),
    ])
