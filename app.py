import streamlit as st

from chart import build_radar, pretty
from models import (
    CATEGORIES,
    MAX_RATING,
    OVERALL_VIEW,
    POSITIONS,
    Player,
    load_players,
    load_position_weights,
    update_player,
    update_position_weights,
)

RATING_STEP = 0.5
WEIGHT_STEP = 0.5


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

    weights = load_position_weights()

    st.subheader("Ratings")
    cols = st.columns(len(selected))
    for col, name in zip(cols, selected):
        player = players[name]
        with col:
            st.markdown(f"**{pretty(name)}**")
            st.metric("Overall", f"{player.overall:.2f}")
            for cat in CATEGORIES:
                st.caption(f"{pretty(cat)}-Overall: {player.category_overall(cat):.2f}")
            fits = " · ".join(
                f"{pretty(pos)[:3]} {player.fit(weights[pos]):.2f}" for pos in POSITIONS
            )
            st.caption(f"Fit — {fits}")


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
                    key=f"edit_{name}_{stat}",
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


def weights_page() -> None:
    st.title("Ultimate XI — Edit Position Weights")
    st.caption(
        "Relative importance of each stat for a Position. Magnitudes are free — "
        "Fit normalizes by their sum. Higher = matters more."
    )

    weights = load_position_weights()
    position = st.selectbox("Position", POSITIONS, format_func=pretty)
    current = weights[position]

    with st.form("edit_weights", clear_on_submit=False):
        new_weights: dict[str, float] = {}
        stats = sorted(current, key=lambda s: current[s], reverse=True)
        cols = st.columns(3)
        for i, stat in enumerate(stats):
            new_weights[stat] = cols[i % 3].number_input(
                pretty(stat),
                min_value=0.0,
                step=WEIGHT_STEP,
                value=float(current[stat]),
                key=f"weight_{position}_{stat}",
            )
        submitted = st.form_submit_button("Save", type="primary")

    if submitted:
        update_position_weights(position, new_weights)
        st.success(f"Saved weights for {pretty(position)}.")


def main() -> None:
    st.set_page_config(page_title="Ultimate XI", layout="wide")
    players = load_players()

    with st.sidebar:
        page = st.radio("Page", ["Compare", "Edit ratings", "Edit weights"], index=0)

    if page == "Compare":
        compare_page(players)
    elif page == "Edit ratings":
        edit_page(players)
    else:
        weights_page()


if __name__ == "__main__":
    main()
