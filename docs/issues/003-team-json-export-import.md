# Team JSON export / import

Type: AFK

## What to build

Make a **Team** a portable, ephemeral JSON document (see ADR-0001). Define a
Pydantic `TeamDoc` schema — not a SQLModel table — that represents a Team as its
list of Placements (Character + Position) plus an optional name.

From the builder: **Export** downloads the current Team as a JSON file.
**Import** uploads a JSON file to populate the builder so the user can start blank
or tweak an existing Team. The Pydantic schema does double duty: `model_dump_json`
to export, `model_validate_json` to parse on import.

Validate on import (reject with a clear message on failure): exactly 11
Placements, exactly one Goalkeeper Position, every Character exists in the DB, and
no duplicate Character. A partially-built Team may also be exportable, but only a
valid complete Team round-trips cleanly.

## Acceptance criteria

- [ ] A `TeamDoc` Pydantic schema serializes/deserializes a Team to/from JSON
- [ ] Export produces a downloadable JSON file of the current build
- [ ] Import loads a JSON file into the builder for tweaking
- [ ] Import rejects malformed teams with a clear message (not 11, not one GK, unknown Character, duplicate Character)
- [ ] A complete valid Team round-trips (export then import) without loss
- [ ] Tests cover the schema round-trip and each import-validation failure

## Blocked by

- 002-team-builder
