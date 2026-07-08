# Ultimate XI

A Streamlit app that rates ~89 Super Smash Bros. characters as if they were
footballers, then lets you compare them, build teams, and simulate matches.

## What it does

- **Compare** — FIFA-style radar charts of any number of characters, per stat
  category or overall.
- **Players** — a sortable table of every character by any stat or category average.
- **Team builder** — fill an 11-slot team (exactly one goalkeeper), assign each
  player a position, and export/import the team as JSON. "Random All" generates a
  valid random team.
- **Team vs Team** — paste two teams and get a per-position breakdown plus a match
  simulation: expected goals, win/draw/loss probabilities, and a likely scoreline
  (with the maths shown in LaTeX).
- **Edit ratings / Edit weights** — adjust character stats and the per-position
  Fit weights; changes persist to a local SQLite database.

Character stats live in a SQLite database (`ultimate_xi.db`), seeded from
`seed.yaml`. See `CONTEXT.md` for the domain glossary and `docs/` for design notes.

## Run it locally

Requires [uv](https://docs.astral.sh/uv/) and Python 3.14+.

```bash
# 1. install dependencies
uv sync

# 2. create and seed the database (first run only)
uv run python scripts/seed_db.py

# 3. start the app
uv run streamlit run app.py
```

The app opens at http://localhost:8501.

## Tests

```bash
uv run pytest
```
