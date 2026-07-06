# Team builder — 11 Placements with live tally and validity

Type: AFK

## What to build

A team-builder page where a user assembles a **Team** of 11 **Placements**. Each
Placement assigns a Character to one Position (Goalkeeper, Defence, Midfield,
Attack). The builder holds state in-session only (no persistence in this slice).

As Placements are added, show a **live Position tally** (e.g. `GK 1 · DEF 4 ·
MID 4 · ATT 2`) so the user sees where they are. Position counts are not chosen up
front — they emerge from the assignments. Show each Placement's **Fit** for its
assigned Position, so a poor fit (e.g. an Attack Character placed in Goal) is
visible.

Enforce validity: a Team is *complete/comparable* only when all 11 slots are
filled and **exactly one** Placement is on the Goalkeeper Position. A Character
appears at most once per Team. Surface completeness/validity clearly (the user
can build an incomplete or invalid Team, but it is flagged as not complete).

## Acceptance criteria

- [ ] User can fill up to 11 slots, each a Character + assigned Position
- [ ] A live Position tally updates as Placements change
- [ ] Each Placement shows the Character's Fit for its assigned Position
- [ ] A Character cannot be placed more than once in the same Team
- [ ] The Team is flagged complete only at 11 Placements with exactly one Goalkeeper
- [ ] Invalid states (no GK, two GKs, fewer than 11) are shown as not-complete rather than silently accepted

## Blocked by

- 001-fit-from-position-weights (needs Fit and the Character list)
