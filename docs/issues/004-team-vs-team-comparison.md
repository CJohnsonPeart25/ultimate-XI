# Team-vs-team comparison

Type: HITL

## What to build

Compare two complete Teams. Load two Team JSON documents (or one built + one
imported) and show a per-Position comparison plus an overall.

**This slice is HITL: the comparison method is not locked.** The tentative
approach is per-Position **mean Fit** (mean of the Fits of the Placements assigned
to each Position) plus an overall mean of all 11 Fits, overlaid on the existing
radar (four Position axes). ADR-0001 records the intended direction as a
lightweight *matchup* model — a team's Attack (supplied by Midfield) tested
against the opponent's Defence + Goalkeeper to produce expected goals, with
`link_up_partners` as a chemistry multiplier — so that formation balance emerges
rather than being a fairness rule. **A human decision is required before
implementing:** ship the tentative mean now, or invest in the matchup model.

Resolve that decision first, then build the agreed comparison.

## Acceptance criteria

- [ ] Decision recorded (update ADR-0001): tentative per-Position mean vs matchup model
- [ ] Two complete Teams can be loaded for comparison
- [ ] The agreed metric is computed for each Team and shown per Position plus overall
- [ ] The comparison is visualized (radar overlay of the two Teams across the four Positions)
- [ ] Tests cover the chosen comparison computation

## Blocked by

- 003-team-json-export-import
