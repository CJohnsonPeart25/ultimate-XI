# Team-vs-team comparison — per-Position mean baseline (S1)

Type: AFK

## Parent

epic-team-vs-team-simulation

## What to build

The **baseline** team-vs-team comparison. Load two complete Teams (paste JSON,
reusing the `TeamDoc` schema and validation) and show which is stronger by
**per-Position mean Fit** plus an **overall mean** of all 11 Placements' Fit.
Overlay the two Teams on a four-axis (Position) radar and show a line-by-line
table.

Decision (resolves the former HITL question): ship S1 now as an explicit
**baseline**, and commit to the matchup → expected-goals model (issue 005 / M1) as
the real answer. S1's per-Position means become the inputs to M1, so this is not
throwaway. See docs/research/team-comparison-methods.md.

## Acceptance criteria

- [x] Decision recorded: ship S1 baseline, target M1 (this issue = S1)
- [x] Two complete Teams can be loaded (pasted JSON, validated; incomplete teams rejected clearly)
- [x] Per-Position mean Fit computed for each Team, plus an overall mean
- [x] The two Teams are overlaid on a four-Position radar
- [x] A per-Position table shows both Teams and the difference
- [x] Tests cover the per-Position mean and overall-mean computations

## Blocked by

- None — can start immediately (depends only on Fit + TeamDoc, both built)
