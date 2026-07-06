import pytest

from models import STAT_FIELDS, Player
from simulation import (
    SimParams,
    chemistry_links,
    expected_goals,
    outcome_probabilities,
    simulate,
)
from team import Placement, TeamDoc

PARAMS = SimParams()
WEIGHTS = {pos: {"pace": 1.0} for pos in
           ["goalkeeper", "defence", "midfield", "attack"]}


def _player(name: str, value: float, partners: list[str] | None = None) -> Player:
    values = {stat: value for stat in STAT_FIELDS}
    return Player(name=name, link_up_partners=partners or [], **values)


def _team(assignments: list[tuple[str, str]]) -> TeamDoc:
    return TeamDoc(placements=[Placement(character=c, position=p)
                              for c, p in assignments])


def _flat_players(assignments, value=3.0, partners=None):
    partners = partners or {}
    return {c: _player(c, value, partners.get(c, [])) for c, _ in assignments}


def test_expected_goals_has_floor_and_rises_with_dominance():
    assert expected_goals(0.0, 5.0, PARAMS) == pytest.approx(PARAMS.xg_floor)
    weak = expected_goals(2.0, 2.0, PARAMS)
    strong = expected_goals(4.5, 1.0, PARAMS)
    assert strong > weak


def test_outcome_probabilities_sum_to_one_and_are_symmetric():
    probs = outcome_probabilities(1.5, 1.5)
    # Truncating the Poisson tail at MAX_GOALS loses a negligible sliver of mass.
    assert probs["p_a_win"] + probs["p_draw"] + probs["p_b_win"] == pytest.approx(1.0, abs=1e-3)
    assert probs["p_a_win"] == pytest.approx(probs["p_b_win"])
    assert probs["p_draw"] > 0


def test_higher_xg_wins_more_often():
    probs = outcome_probabilities(2.5, 0.5)
    assert probs["p_a_win"] > probs["p_b_win"]


def test_chemistry_counts_only_creative_coplaced_pairs():
    assignments = [("a", "attack"), ("b", "midfield"), ("c", "defence")]
    # a<->b are partners and both creative; a<->c partners but c is a defender.
    players = _flat_players(assignments, partners={"a": ["b", "c"]})
    assert chemistry_links(_team(assignments), players) == 1


def test_ten_in_attack_loses_to_balanced_without_a_rule():
    balanced = [("gk", "goalkeeper")] + [("d%d" % i, "defence") for i in range(4)] \
        + [("m%d" % i, "midfield") for i in range(4)] + [("f0", "attack"), ("f1", "attack")]
    stacked = [("gk", "goalkeeper")] + [("x%d" % i, "attack") for i in range(10)]

    # Everyone equally rated at 4.0, so only the shape differs.
    players = {}
    for c, _ in balanced + stacked:
        players.setdefault(c, _player(c, 4.0))

    result = simulate(_team(balanced), _team(stacked), players, WEIGHTS, PARAMS)
    # The stacked team has empty defence/midfield -> low resistance -> concedes more.
    assert result.xg_a > result.xg_b
    assert result.p_a_win > result.p_b_win
