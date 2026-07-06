# Chemistry multiplier from link_up_partners (synergy)

Type: AFK

## Parent

epic-team-vs-team-simulation

## What to build

Factor **synergy** into the matchup. When a Character is placed alongside one of its
`link_up_partners` in the same Position (or an adjacent one — Midfield/Attack), apply
a chemistry multiplier that boosts the relevant line's contribution to xG. Start as a
single tunable coefficient scaled by the count of co-placed partner pairs.

This is the "link-up plays" the data was designed for (EA FC Ultimate Team chemistry
is the analogue). See docs/research/team-comparison-methods.md.

## Acceptance criteria

- [ ] Co-placed `link_up_partners` pairs are detected within a Team
- [ ] A tunable chemistry multiplier adjusts the affected line's contribution to xG
- [ ] A Team with strong link-ups beats an otherwise-identical Team without them
- [ ] The chemistry contribution is visible in the comparison output
- [ ] Tests cover pair detection and the multiplier effect

## Blocked by

- 006-poisson-scoreline-distribution
