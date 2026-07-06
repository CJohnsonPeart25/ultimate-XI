import plotly.graph_objects as go

from models import MAX_RATING, POSITIONS, Player, view_axis_keys

# Distinct hues; each player gets one, with a translucent fill for the FIFA look.
PALETTE = [
    "#e6194B", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
    "#42d4f4", "#f032e6", "#bfef45", "#fabed4", "#469990",
    "#dcbeff", "#9A6324", "#800000", "#808000", "#000075",
]


def pretty(name: str) -> str:
    return name.replace("_", " ").title()


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def build_radar(players: dict[str, Player], selected: list[str],
                view: str) -> go.Figure:
    axis_labels = [pretty(key) for key in view_axis_keys(view)]
    closed_labels = axis_labels + axis_labels[:1]  # repeat first axis to close polygon

    fig = go.Figure()
    for i, name in enumerate(selected):
        values = players[name].axis_values(view)
        values = values + values[:1]
        color = PALETTE[i % len(PALETTE)]
        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=closed_labels,
                fill="toself",
                name=pretty(name),
                line=dict(color=color, width=2),
                fillcolor=_rgba(color, 0.25),
                hovertemplate="%{theta}: %{r:.2f}<extra>" + name + "</extra>",
            )
        )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, MAX_RATING])),
        showlegend=True,
        height=600,
        margin=dict(l=60, r=60, t=40, b=40),
    )
    return fig


def build_team_radar(team_series: dict[str, dict[str, float]]) -> go.Figure:
    """Overlay Teams on the four Position axes; each value is a mean Fit."""
    axis_labels = [pretty(pos) for pos in POSITIONS]
    closed_labels = axis_labels + axis_labels[:1]

    fig = go.Figure()
    for i, (label, scores) in enumerate(team_series.items()):
        values = [scores[pos] for pos in POSITIONS]
        values = values + values[:1]
        color = PALETTE[i % len(PALETTE)]
        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=closed_labels,
                fill="toself",
                name=label,
                line=dict(color=color, width=2),
                fillcolor=_rgba(color, 0.25),
                hovertemplate="%{theta}: %{r:.2f}<extra>" + label + "</extra>",
            )
        )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, MAX_RATING])),
        showlegend=True,
        height=520,
        margin=dict(l=60, r=60, t=40, b=40),
    )
    return fig
