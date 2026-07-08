import random
import time

import pandas  # noqa: F401  # eager: force a clean pandas import at startup so
# plotly's lazy pd.Series check never triggers a first-time import mid hot-reload
# (which surfaces as "partially initialized module 'pandas'").
import streamlit as st

from chart import build_radar, build_team_radar, pretty
from models import (
    CATEGORIES,
    GOALKEEPER,
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
from match_engine import generate_match
from simulation import MAX_GOALS, SimParams, simulate
from team import (
    Placement,
    TeamDoc,
    position_mean_fits,
    team_validation_errors,
)

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

    st.plotly_chart(build_radar(players, selected, view), width="stretch")

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
        "Fit normalizes by their sum. Higher = matters more; 0 = no impact."
    )

    weights = load_position_weights()
    position = st.selectbox("Position", POSITIONS, format_func=pretty)
    current = weights[position]

    with st.form("edit_weights", clear_on_submit=False):
        new_weights: dict[str, float] = {}
        for category, stats in CATEGORIES.items():
            st.markdown(f"**{pretty(category)}**")
            cols = st.columns(len(stats))
            for col, stat in zip(cols, stats):
                new_weights[stat] = col.number_input(
                    pretty(stat),
                    min_value=0.0,
                    step=WEIGHT_STEP,
                    value=float(current.get(stat, 0.0)),
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


def _random_team_doc(names: list[str]) -> TeamDoc:
    """A valid random team: slot 1 the sole Goalkeeper, the rest random outfield."""
    picks = random.sample(names, TEAM_SIZE)
    outfield = [p for p in POSITIONS if p != GOALKEEPER]
    placements = [Placement(character=picks[0], position=GOALKEEPER)]
    placements += [
        Placement(character=c, position=random.choice(outfield)) for c in picks[1:]
    ]
    return TeamDoc(name="Random XI", placements=placements)


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

    # Buttons that write slot/name session_state must run before those widgets
    # are instantiated this run (Streamlit forbids setting a widget's key after).
    col_clear, col_random = st.columns(2)
    if col_clear.button("Clear team"):
        for i in range(TEAM_SIZE):
            st.session_state.pop(f"slot_{i}_char", None)
            st.session_state.pop(f"slot_{i}_pos", None)
        st.session_state.pop("team_name", None)
        st.rerun()
    if col_random.button("Random All", type="primary"):
        _apply_team_doc(_random_team_doc(names))

    st.text_input("Team name", key="team_name")

    weights = load_position_weights()
    default_pos = POSITIONS.index("midfield")
    header = st.container()  # tally + validity, filled in after the slots

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


def _load_team_input(container, label: str, key: str,
                     known: set[str]) -> TeamDoc | None:
    text = container.text_area(f"{label} JSON", key=key, height=170)
    if not text.strip():
        container.info(f"Paste {label} (copy it from the Team Builder's Export).")
        return None
    try:
        doc = TeamDoc.model_validate_json(text)
    except ValueError as exc:
        container.error(f"{label}: could not parse JSON — {exc}")
        return None
    errors = team_validation_errors(doc, known)
    if errors:
        container.error(f"{label} invalid — " + "; ".join(errors))
        return None
    return doc


def compare_teams_page(players: dict[str, Player]) -> None:
    st.title("Ultimate XI — Team vs Team")
    st.caption("Per-Position mean Fit breakdown, then the match simulation for the "
               "verdict. Paste two complete teams.")

    known = set(players)
    weights = load_position_weights()

    col_a, col_b = st.columns(2)
    doc_a = _load_team_input(col_a, "Team A", "compare_a", known)
    doc_b = _load_team_input(col_b, "Team B", "compare_b", known)
    if doc_a is None or doc_b is None:
        return

    label_a = f"A · {doc_a.name}" if doc_a.name else "Team A"
    label_b = f"B · {doc_b.name}" if doc_b.name else "Team B"
    means_a = position_mean_fits(doc_a, players, weights)
    means_b = position_mean_fits(doc_b, players, weights)

    st.plotly_chart(build_team_radar({label_a: means_a, label_b: means_b}),
                    width="stretch")

    rows = [
        {"Position": pretty(pos), label_a: round(means_a[pos], 2),
         label_b: round(means_b[pos], 2),
         "Diff": round(means_a[pos] - means_b[pos], 2)}
        for pos in POSITIONS
    ]
    st.table(rows)

    _simulation_section(doc_a, doc_b, players, weights, label_a, label_b)


def _simulation_section(doc_a, doc_b, players, weights, label_a, label_b) -> None:
    st.subheader("Match simulation")
    st.caption("Attack (fed by Midfield) vs the opponent's Defence + Goalkeeper "
               "→ expected goals → outcome. Tune the sliders to taste.")

    params = SimParams()
    with st.expander("Simulation settings"):
        params.base_xg = st.slider("Base expected goals", 0.5, 3.0,
                                   params.base_xg, 0.05)
        params.slope = st.slider("Attack sensitivity", 0.1, 1.5,
                                 params.slope, 0.05)
        params.midfield_supply_weight = st.slider(
            "Midfield supply to attack", 0.0, 1.0, params.midfield_supply_weight, 0.05)
        params.goalkeeper_weight = st.slider("Goalkeeper share of resistance",
                                            0.0, 1.5, params.goalkeeper_weight, 0.05)
        params.chemistry_per_link = st.slider("Chemistry boost per link-up", 0.0, 0.2,
                                             params.chemistry_per_link, 0.01)

    result = simulate(doc_a, doc_b, players, weights, params)

    c1, c2 = st.columns(2)
    c1.metric(f"{label_a} — xG", f"{result.xg_a:.2f}")
    c2.metric(f"{label_b} — xG", f"{result.xg_b:.2f}")
    c1.metric("Win / Draw / Loss",
              f"{result.p_a_win:.0%} / {result.p_draw:.0%} / {result.p_b_win:.0%}")
    c2.metric("Win / Draw / Loss",
              f"{result.p_b_win:.0%} / {result.p_draw:.0%} / {result.p_a_win:.0%}")
    c1.metric("Expected points", f"{result.xpoints_a:.2f}")
    c2.metric("Expected points", f"{result.xpoints_b:.2f}")

    st.markdown(
        f"**Most likely score:** {label_a} {result.likely_score[0]}"
        f"–{result.likely_score[1]} {label_b}"
    )
    st.caption(
        f"Attack/Resistance — {label_a}: {result.a.attack:.2f}/{result.a.resistance:.2f} "
        f"({result.a.chemistry_links} link-ups) · "
        f"{label_b}: {result.b.attack:.2f}/{result.b.resistance:.2f} "
        f"({result.b.chemistry_links} link-ups)"
    )

    _live_match_section(doc_a, doc_b, players, label_a, label_b, result)
    _maths_expander(params)


def _live_match_section(doc_a, doc_b, players, label_a, label_b, result) -> None:
    st.subheader("Live match")
    st.caption("Plays one sampled 90-minute match consistent with the xG above — "
               "same model, one realised outcome. Purely for flavour, not a forecast.")

    speed = st.select_slider("Speed", options=["Slow", "Normal", "Fast", "Instant"],
                             value="Normal", key="live_speed")
    delay = {"Slow": 0.2, "Normal": 0.08, "Fast": 0.02, "Instant": 0.0}[speed]

    if st.button("Kick off ⚽", key="kickoff_btn"):
        timeline = generate_match(doc_a, doc_b, players, result.a, result.b,
                                  result.xg_a, result.xg_b)
        _play_match(timeline, label_a, label_b, delay)


def _play_match(timeline, label_a: str, label_b: str, delay: float) -> None:
    clock_ph = st.empty()
    score_ph = st.empty()
    poss_ph = st.empty()
    stats_ph = st.empty()
    log_ph = st.empty()

    log_lines: list[str] = []
    for state in timeline:
        for ev in state.events:
            log_lines.append(f"**{ev.minute}'** {ev.text}")

        clock_ph.markdown(f"### ⏱️ {state.minute}'")
        score_ph.markdown(f"## {label_a} **{state.score_a}** – **{state.score_b}** {label_b}")

        poss_a = state.possession_a
        with poss_ph.container():
            st.caption(f"Possession — {label_a} {poss_a:.0f}% · "
                      f"{label_b} {100 - poss_a:.0f}%")
            st.progress(poss_a / 100)

        with stats_ph.container():
            c1, c2, c3, c4 = st.columns(4)
            c1.metric(f"{label_a} shots", state.shots_a)
            c2.metric(f"{label_b} shots", state.shots_b)
            c3.metric(f"{label_a} passes", state.passes_a)
            c4.metric(f"{label_b} passes", state.passes_b)

        log_ph.markdown("\n\n".join(reversed(log_lines[-8:])))

        if delay:
            time.sleep(delay)


def _maths_expander(params: SimParams) -> None:
    """The exact formulas behind xG and W/D/L, with the current coefficients."""
    with st.expander("Show the maths (LaTeX)"):
        st.markdown(
            r"$\overline{F}_{p}$ = mean positional Fit of a team's line $p$ "
            r"(goalkeeper, defence, midfield, attack); $L$ = co-placed link-up pairs."
        )

        st.markdown("**1. Attack rating** — attack line, supplied by midfield, boosted by chemistry:")
        st.latex(
            r"\text{Att} = \frac{w_a\,\overline{F}_{att} + w_{ms}\,\overline{F}_{mid}}"
            r"{w_a + w_{ms}}\;\bigl(1 + c\,L\bigr)"
        )

        st.markdown("**2. Resistance** — defence + goalkeeper, shielded by midfield:")
        st.latex(
            r"\text{Res} = \frac{w_d\,\overline{F}_{def} + w_g\,\overline{F}_{gk}"
            r" + w_{sh}\,\overline{F}_{mid}}{w_d + w_g + w_{sh}}"
        )

        st.markdown("**3. Expected goals** — each team's attack vs the other's resistance:")
        st.latex(
            r"xG_A = \max\!\bigl(f,\; b + s\,(\text{Att}_A - \text{Res}_B)\bigr)"
            r" \qquad "
            r"xG_B = \max\!\bigl(f,\; b + s\,(\text{Att}_B - \text{Res}_A)\bigr)"
        )

        st.markdown(r"**4. Goals are Poisson** with mean $\lambda = xG$:")
        st.latex(r"P(k) = \frac{\lambda^{k} e^{-\lambda}}{k!}")

        st.markdown(
            f"**5. Outcome** — sum over the score grid $i,j \\in [0,{MAX_GOALS}]$:"
        )
        st.latex(
            r"P(\text{A win}) = \sum_{i>j} P_A(i)\,P_B(j)"
            r" \qquad "
            r"P(\text{draw}) = \sum_{i=j} P_A(i)\,P_B(j)"
            r" \qquad "
            r"P(\text{B win}) = \sum_{i<j} P_A(i)\,P_B(j)"
        )

        st.markdown("**6. Expected points** and most likely score:")
        st.latex(
            r"xP_A = 3\,P(\text{A win}) + P(\text{draw})"
            r" \qquad "
            r"(\hat{i},\hat{j}) = \arg\max_{i,j} P_A(i)\,P_B(j)"
        )

        st.caption("Current coefficients (from the sliders / SimParams):")
        st.latex(
            rf"w_a={params.attack_weight:g},\; w_{{ms}}={params.midfield_supply_weight:g},\;"
            rf"w_d={params.defence_weight:g},\; w_g={params.goalkeeper_weight:g},\;"
            rf"w_{{sh}}={params.midfield_shield_weight:g},\;"
            rf"b={params.base_xg:g},\; s={params.slope:g},\;"
            rf"f={params.xg_floor:g},\; c={params.chemistry_per_link:g}"
        )
        st.markdown(
            "| Symbol | Meaning |\n"
            "|---|---|\n"
            r"| $w_a$ | attack line's weight in the Attack rating |" "\n"
            r"| $w_{ms}$ | midfield's supply weight into the Attack rating |" "\n"
            r"| $w_d$ | defence's weight in Resistance |" "\n"
            r"| $w_g$ | goalkeeper's weight in Resistance |" "\n"
            r"| $w_{sh}$ | midfield's shielding weight in Resistance |" "\n"
            r"| $b$ | base expected goals for an evenly-matched game |" "\n"
            r"| $s$ | slope: how hard an Attack−Resistance gap swings xG |" "\n"
            r"| $f$ | xG floor (there's always a chance) |" "\n"
            r"| $c$ | chemistry boost to attack per co-placed link-up pair |" "\n"
            r"| $L$ | count of those link-up pairs in the creative lines |" "\n"
            r"| $\overline{F}_p$ | mean positional Fit of line $p$ |"
        )


def _view_metrics(view: str) -> dict[str, callable]:
    """Metric label → function(Player) -> float for a Players view.

    Overall shows the global Overall plus each category average (like the
    radar's Overall); a category shows just that category's stats.
    """
    if view == OVERALL_VIEW:
        metrics: dict[str, callable] = {"Overall": lambda p: p.overall}
        for cat in CATEGORIES:
            metrics[f"{pretty(cat)}-Overall"] = lambda p, c=cat: p.category_overall(c)
        return metrics
    return {pretty(stat): (lambda p, s=stat: getattr(p, s)) for stat in CATEGORIES[view]}


def players_page(players: dict[str, Player]) -> None:
    st.title("Ultimate XI — Players")
    st.caption("Every player ranked. Pick a view: Overall shows category "
               "averages, a category shows its individual stats.")

    view_options = [OVERALL_VIEW] + [pretty(c) for c in CATEGORIES]
    label_to_key = {pretty(c): c for c in CATEGORIES}

    view_label = st.selectbox("View", view_options)
    view = OVERALL_VIEW if view_label == OVERALL_VIEW else label_to_key[view_label]
    st.caption("Click a column header to sort.")

    metrics = _view_metrics(view)
    headline = next(iter(metrics.values()))
    ranked = sorted(players.values(), key=headline, reverse=True)

    rows = []
    for player in ranked:
        row = {"Player": pretty(player.name)}
        for label, fn in metrics.items():
            row[label] = round(fn(player), 2)
        rows.append(row)

    st.dataframe(rows, width="stretch", hide_index=True)


def main() -> None:
    st.set_page_config(page_title="Ultimate XI", layout="wide")
    players = load_players()

    with st.sidebar:
        page = st.radio(
            "Page",
            ["Compare", "Players", "Team builder", "Team vs Team",
             "Edit ratings", "Edit weights"],
            index=0,
        )

    if page == "Compare":
        compare_page(players)
    elif page == "Players":
        players_page(players)
    elif page == "Team builder":
        team_builder_page(players)
    elif page == "Team vs Team":
        compare_teams_page(players)
    elif page == "Edit ratings":
        edit_page(players)
    else:
        weights_page()


if __name__ == "__main__":
    main()
