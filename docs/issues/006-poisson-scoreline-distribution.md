# Poisson scoreline distribution (M2)

Type: AFK

## Parent

epic-team-vs-team-simulation

## What to build

Turn M1's two xG numbers into an outcome distribution. Model each side's goals as a
Poisson process with mean = that side's xG, and derive P(win) / P(draw) / P(loss),
the most likely scorelines, and expected points. Small increment on top of M1, big
interpretability gain. Show it alongside the xG numbers on the comparison page.

Grounded in bivariate-Poisson / Dixon–Coles goal models (see
docs/research/team-comparison-methods.md).

## Acceptance criteria

- [x] P(win)/P(draw)/P(loss) computed from the two xG values via a Poisson model
- [x] Most likely scoreline(s) surfaced
- [x] Displayed on the team comparison page next to the xG numbers
- [x] Tests cover the probability computation (sums to 1; symmetry sanity checks)

## Blocked by

- 005-matchup-expected-goals
