# Fit from a seeded, editable position_weight table

Type: AFK

## What to build

Introduce **Fit** end-to-end. Add a `position_weight` table to the SQLite
database, seeded with sensible default weights for each of the four Positions
(Goalkeeper, Defence, Midfield, Attack) over the outfield/keeper Stats. Compute
`Fit(character, position)` as a **normalized weighted blend** of the Character's
Stats — `sum(weight * stat) / sum(weights)` — so Fit lands on the same 0–5 scale
regardless of the raw weight numbers. Hidden Stats (`consistency`,
`injury_proneness`) never contribute to Fit.

Surface the result: show each Character's four Fit scores on the existing Compare
page. Add a weights-editor page (mirroring the existing ratings editor) that edits
`position_weight` rows; saving persists the change and Fit recomputes on next read.

Weights are a single global set, last-write-wins (consistent with Character
ratings). See CONTEXT.md for the Position / Fit vocabulary.

## Acceptance criteria

- [ ] `position_weight` table exists and is seeded with default weights for all four Positions
- [ ] `Fit(character, position)` returns a normalized weighted blend on the 0–5 scale
- [ ] Hidden Stats are excluded from every Fit calculation
- [ ] The Compare page shows each selected Character's four Position Fit scores
- [ ] A weights-editor page can change `position_weight` values, and the edit persists and re-scores Fit
- [ ] Tests cover the Fit math, normalization (arbitrary weight magnitudes), and hidden-stat exclusion

## Blocked by

- None — can start immediately
