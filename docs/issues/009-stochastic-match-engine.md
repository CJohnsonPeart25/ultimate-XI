# Stochastic match engine (L1, deferred)

Type: HITL

## Parent

epic-team-vs-team-simulation

## What to build

Deferred long-term endpoint. Simulate a match event-by-event (possession →
chances → shots → saves → goals), driving each event off line Fit and chemistry,
with the hidden Stats finally in play: `consistency` as per-match variance,
`aggression` → fouls/cards, `injury_proneness` → injuries. Aggregate many seeded
Monte Carlo runs into outcome probabilities. A Markov-chain / possession-flow
variant (L1a) is the lighter fallback if full event simulation is too costly.

Only start once M1/M2 have proven the strength model. Grounded in Hattrick / FM /
OOTP engines and Monte Carlo match simulation (see docs/research/team-comparison-methods.md).

## Acceptance criteria

- [ ] Decision recorded: full event engine vs Markov (L1a) variant
- [ ] Seeded RNG so runs are reproducible
- [ ] Hidden Stats (consistency, aggression, injury_proneness) drive simulated events
- [ ] Monte Carlo aggregation yields outcome probabilities consistent with M1/M2
- [ ] Dedicated module with a strong test harness

## Blocked by

- 008-role-weighted-fit
