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
- **Team-vs-team comparison — LOCKED.** The accepted method is the **matchup →
  expected-goals model (M1)**: a team's Attack (supplied by Midfield) is tested
  against the opponent's Defence + Goalkeeper to produce expected goals, a Poisson
  layer (M2) turns the two xG numbers into P(win/draw/loss) and a likely scoreline,
  and co-placed `link_up_partners` in the creative lines add a chemistry boost (M2/
  M1). Formation balance emerges (e.g. "10 in attack" concedes rather than being
  penalised by a rule). Implemented in `simulation.py` with all coefficients in
  `SimParams` (surfaced as sliders). The earlier per-Position **mean Fit + overall
  (S1)** is retained as a quick static baseline on the same page, superseded by M1
  as the verdict. Rationale and every coefficient choice:
  `docs/research/simulation-design-decisions.md`.
- **Deferred (not built):** finer **role-weighted Fit for named positions (M3)** and
  a full **stochastic match engine (L1)** — see issues 008/009. These were
  consciously deferred in favour of simplicity; the current xG+Poisson model is the
  intended everyday tool. The `state_template.yaml` stats (consistency = variance,
  aggression → fouls, injury_resilience) remain the design target for L1 if it is
  ever picked up.
