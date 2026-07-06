# Matchup → expected goals (M1)

Type: HITL

## Parent

epic-team-vs-team-simulation

## What to build

The real comparison model. Instead of comparing like-for-like Positions, test each
Team's **Attack (supplied by Midfield)** against the opponent's **Defence +
Goalkeeper**, both directions, to produce an expected-goals (xG) number per side —
and from that, a verdict/scoreline. Formation balance emerges: an empty Defence is
punished only when the opponent's Attack is scored against it, not by a rule.

Reuse S1's per-Position mean Fit as the raw strength inputs. The strength→xG mapping
has no ground-truth data, so expose tunable coefficients and hand-calibrate. Grounded
in Hattrick sector matchups and Dixon–Coles attack/defence-strength Poisson models
(see docs/research/team-comparison-methods.md).

HITL: the exact strength→xG function and its coefficients need a human design pass
before implementation.

## Acceptance criteria

- [ ] A team's Attack strength (Attack fed by Midfield) and defensive resistance (Defence + Goalkeeper) are derived from per-Position Fit
- [ ] Each side's xG is computed from its attack strength vs the opponent's resistance
- [ ] "10 in attack" loses to a balanced Team without any explicit fairness rule
- [ ] Coefficients are tunable and documented
- [ ] ADR-0001 updated: M1 recorded as accepted method, S1 as superseded baseline
- [ ] Tests cover the strength derivation and xG computation

## Blocked by

- 004-team-vs-team-comparison
