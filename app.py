import streamlit as st

from chart import build_radar, pretty
from models import (
    CATEGORIES,
    MAX_RATING,
    OVERALL_VIEW,
    POSITIONS,
    TEAM_SIZE,
    Player,
    load_players,
    load_position_weights,
    team_issues,
    team_tally,
    update_player,
    update_position_weights,
)
from team import Placement, TeamDoc, team_validation_errors

RATING_STEP = 0.5
WEIGHT_STEP = 0.5
EMPTY_SLOT = "— empty —"


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


def _apply_team_doc(doc: TeamDoc) -> None:
    """Load an imported Team into the builder's slot widgets, then rerun."""
    for i in range(TEAM_SIZE):
        if i < len(doc.placements):
            st.session_state[f"slot_{i}_char"] = doc.placements[i].character
            st.session_state[f"slot_{i}_pos"] = doc.placements[i].position
        else:
            st.session_state.pop(f"slot_{i}_char", None)
            st.session_state.pop(f"slot_{i}_pos", None)
    st.session_state["team_name"] = doc.name
    st.rerun()


def team_builder_page(players: dict[str, Player]) -> None:
    st.title("Ultimate XI — Team Builder")
    st.caption("Fill 11 slots. Assign each a Position. Exactly one Goalkeeper. "
               "A Character can only appear once.")

    names = sorted(players.keys())

    # Import must run before the slot/name widgets are instantiated this run.
    with st.expander("Import a team (paste JSON)"):
        pasted = st.text_area("Team JSON", key="team_paste", height=150)
        if st.button("Load team") and pasted.strip():
            try:
                doc = TeamDoc.model_validate_json(pasted)
            except ValueError as exc:
                st.error(f"Could not parse JSON: {exc}")
            else:
                errors = team_validation_errors(doc, set(names))
                if errors:
                    st.error("Invalid team — " + "; ".join(errors))
                else:
                    _apply_team_doc(doc)

    st.text_input("Team name", key="team_name")

    weights = load_position_weights()
    default_pos = POSITIONS.index("midfield")
    header = st.container()  # tally + validity, filled in after the slots

    if st.button("Clear team"):
        for i in range(TEAM_SIZE):
            st.session_state.pop(f"slot_{i}_char", None)
            st.session_state.pop(f"slot_{i}_pos", None)
        st.rerun()

    chosen = [st.session_state.get(f"slot_{i}_char", EMPTY_SLOT) for i in range(TEAM_SIZE)]
    placements: list[tuple[str, str]] = []
    for i in range(TEAM_SIZE):
        taken_elsewhere = {chosen[j] for j in range(TEAM_SIZE) if j != i} - {EMPTY_SLOT}
        options = [EMPTY_SLOT] + [n for n in names if n not in taken_elsewhere]
        c_char, c_pos, c_fit = st.columns([3, 2, 2])
        char = c_char.selectbox(
            f"Slot {i + 1}", options, key=f"slot_{i}_char",
            format_func=lambda n: n if n == EMPTY_SLOT else pretty(n),
        )
        pos = c_pos.selectbox(
            "Position", POSITIONS, index=default_pos, key=f"slot_{i}_pos",
            format_func=pretty,
        )
        if char != EMPTY_SLOT:
            placements.append((char, pos))
            c_fit.metric("Fit", f"{players[char].fit(weights[pos]):.2f}")

    positions = [pos for _, pos in placements]
    tally = team_tally(positions)
    issues = team_issues(positions)
    with header:
        st.markdown(" · ".join(
            f"**{pretty(pos)[:3]}** {tally[pos]}" for pos in POSITIONS
        ))
        if issues:
            st.warning("Not complete — " + "; ".join(issues))
        else:
            st.success("Complete team ✓")

    if placements:
        doc = TeamDoc(
            name=st.session_state.get("team_name", ""),
            placements=[Placement(character=c, position=p) for c, p in placements],
        )
        st.markdown("**Export** — copy this JSON to share or save:")
        st.code(doc.model_dump_json(indent=2), language="json")


def main() -> None:
    st.set_page_config(page_title="Ultimate XI", layout="wide")
    players = load_players()

    with st.sidebar:
        page = st.radio(
            "Page",
            ["Compare", "Team builder", "Edit ratings", "Edit weights"],
            index=0,
        )

    if page == "Compare":
        compare_page(players)
    elif page == "Team builder":
        team_builder_page(players)
    elif page == "Edit ratings":
        edit_page(players)
    else:
        weights_page()


if __name__ == "__main__":
    main()
