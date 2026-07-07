# Stochastic match engine (L1, deferred)

Type: HITL — DEFERRED

> Deferred by decision (see docs/research/simulation-design-decisions.md and
> ADR-0001). A full event-by-event Monte Carlo engine is a large subsystem; the
> M1+M2 xG/Poisson model already gives outcome probabilities and a scoreline at a
> fraction of the complexity. This remains the long-term endpoint the hidden Stats
> were authored for — build only if the group wants event-level realism.

## Parent

epic-team-vs-team-simulation

## What to build

Deferred long-term endpoint. Simulate a match event-by-event (possession →
chances → shots → saves → goals), driving each event off line Fit and chemistry,
with the hidden Stats finally in play: `consistency` as per-match variance,
`aggression` → fouls/cards, low `injury_resilience` → injuries. Aggregate many seeded
Monte Carlo runs into outcome probabilities. A Markov-chain / possession-flow
variant (L1a) is the lighter fallback if full event simulation is too costly.

Only start once M1/M2 have proven the strength model. Grounded in Hattrick / FM /
OOTP engines and Monte Carlo match simulation (see docs/research/team-comparison-methods.md).

## Acceptance criteria

- [ ] Decision recorded: full event engine vs Markov (L1a) variant
- [ ] Seeded RNG so runs are reproducible
- [ ] Hidden Stats (consistency, aggression, injury_resilience) drive simulated events
- [ ] Monte Carlo aggregation yields outcome probabilities consistent with M1/M2
- [ ] Dedicated module with a strong test harness

## Blocked by

- 008-role-weighted-fit
