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

1. **004 — Per-Position mean Fit + overall (S1, baseline)** — ✅ done.
2. **005 — Matchup → expected goals (M1)** — ✅ done (`simulation.py`).
3. **006 — Poisson scoreline distribution (M2)** — ✅ done.
4. **007 — Chemistry multiplier from `link_up_partners`** — ✅ done.
5. **008 — Role-weighted Fit (M3, future)** — ⏸️ deferred (needs named Positions).
6. **009 — Stochastic match engine (L1, deferred)** — ⏸️ deferred (long-term endpoint).

Status: the core simulation (S1 baseline + M1 xG + M2 Poisson + chemistry) is
shipped and tunable via sliders. 008 and 009 are consciously deferred in favour of
simplicity — the xG+Poisson model is the intended everyday tool. Pick them up only
if the group wants named positions (008) or a full event-by-event engine (009).

## Notes

- Each stage produces a working comparison and feeds the next (S1's per-Position
  means become inputs to M1).
- Lock the method into ADR-0001 when M1 is designed (record M1 as accepted, S1 as
  the superseded baseline, L1 as deferred).
- Vocabulary per CONTEXT.md (Character, Position, Fit, Team, Placement).
