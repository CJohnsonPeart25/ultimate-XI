"""Minute-by-minute live match playback, built on top of the xG simulation.

simulate() gives each team a final xG and win/draw/loss verdict but no sense
of *when* things happen. This module spreads that same xG across 90 minutes
as a Poisson process (plus shots, possession and passes derived from the
same Attack/Resistance ratings) so the Team vs Team page can play the match
out like a basic football-manager live tracker.
"""
import random
from dataclasses import dataclass, field

from simulation import TeamStrength

FULL_TIME = 90
HALF_TIME = 45
SHOTS_PER_GOAL = 5.5  # flavour only: shots fire ~5.5x as often as goals


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


def _scorer(doc, players, rng: random.Random) -> str:
    """Pick a plausible name for a goal/chance: attack line first, then anyone outfield."""
    attackers = [p.character for p in doc.placements if p.position == "attack"]
    pool = attackers or [p.character for p in doc.placements if p.position != "goalkeeper"]
    if not pool:
        return doc.name or "Unknown"
    return players[rng.choice(pool)].name


def generate_match(doc_a, doc_b, players: dict, a: TeamStrength, b: TeamStrength,
                    xg_a: float, xg_b: float, seed: int | None = None) -> list[MinuteState]:
    """Build the full 90-minute timeline as a list of per-minute snapshots."""
    rng = random.Random(seed)
    goal_rate_a, goal_rate_b = xg_a / FULL_TIME, xg_b / FULL_TIME
    shot_rate_a, shot_rate_b = goal_rate_a * SHOTS_PER_GOAL, goal_rate_b * SHOTS_PER_GOAL

    # Possession tilts with the gap in Attack rating, then drifts minute to minute.
    base_possession_a = 50 + (a.attack - b.attack) * 12
    possession_a = min(80.0, max(20.0, base_possession_a))

    score_a = score_b = 0
    passes_a = passes_b = 0
    timeline: list[MinuteState] = []

    kickoff = MatchEvent(0, "kickoff", None, "Kick-off!")
    for minute in range(1, FULL_TIME + 1):
        events: list[MatchEvent] = [kickoff] if minute == 1 else []

        possession_a += rng.uniform(-3.0, 3.0)
        possession_a = min(80.0, max(20.0, possession_a))
        passes_a += round(rng.uniform(6, 10) * (possession_a / 50))
        passes_b += round(rng.uniform(6, 10) * ((100 - possession_a) / 50))

        if rng.random() < shot_rate_a:
            if rng.random() < goal_rate_a / shot_rate_a:
                score_a += 1
                events.append(MatchEvent(minute, "goal", "a",
                                          f"GOAL! {_scorer(doc_a, players, rng)} scores for "
                                          f"{doc_a.name or 'Team A'}!"))
            else:
                events.append(MatchEvent(minute, "chance", "a",
                                          f"Chance for {_scorer(doc_a, players, rng)} — saved!"))
        if rng.random() < shot_rate_b:
            if rng.random() < goal_rate_b / shot_rate_b:
                score_b += 1
                events.append(MatchEvent(minute, "goal", "b",
                                          f"GOAL! {_scorer(doc_b, players, rng)} scores for "
                                          f"{doc_b.name or 'Team B'}!"))
            else:
                events.append(MatchEvent(minute, "chance", "b",
                                          f"Chance for {_scorer(doc_b, players, rng)} — saved!"))

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
