# Role-weighted Fit for named Positions (M3, future)

Type: HITL — DEFERRED

> Deferred by decision (see docs/research/simulation-design-decisions.md and
> ADR-0001). Introducing named positions expands the Position model, the team
> builder UI, and CONTEXT.md — a real product step that runs against the current
> "simplicity wins" preference. The coarse four-Position model is the intended
> everyday tool. Pick this up only if the group wants named positions.

## Parent

epic-team-vs-team-simulation

## What to build

Optional/future. Refine coarse Positions into named positions (e.g. centre-back,
full-back, deep-lying playmaker, striker) with their own weight sets, so Fit — and
therefore every downstream comparison — becomes role-specific. This is the
granularity upgrade CONTEXT.md anticipates: the four coarse Positions become
groupings of named positions.

HITL: introducing named positions is a modelling decision (which positions, how they
group, whether the Team shape UI changes) that needs a human design pass. Grounded in
Football Manager's role/attribute weighting (see docs/research/team-comparison-methods.md).

## Acceptance criteria

- [ ] Decision recorded on the named-position taxonomy and how it maps to the four coarse Positions
- [ ] Per-role weight sets exist and drive Fit
- [ ] Existing coarse-Position behaviour still works (or a clean migration path)
- [ ] CONTEXT.md updated for the named-position vocabulary

## Blocked by

- 007-chemistry-multiplier
