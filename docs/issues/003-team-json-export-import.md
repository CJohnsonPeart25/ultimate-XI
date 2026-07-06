# Team JSON export / import

Type: AFK

## What to build

Make a **Team** a portable, ephemeral JSON document (see ADR-0001). Define a
Pydantic `TeamDoc` schema — not a SQLModel table — that represents a Team as its
list of Placements (Character + Position) plus an optional name.

From the builder: **Export** shows the current Team as copy-able JSON (a text/code
box, not a file download). **Import** is a paste-in text area + Load button that
populates the builder so the user can start blank or tweak an existing Team. The
Pydantic schema does double duty: `model_dump_json` to export, `model_validate_json`
to parse on import. (Copy-paste chosen over file download/upload for easy sharing
of small team docs.)

Validate on import (reject with a clear message on failure): exactly 11
Placements, exactly one Goalkeeper Position, every Character exists in the DB, and
no duplicate Character. A partially-built Team may also be exportable, but only a
valid complete Team round-trips cleanly.

## Acceptance criteria

- [x] A `TeamDoc` Pydantic schema serializes/deserializes a Team to/from JSON
- [x] Export shows copy-able JSON of the current build
- [x] Import loads pasted JSON into the builder for tweaking
- [x] Import rejects malformed teams with a clear message (not 11, not one GK, unknown Character, duplicate Character)
- [x] A complete valid Team round-trips (export then import) without loss
- [x] Tests cover the schema round-trip and each import-validation failure

## Blocked by

- 002-team-builder
