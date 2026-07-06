# EPIC: Team-vs-team comparison → match simulation

Type: Epic

## Goal

Let a user load two complete Teams and get a meaningful verdict on which is
stronger — evolving from a cheap static baseline to a matchup-based expected-goals
model, and ultimately (deferred) a stochastic match engine. Fairness for lopsided
Teams (e.g. "10 in attack") should **emerge** from the model rather than be imposed
by a rule.

Full analysis, alternatives, and real-game grounding (EA FC, Football Manager,
Hattrick, Dixon–Coles/Poisson, OOTP) in
[docs/research/team-comparison-methods.md](../research/team-comparison-methods.md).

## Staged path (each slice depends on the last)

1. **004 — Per-Position mean Fit + overall (S1, baseline)** — ship now.
2. **005 — Matchup → expected goals (M1)** — the real comparison; ADR-0001's intent.
3. **006 — Poisson scoreline distribution (M2)** — turn xG into P(win/draw/loss).
4. **007 — Chemistry multiplier from `link_up_partners`** — synergy in the matchup.
5. **008 — Role-weighted Fit (M3, future)** — pairs with named Positions; optional.
6. **009 — Stochastic match engine (L1, deferred)** — long-term endpoint.

## Notes

- Each stage produces a working comparison and feeds the next (S1's per-Position
  means become inputs to M1).
- Lock the method into ADR-0001 when M1 is designed (record M1 as accepted, S1 as
  the superseded baseline, L1 as deferred).
- Vocabulary per CONTEXT.md (Character, Position, Fit, Team, Placement).
