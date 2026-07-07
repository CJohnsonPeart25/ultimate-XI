# Deploying Ultimate XI (and the SQLite question)

Notes on how to host this app, focused on the persistence problem. This is a
research/reference doc — nothing here is implemented yet.

## TL;DR

Streamlit Community Cloud (SCC) **lets you put a SQLite file in the repo, but you
should not rely on it** for this app. SCC's container disk is *ephemeral*: any
write (the edit-ratings form, friends editing rankings) is lost on every restart,
redeploy, or the periodic sleep/wake cycle. It "works" during a session and then
silently resets — the most confusing failure mode. SQLite-on-disk is fine for a
read-only demo, wrong for our "friends concurrently edit rankings" use case.

Because SQLModel/SQLAlchemy is database-agnostic, switching stores is essentially
a one-line engine-URL change plus a connection secret — the schema and models
don't change.

## Options, ranked for our case

| Option | Why | Effort |
|---|---|---|
| **Turso (libSQL)** | It *is* SQLite, but networked + persistent. SQLAlchemy dialect exists, so the schema barely changes. Free tier. Closest to what we have today. | Low |
| **Supabase / Neon (Postgres)** | Rock-solid managed Postgres, generous free tier. SQLModel just needs a `postgresql://...` URL. Best if we outgrow SQLite. | Low–medium |
| **Keep SQLite as a read-only seed** | Commit the `.db` (or re-seed from `seed.yaml` on deploy) and drop live editing. Only if editing moves elsewhere. | Trivial, but loses the edit feature |

## What deployment looks like (either hosted DB)

1. **Dependencies** — SCC installs from `requirements.txt`, `pyproject.toml`, or
   `uv.lock`. We have `pyproject.toml`; ensure the *app* deps (not just the dev
   group) are declared so SCC installs them.
2. **Secrets** — put the DB URL in Streamlit *Secrets* (`st.secrets["db_url"]`),
   never in the repo. Then `create_engine(st.secrets["db_url"], ...)`.
3. **`.gitignore` the local `.db`** — it should not ship once the DB is hosted.
4. **Seed once** — run `scripts/seed_db.py` against the hosted DB (locally,
   pointing at the remote URL) to load the 89 characters.
5. **SQLite-specific pragmas** — the WAL + `busy_timeout` `PRAGMA`s in `models.py`
   are SQLite-only. On Postgres they'd be removed (Postgres handles concurrency
   natively); on Turso they can stay.

## Why this matters for our design choices

The last-write-wins concurrency model and the `extend_existing` hot-reload guard
both assume a **persistent, shared** database. Turso/Postgres provide that;
on-disk SQLite on SCC does not — each restart wipes state and there's no real
sharing between deploys. So the persistence choice is what makes the concurrent-
editing feature actually behave as designed.

## Suggested path if/when we deploy

Read the DB URL from `st.secrets` with a local SQLite fallback, so the app runs
locally on SQLite unchanged but uses the hosted DB when deployed. Add a
`requirements.txt` (or confirm SCC reads `pyproject.toml`) and a `.gitignore`
entry for `ultimate_xi.db`. Turso is the least-disruptive first step given the
existing SQLite schema.
