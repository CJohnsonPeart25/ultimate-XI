"""Minute-by-minute live match playback, built on top of the xG simulation.

simulate() gives each team a final xG and win/draw/loss verdict but no sense
of *when* things happen, or *who*. This module spreads that same xG across 90
minutes as a Poisson process, then resolves each shot against the actual
Players involved — who takes it (weighted by shooting/pace/dribbling) and
whether it beats the keeper (shooter's shooting/composure vs keeper's
reflexes/handling) — so the Team vs Team page can play the match out like a
basic football-manager live tracker.
"""
import random
from dataclasses import dataclass, field

from chart import pretty
from models import Player
from simulation import TeamStrength

FULL_TIME = 90
HALF_TIME = 45
SHOTS_PER_GOAL = 5.5  # flavour anchor: shots fire ~5.5x as often as goals


@dataclass
class MatchEvent:
    minute: int
    kind: str  # "kickoff" | "chance" | "goal" | "half-time" | "full-time"
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


def _attacking_pool(doc) -> list[str]:
    attackers = [p.character for p in doc.placements if p.position == "attack"]
    return attackers or [p.character for p in doc.placements if p.position != "goalkeeper"]


def _pick_shooter(doc, players: dict[str, Player], rng: random.Random) -> Player:
    """Weighted by attacking threat, so a team's best finisher gets more shots."""
    pool = _attacking_pool(doc)
    threats = [max(0.1, players[c].shooting * 2 + players[c].pace + players[c].dribbling)
              for c in pool]
    return players[rng.choices(pool, weights=threats)[0]]


def _keeper(doc, players: dict[str, Player]) -> Player | None:
    gks = [p.character for p in doc.placements if p.position == "goalkeeper"]
    return players[gks[0]] if gks else None


def _resolve_shot(minute: int, team: str, doc, opp_doc, players: dict[str, Player],
                  base_conversion: float, rng: random.Random) -> MatchEvent:
    """Pick a shooter, then decide goal vs save from their stats against the keeper's."""
    shooter = _pick_shooter(doc, players, rng)
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


def generate_match(doc_a, doc_b, players: dict[str, Player], a: TeamStrength,
                    b: TeamStrength, xg_a: float, xg_b: float,
                    seed: int | None = None) -> list[MinuteState]:
    """Build the full 90-minute timeline as a list of per-minute snapshots."""
    rng = random.Random(seed)
    goal_rate_a, goal_rate_b = xg_a / FULL_TIME, xg_b / FULL_TIME
    shot_rate_a, shot_rate_b = goal_rate_a * SHOTS_PER_GOAL, goal_rate_b * SHOTS_PER_GOAL
    base_conversion_a, base_conversion_b = 1 / SHOTS_PER_GOAL, 1 / SHOTS_PER_GOAL

    # Possession tilts with the gap in Attack rating, then drifts minute to minute.
    base_possession_a = 50 + (a.attack - b.attack) * 12
    possession_a = _clamp(base_possession_a, 20.0, 80.0)

    score_a = score_b = 0
    passes_a = passes_b = 0
    timeline: list[MinuteState] = []

    kickoff = MatchEvent(0, "kickoff", None, "Kick-off!")
    for minute in range(1, FULL_TIME + 1):
        events: list[MatchEvent] = [kickoff] if minute == 1 else []

        possession_a += rng.uniform(-3.0, 3.0)
        possession_a = _clamp(possession_a, 20.0, 80.0)
        passes_a += round(rng.uniform(6, 10) * (possession_a / 50))
        passes_b += round(rng.uniform(6, 10) * ((100 - possession_a) / 50))

        if rng.random() < shot_rate_a:
            event = _resolve_shot(minute, "a", doc_a, doc_b, players,
                                  base_conversion_a, rng)
            if event.kind == "goal":
                score_a += 1
            events.append(event)
        if rng.random() < shot_rate_b:
            event = _resolve_shot(minute, "b", doc_b, doc_a, players,
                                  base_conversion_b, rng)
            if event.kind == "goal":
                score_b += 1
            events.append(event)

        if minute == HALF_TIME:
            events.append(MatchEvent(minute, "half-time", None, "Half-time."))
        if minute == FULL_TIME:
            events.append(MatchEvent(minute, "full-time", None, "Full-time!"))

        timeline.append(MinuteState(
            minute=minute, score_a=score_a, score_b=score_b,
            possession_a=possession_a, shots_a=0, shots_b=0,
            passes_a=passes_a, passes_b=passes_b, events=events,
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
