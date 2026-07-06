"""Matchup-based match simulation (issues 005/006/007).

A Team's Attack (fed by Midfield) is tested against the opponent's Defence +
Goalkeeper to produce expected goals; a Poisson model turns the two xG numbers
into outcome probabilities and a likely scoreline. link_up_partners placed in the
creative lines add a chemistry boost. Formation balance is emergent: an empty
Defence simply concedes more, no fairness rule needed.

All coefficients live in SimParams so they can be surfaced as sliders. Defaults
are a first-pass calibration (see docs/research/simulation-design-decisions.md).
"""
from dataclasses import dataclass
from math import exp, factorial

from models import POSITIONS, Player
from team import TeamDoc, position_mean_fits

CREATIVE_POSITIONS = {"midfield", "attack"}
MAX_GOALS = 10


@dataclass
class SimParams:
    # Attack rating = attack line, supplied by midfield.
    attack_weight: float = 1.0
    midfield_supply_weight: float = 0.5
    # Defensive resistance = defence, goalkeeper, shielded by midfield.
    defence_weight: float = 1.0
    goalkeeper_weight: float = 0.6
    midfield_shield_weight: float = 0.4
    # Strength (0-5 difference) -> expected goals.
    base_xg: float = 1.3
    slope: float = 0.55
    xg_floor: float = 0.05
    # Each co-placed link_up_partners pair in the creative lines boosts attack.
    chemistry_per_link: float = 0.05


@dataclass
class TeamStrength:
    attack: float
    resistance: float
    chemistry_links: int


@dataclass
class SimResult:
    a: TeamStrength
    b: TeamStrength
    xg_a: float
    xg_b: float
    p_a_win: float
    p_draw: float
    p_b_win: float
    likely_score: tuple[int, int]
    xpoints_a: float
    xpoints_b: float


def chemistry_links(doc: TeamDoc, players: dict[str, Player]) -> int:
    """Count unique link_up_partner pairs both placed in the creative lines."""
    creative = {p.character for p in doc.placements
                if p.position in CREATIVE_POSITIONS}
    seen: set[frozenset[str]] = set()
    for character in creative:
        for partner in players[character].link_up_partners:
            if partner in creative:
                seen.add(frozenset((character, partner)))
    return len(seen)


def team_strength(doc: TeamDoc, players: dict[str, Player],
                  weights: dict[str, dict[str, float]],
                  params: SimParams) -> TeamStrength:
    means = position_mean_fits(doc, players, weights)
    links = chemistry_links(doc, players)

    attack_w = params.attack_weight + params.midfield_supply_weight
    attack = (means["attack"] * params.attack_weight
              + means["midfield"] * params.midfield_supply_weight) / attack_w
    attack *= 1 + params.chemistry_per_link * links

    res_w = (params.defence_weight + params.goalkeeper_weight
             + params.midfield_shield_weight)
    resistance = (means["defence"] * params.defence_weight
                  + means["goalkeeper"] * params.goalkeeper_weight
                  + means["midfield"] * params.midfield_shield_weight) / res_w

    return TeamStrength(attack=attack, resistance=resistance, chemistry_links=links)


def expected_goals(attack: float, resistance: float, params: SimParams) -> float:
    return max(params.xg_floor, params.base_xg + params.slope * (attack - resistance))


def _poisson_pmf(k: int, lam: float) -> float:
    return lam ** k * exp(-lam) / factorial(k)


def outcome_probabilities(xg_a: float, xg_b: float,
                          max_goals: int = MAX_GOALS) -> dict:
    """P(win/draw/loss), likely scoreline and expected points from two xG values."""
    pmf_a = [_poisson_pmf(k, xg_a) for k in range(max_goals + 1)]
    pmf_b = [_poisson_pmf(k, xg_b) for k in range(max_goals + 1)]

    p_a = p_draw = p_b = 0.0
    best_p, best_score = -1.0, (0, 0)
    for i, pa in enumerate(pmf_a):
        for j, pb in enumerate(pmf_b):
            p = pa * pb
            if i > j:
                p_a += p
            elif i == j:
                p_draw += p
            else:
                p_b += p
            if p > best_p:
                best_p, best_score = p, (i, j)
    return {
        "p_a_win": p_a, "p_draw": p_draw, "p_b_win": p_b,
        "likely_score": best_score,
        "xpoints_a": 3 * p_a + p_draw, "xpoints_b": 3 * p_b + p_draw,
    }


def simulate(doc_a: TeamDoc, doc_b: TeamDoc, players: dict[str, Player],
             weights: dict[str, dict[str, float]], params: SimParams) -> SimResult:
    a = team_strength(doc_a, players, weights, params)
    b = team_strength(doc_b, players, weights, params)
    xg_a = expected_goals(a.attack, b.resistance, params)
    xg_b = expected_goals(b.attack, a.resistance, params)
    probs = outcome_probabilities(xg_a, xg_b)
    return SimResult(a=a, b=b, xg_a=xg_a, xg_b=xg_b,
                     likely_score=probs["likely_score"],
                     p_a_win=probs["p_a_win"], p_draw=probs["p_draw"],
                     p_b_win=probs["p_b_win"],
                     xpoints_a=probs["xpoints_a"], xpoints_b=probs["xpoints_b"])
