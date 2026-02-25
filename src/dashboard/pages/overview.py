import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from src.database import get_commits_df

dash.register_page(__name__, path="/", name="Overview")

# Color map for classifications
CLASS_COLORS = {
    "human": "#636EFA",
    "ai_claude": "#EF553B",
    "ai_copilot": "#00CC96",
    "ai_cursor": "#AB63FA",
    "ai_codex": "#FFA15A",
    "ai_aider": "#19D3F3",
    "ai_cody": "#FF6692",
    "ai_devin": "#B6E880",
    "ai_gemini": "#FF97FF",
    "ai_windsurf": "#FECB52",
    "ai_other": "#999999",
}

FRIENDLY_NAMES = {
    "human": "Human",
    "ai_claude": "Claude",
    "ai_copilot": "GitHub Copilot",
    "ai_cursor": "Cursor",
    "ai_codex": "Codex",
    "ai_aider": "Aider",
    "ai_cody": "Cody",
    "ai_devin": "Devin",
    "ai_gemini": "Gemini",
    "ai_windsurf": "Windsurf",
    "ai_other": "Other AI",
}


def _kpi_card(title: str, value: str, color: str = "primary"):
    return dbc.Card(
        dbc.CardBody([
            html.H6(title, className="card-subtitle mb-2 text-muted"),
            html.H3(value, className=f"card-title text-{color}"),
        ]),
        className="shadow-sm",
    )


layout = html.Div([
    html.H3("Overview", className="mb-4"),
    html.Div(id="overview-content"),
])


@callback(
    Output("overview-content", "children"),
    Input("filter-state", "data"),
    Input("refresh-btn", "n_clicks"),
    Input("auto-refresh", "n_intervals"),
)
def render_overview(filters, *_):
    filters = filters or {}
    df = get_commits_df(
        start_date=filters.get("start_date"),
        end_date=filters.get("end_date"),
    )

    # Apply repo/author filters
    repos = filters.get("repos", [])
    authors = filters.get("authors", [])
    if repos:
        df = df[df["repo_name"].isin(repos)]
    if authors:
        df = df[df["author_login"].isin(authors)]

    if df.empty:
        return dbc.Alert("No commit data available. Run the collector first.", color="info")

    total = len(df)
    ai_df = df[df["classification"] != "human"]
    ai_count = len(ai_df)
    human_count = total - ai_count
    ai_pct = f"{(ai_count / total * 100):.1f}%" if total > 0 else "0%"
    repos_count = df["repo_name"].nunique()
    authors_count = df["author_login"].nunique()

    # KPI cards
    kpi_row = dbc.Row([
        dbc.Col(_kpi_card("Total Commits", f"{total:,}"), width=2),
        dbc.Col(_kpi_card("AI-Assisted", f"{ai_count:,} ({ai_pct})", "danger"), width=3),
        dbc.Col(_kpi_card("Human", f"{human_count:,}", "success"), width=2),
        dbc.Col(_kpi_card("Repos Monitored", str(repos_count), "info"), width=2),
        dbc.Col(_kpi_card("Active Authors", str(authors_count), "warning"), width=2),
    ], className="mb-4 g-3")

    # Trend chart: AI vs Human over time (weekly)
    trend_df = df.copy()
    trend_df["week"] = trend_df["committed_at"].dt.to_period("W").dt.start_time
    trend_df["is_ai"] = trend_df["classification"] != "human"
    weekly = trend_df.groupby(["week", "is_ai"]).size().reset_index(name="count")
    weekly["type"] = weekly["is_ai"].map({True: "AI-Assisted", False: "Human"})
    trend_fig = px.line(
        weekly, x="week", y="count", color="type",
        title="Commits Over Time (Weekly)",
        color_discrete_map={"AI-Assisted": "#EF553B", "Human": "#636EFA"},
        labels={"week": "Week", "count": "Commits"},
    )
    trend_fig.update_layout(legend=dict(orientation="h", y=-0.15))

    # Pie chart: classification breakdown
    class_counts = df["classification"].value_counts().reset_index()
    class_counts.columns = ["classification", "count"]
    class_counts["label"] = class_counts["classification"].map(FRIENDLY_NAMES)
    pie_fig = px.pie(
        class_counts, values="count", names="label",
        title="Code Authorship Breakdown",
        color="classification",
        color_discrete_map=CLASS_COLORS,
    )

    # Bar chart: Top 10 repos by AI ratio
    repo_stats = df.groupby("repo_name").apply(
        lambda g: pd.Series({
            "total": len(g),
            "ai_count": (g["classification"] != "human").sum(),
        })
    ).reset_index()
    repo_stats["ai_pct"] = (repo_stats["ai_count"] / repo_stats["total"] * 100).round(1)
    repo_stats["repo_short"] = repo_stats["repo_name"].str.split("/").str[-1]
    top_repos = repo_stats.nlargest(10, "ai_pct")
    bar_fig = px.bar(
        top_repos, x="repo_short", y="ai_pct",
        title="Top 10 Repos by AI-Assisted Code %",
        labels={"repo_short": "Repository", "ai_pct": "AI-Assisted %"},
        color="ai_pct",
        color_continuous_scale="Reds",
    )

    # Recent commits table
    recent = df.head(15)[["sha", "repo_name", "author_login", "committed_at", "classification", "message"]]
    recent = recent.copy()
    recent["sha"] = recent["sha"].str[:8]
    recent["repo_name"] = recent["repo_name"].str.split("/").str[-1]
    recent["message"] = recent["message"].str[:80]
    recent["classification"] = recent["classification"].map(FRIENDLY_NAMES)

    table = dbc.Table.from_dataframe(recent, striped=True, bordered=True, hover=True, size="sm")

    return html.Div([
        kpi_row,
        dbc.Row([
            dbc.Col(dcc.Graph(figure=trend_fig), width=8),
            dbc.Col(dcc.Graph(figure=pie_fig), width=4),
        ], className="mb-4"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=bar_fig), width=12),
        ], className="mb-4"),
        html.H5("Recent Commits", className="mt-4 mb-3"),
        table,
    ])
