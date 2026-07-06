# Ultimate XI

A tool for rating Super Smash Bros. characters as football players, comparing
them on a radar chart, and (in progress) assembling them into Teams to compare
team-vs-team. Stats are authored with a future match simulation in mind.

## Language

**Character**:
One of the ~89 rated entities (e.g. `mario`). The unit that owns stats and can
be placed in a Team. Persisted as a `Player` row.
_Avoid_: player (ambiguous with the human user), fighter.

**Stat**:
A single 0–5 rated attribute (e.g. `pace`, `reflexes`). Grouped into Categories.

**Category**:
A grouping of Stats for *display and averaging*: physical, technical, mental,
goalkeeping, hidden. Categories describe *what kind* of attribute a Stat is —
they are NOT Positions.
_Avoid_: using a Category as a Position.

**Position**:
The area a Character is assigned to play in a Team. Currently **coarse** — exactly
four values: **Goalkeeper**, **Defence**, **Midfield**, **Attack**. Named
positions (centre-back, striker, ...) are a possible *future refinement of this
same concept* — finer granularity, not a new term — at which point these four
become groupings ("lines") of positions. There are no named formations.
_Avoid_: line/unit (reserved for the future grouping-of-positions sense), role
(implies FM-style sub-roles we cut), formation.

**Fit**:
How suited a Character is to a Position, computed as a normalized weighted blend
of its Stats (weights held in the `position_weight` table; hidden Stats never
count). Every Character has a Fit score, on the same 0–5 scale, for each of the
four Positions. This is what stops a strong Attack Character being wasted in Goal.
_Avoid_: familiarity (FM term), position rating (FIFA term), chemistry.

**Team**:
Eleven Placements. A Team is *complete* (and therefore comparable) only when all
11 slots are filled and exactly one Placement is on the Goalkeeper Position.
Position counts are not chosen up front — they emerge from the Placements, shown
as a live tally while building. A Team is **not** stored in the database; it is an
ephemeral, in-session document exported to / imported from JSON (validated by a
Pydantic schema). Only Characters and Position weights live in the DB.
_Avoid_: squad, lineup, formation.

**Placement**:
The assignment of one Character to one Position within a Team. A Character appears
at most once per Team. The Character's Fit for its Placement's Position is what the
Placement contributes to Team strength.
_Avoid_: slot (informal only).
