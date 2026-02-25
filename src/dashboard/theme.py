"""Shared theme constants and helpers for the cyberpunk dashboard."""

import plotly.graph_objects as go

# Color map for classifications
CLASS_COLORS = {
    "human": "#00f0ff",
    "ai_claude": "#ff3c5f",
    "ai_copilot": "#39ff14",
    "ai_cursor": "#b34dff",
    "ai_codex": "#FFA15A",
    "ai_aider": "#19D3F3",
    "ai_cody": "#FF6692",
    "ai_devin": "#B6E880",
    "ai_gemini": "#ff00e5",
    "ai_windsurf": "#f0e130",
    "ai_other": "#666688",
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


def apply_dark_layout(fig):
    """Apply cyberpunk dark theme to a Plotly figure."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Courier New, monospace", color="#e0e0ff"),
    )
    return fig
