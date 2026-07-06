---
status: accepted
---

# Teams are ephemeral JSON documents, not database entities

Characters and Position weights live in SQLite (via SQLModel), so the obvious move
would be to store Teams relationally too. We deliberately did **not**: a Team is
an ephemeral, in-session construct that the team-builder page exports to / imports
from a JSON document (validated by a plain Pydantic model, not a SQLModel table).
Starting blank or importing a JSON lets a user tweak an existing Team without any
shared persistence, migrations, or concurrency handling.

## Considered Options

- **Saved named Teams in the DB** (`team` + `team_placement` tables). Rejected:
  adds schema, a shared library, and last-write-wins concurrency for something the
  user wants to be throwaway and hand-editable.
- **Ephemeral JSON documents** (chosen). No DB footprint; a Pydantic schema does
  double duty as export serializer and import validator (11 Placements, exactly
  one Goalkeeper, known Characters, no duplicate Character).

## Consequences

- SQLModel is **not** involved in Teams; only Characters and the `position_weight`
  table are DB-backed. A future move to persisted Teams would be a real migration.
- **Team-vs-team comparison is not yet locked.** Tentative approach: per-Position
  mean Fit plus an overall mean. Documented intended direction is a lightweight
  *matchup* model — a team's Attack (supplied by Midfield) tested against the
  opponent's Defence + Goalkeeper to produce expected goals — so that formation
  balance (e.g. "10 in attack") emerges from the matchup rather than a fairness
  rule, with `link_up_partners` acting as a chemistry multiplier. The per-Position
  means become inputs to that model, not the final answer. The `state_template.yaml`
  stat descriptions (consistency = variance, aggression → fouls) point at an
  eventual stochastic match engine as the endpoint.
