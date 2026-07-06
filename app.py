import plotly.graph_objects as go
import streamlit as st

from models import (
    CATEGORIES,
    OVERALL_VIEW,
    Player,
    load_players,
    update_player,
    view_axis_keys,
)

MAX_RATING = 5.0
RATING_STEP = 0.5

# Distinct hues; each player gets one, with a translucent fill for the FIFA look.
PALETTE = [
    "#e6194B", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
    "#42d4f4", "#f032e6", "#bfef45", "#fabed4", "#469990",
    "#dcbeff", "#9A6324", "#800000", "#808000", "#000075",
]


def pretty(name: str) -> str:
    return name.replace("_", " ").title()


def rgba(hex_color: str, alpha: float) -> str:
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
                name=name.replace("_", " ").title(),
                line=dict(color=color, width=2),
                fillcolor=rgba(color, 0.25),
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


def compare_page(players: dict[str, Player]) -> None:
    st.title("Ultimate XI — Stat Comparison")
    view_options = [OVERALL_VIEW] + [pretty(c) for c in CATEGORIES]
    label_to_key = {pretty(c): c for c in CATEGORIES}

    with st.sidebar:
        selected = st.multiselect(
            "Characters",
            options=sorted(players.keys()),
            default=["mario", "bowser"],
            format_func=pretty,
        )
        view_label = st.radio("Stat view", view_options, index=0)

    view = OVERALL_VIEW if view_label == OVERALL_VIEW else label_to_key[view_label]

    if not selected:
        st.info("Pick at least one character in the sidebar to compare.")
        return

    st.plotly_chart(build_radar(players, selected, view),
                    use_container_width=True)

    st.subheader("Ratings")
    cols = st.columns(len(selected))
    for col, name in zip(cols, selected):
        player = players[name]
        with col:
            st.markdown(f"**{pretty(name)}**")
            st.metric("Overall", f"{player.overall:.2f}")
            for cat in CATEGORIES:
                st.caption(f"{pretty(cat)}-Overall: {player.category_overall(cat):.2f}")


def edit_page(players: dict[str, Player]) -> None:
    st.title("Ultimate XI — Edit Ratings")

    names = sorted(players.keys())
    name = st.selectbox("Player to edit", names, format_func=pretty)
    player = players[name]

    with st.form("edit_player", clear_on_submit=False):
        new_values: dict[str, float] = {}
        for category, stats in CATEGORIES.items():
            st.markdown(f"**{pretty(category)}**")
            cols = st.columns(len(stats))
            for col, stat in zip(cols, stats):
                new_values[stat] = col.number_input(
                    pretty(stat),
                    min_value=0.0,
                    max_value=MAX_RATING,
                    step=RATING_STEP,
                    value=float(getattr(player, stat)),
                    key=f"edit_{stat}",
                )

        partners = st.multiselect(
            "Link-up partners",
            options=[n for n in names if n != name],
            default=[p for p in player.link_up_partners if p in names],
            format_func=pretty,
        )
        submitted = st.form_submit_button("Save", type="primary")

    if submitted:
        update_player(name, new_values, partners)
        st.success(f"Saved ratings for {pretty(name)}.")


def main() -> None:
    st.set_page_config(page_title="Ultimate XI", layout="wide")
    players = load_players()

    with st.sidebar:
        page = st.radio("Page", ["Compare", "Edit ratings"], index=0)

    if page == "Compare":
        compare_page(players)
    else:
        edit_page(players)


if __name__ == "__main__":
    main()
