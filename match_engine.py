"""Minute-by-minute live match playback, built on top of the xG simulation.

simulate() gives each team a final xG and win/draw/loss verdict but no sense
of *when* things happen, or *who*. This module spreads that same xG across 90
minutes as a Poisson process, then resolves each shot against the actual
Players involved — who takes it (weighted by shooting/pace/dribbling) and
whether it beats the keeper (shooter's shooting/composure vs keeper's
reflexes/handling) — plus corners, throw-ins, fouls and offsides for flavour,
so the Team vs Team page can play the match out like a basic
football-manager live tracker.
"""
import random
from dataclasses import dataclass, field

from chart import pretty
from models import Player
from simulation import TeamStrength

FULL_TIME = 90
HALF_TIME = 45
SHOTS_PER_GOAL = 5.5  # flavour anchor: shots fire ~5.5x as often as goals

# Per-team, per-minute odds of each flavour event firing.
CORNER_RATE = 0.07
THROW_IN_RATE = 0.10
FOUL_RATE = 0.09
OFFSIDE_RATE = 0.03
YELLOW_CARD_BASE = 0.15  # scaled by the fouler's aggression once a foul happens


@dataclass
class MatchEvent:
    minute: int
    kind: str  # "kickoff"|"chance"|"goal"|"corner"|"throw-in"|"foul"|"yellow-card"|
               # "offside"|"half-time"|"full-time"
    team: str | None  # "a" | "b" | None
    text: str


@dataclass
class MinuteState:
    minute: int
    score_a: int
    score_b: int
    possession_a: float  # rolling 0-100, share held by team A
    shots_a: int
    shots_b: int
    passes_a: int
    passes_b: int
    events: list[MatchEvent] = field(default_factory=list)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _outfield(doc, positions: tuple[str, ...] | None = None) -> list[str]:
    """Characters placed in `positions` (or any non-goalkeeper slot as a fallback)."""
    if positions is not None:
        pool = [p.character for p in doc.placements if p.position in positions]
        if pool:
            return pool
    return [p.character for p in doc.placements if p.position != "goalkeeper"]


def _weighted_pick(pool: list[str], players: dict[str, Player], weight_fn,
                   rng: random.Random) -> Player:
    weights = [max(0.1, weight_fn(players[c])) for c in pool]
    return players[rng.choices(pool, weights=weights)[0]]


def _keeper(doc, players: dict[str, Player]) -> Player | None:
    gks = [p.character for p in doc.placements if p.position == "goalkeeper"]
    return players[gks[0]] if gks else None


def _resolve_shot(minute: int, team: str, doc, opp_doc, players: dict[str, Player],
                  base_conversion: float, rng: random.Random) -> MatchEvent:
    """Pick a shooter, then decide goal vs save from their stats against the keeper's."""
    shooter = _weighted_pick(_outfield(doc, ("attack",)), players,
                             lambda p: p.shooting * 2 + p.pace + p.dribbling, rng)
    keeper = _keeper(opp_doc, players)

    conversion = base_conversion
    if keeper is not None:
        finishing = (shooter.shooting + shooter.composure) / 2
        stopping = (keeper.reflexes + keeper.handling) / 2
        conversion *= _clamp(1 + (finishing - stopping) * 0.15, 0.4, 1.8)

    shooter_name = pretty(shooter.name)
    if rng.random() < conversion:
        return MatchEvent(minute, "goal", team,
                          f"GOAL! {shooter_name} scores for {doc.name or 'the team'}!")
    keeper_name = f" by {pretty(keeper.name)}" if keeper is not None else ""
    return MatchEvent(minute, "chance", team,
                      f"Chance for {shooter_name} — saved{keeper_name}!")


def _minor_events(minute: int, team: str, doc, opp_doc, players: dict[str, Player],
                  rng: random.Random) -> list[MatchEvent]:
    """Corners, throw-ins, fouls (with a chance of a yellow) and offsides for one team."""
    events: list[MatchEvent] = []
    team_label = doc.name or ("Team A" if team == "a" else "Team B")

    if rng.random() < CORNER_RATE:
        events.append(MatchEvent(minute, "corner", team, f"Corner for {team_label}."))

    if rng.random() < THROW_IN_RATE:
        events.append(MatchEvent(minute, "throw-in", team, f"Throw-in for {team_label}."))

    if rng.random() < OFFSIDE_RATE:
        attacker = _weighted_pick(_outfield(doc, ("attack",)), players,
                                  lambda p: p.pace, rng)
        events.append(MatchEvent(minute, "offside", team,
                                 f"Offside — {pretty(attacker.name)} was caught out."))

    if rng.random() < FOUL_RATE:
        fouler = _weighted_pick(_outfield(opp_doc, ("defence", "midfield")), players,
                                lambda p: p.aggression * 1.5 + p.tackling, rng)
        victim = _weighted_pick(_outfield(doc, ("attack",)), players,
                                lambda p: p.shooting + p.pace + p.dribbling, rng)
        events.append(MatchEvent(minute, "foul", team,
                                 f"Foul by {pretty(fouler.name)} on {pretty(victim.name)}."))
        if rng.random() < _clamp(YELLOW_CARD_BASE * (fouler.aggression / 3), 0.0, 0.9):
            events.append(MatchEvent(minute, "yellow-card", team,
                                     f"Yellow card for {pretty(fouler.name)}."))

    return events


def generate_match(doc_a, doc_b, players: dict[str, Player], a: TeamStrength,
                    b: TeamStrength, xg_a: float, xg_b: float,
                    seed: int | None = None) -> list[MinuteState]:
    """Build the full 90-minute timeline as a list of per-minute snapshots."""
    rng = random.Random(seed)
    goal_rate_a, goal_rate_b = xg_a / FULL_TIME, xg_b / FULL_TIME
    shot_rate_a, shot_rate_b = goal_rate_a * SHOTS_PER_GOAL, goal_rate_b * SHOTS_PER_GOAL
    base_conversion = 1 / SHOTS_PER_GOAL

    sides = {
        "a": {"doc": doc_a, "opp": doc_b, "shot_rate": shot_rate_a},
        "b": {"doc": doc_b, "opp": doc_a, "shot_rate": shot_rate_b},
    }

    # Possession tilts with the gap in Attack rating, then drifts minute to minute.
    base_possession_a = 50 + (a.attack - b.attack) * 12
    possession_a = _clamp(base_possession_a, 20.0, 80.0)

    score = {"a": 0, "b": 0}
    passes = {"a": 0, "b": 0}
    timeline: list[MinuteState] = []

    kickoff = MatchEvent(0, "kickoff", None, "Kick-off!")
    for minute in range(1, FULL_TIME + 1):
        events: list[MatchEvent] = [kickoff] if minute == 1 else []

        possession_a += rng.uniform(-3.0, 3.0)
        possession_a = _clamp(possession_a, 20.0, 80.0)
        passes["a"] += round(rng.uniform(6, 10) * (possession_a / 50))
        passes["b"] += round(rng.uniform(6, 10) * ((100 - possession_a) / 50))

        for team, side in sides.items():
            if rng.random() < side["shot_rate"]:
                event = _resolve_shot(minute, team, side["doc"], side["opp"], players,
                                      base_conversion, rng)
                if event.kind == "goal":
                    score[team] += 1
                events.append(event)
            events.extend(_minor_events(minute, team, side["doc"], side["opp"],
                                        players, rng))

        if minute == HALF_TIME:
            events.append(MatchEvent(minute, "half-time", None, "Half-time."))
        if minute == FULL_TIME:
            events.append(MatchEvent(minute, "full-time", None, "Full-time!"))

        timeline.append(MinuteState(
            minute=minute, score_a=score["a"], score_b=score["b"],
            possession_a=possession_a, shots_a=0, shots_b=0,
            passes_a=passes["a"], passes_b=passes["b"], events=events,
        ))

    # Backfill cumulative shot counts (kept separate from the event loop above
    # for clarity: shots = chances + goals for that team, running total).
    shots_a = shots_b = 0
    for state in timeline:
        for ev in state.events:
            if ev.kind in ("goal", "chance") and ev.team == "a":
                shots_a += 1
            elif ev.kind in ("goal", "chance") and ev.team == "b":
                shots_b += 1
        state.shots_a, state.shots_b = shots_a, shots_b

    return timeline
