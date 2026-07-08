# Tick-Based Match Engine: Design & Build Research

_Research + design report for issue 009 (stochastic match engine, deferred). It
fleshes the deferred L1 endpoint into a concrete build plan. Uses the CONTEXT.md
vocabulary throughout: **Character**, **Stat**, **Category**, **Position**,
**Fit**, **Team**, **Placement**. Builds ON the prior survey in
`team-comparison-methods.md` (do not re-read the EA FC / Hattrick / Dixon–Coles
material — it is assumed) rather than repeating it._

> **Verification note (workspace policy).** The web-search / web-fetch tools were
> unavailable when this was written, so the open-source projects and papers below
> are cited **from prior knowledge and not live-verified in this session**. Every
> repo name, license, and URL should be confirmed before you rely on it — treat
> the "Open-source options" section as a shortlist to check, not settled fact.

---

## 0. TL;DR — the recommended path

**Write your own tick engine in Python, in-repo, driven by your existing Fit and
Stats — do not adopt a foreign engine as your core.** No open-source football
engine is both (a) a clean drop-in for a Streamlit + SQLModel hobby app and (b)
FM-style in behaviour. The good open-source projects are either research RL
environments (Google Research Football — C++/game-physics, overkill, wrong shape),
old text managers (ESMS, Bygfoot — GPL C, useful as _design references_ not
libraries), or analytics tooling (socceraction, mplsoccer — brilliant, but they
_measure_ football, they don't _simulate_ it). The analytics tooling is the real
prize: it gives you the **decision-making math** (expected threat / xT and pitch
control) and the **visualisation** (mplsoccer pitches) without you having to invent
either.

So the plan is:

- **Phase 1 (text engine).** A per-possession, utility-scored engine: 22 simplified
  agents + a ball on a coordinate pitch, a tick loop, and one decision function that
  scores candidate actions (pass / shoot / dribble / hold / clear) by expected value.
  Success probabilities come from your **Fit** and **Stats**; variance comes from
  `consistency`; fouls from `aggression`; injuries from `injury_resilience`. It emits
  a readable event log. **Calibration bridge:** aggregated over thousands of seeded
  runs it should reproduce the current **M1/M2 xG** expectations — that is your test
  oracle, and the reason you already did M1/M2 first.
- **Phase 2 (visuals).** Log the full per-tick state to a frame buffer during the
  run, then render it _after_ the sim with **mplsoccer** (pitch) + a Plotly animated
  scatter or a matplotlib `FuncAnimation` exported to GIF/MP4. Do not try to animate
  live inside Streamlit's rerun loop — render-then-play.

Everything stays tunable via a `MatchParams` dataclass surfaced as sliders, exactly
like `SimParams`. The tick engine does not replace M1/M2 — it sits beside it, and
M1/M2 becomes its **validation harness**.

The rest of this document explains _why_ and _how_, from first principles.

---

## 1. The mental model of a tick-based engine

If you have never built a simulation, this is the whole idea in one paragraph:

> A simulation is a **state** plus a **step function**. The state is a snapshot of
> the world ("where is everyone, who has the ball, what minute is it"). The step
> function takes the current state and produces the next state a fraction of a
> second later. You call it over and over in a loop until the match ends, and you
> record what happened. That's it. Football Manager is this loop running fast, with
> a very elaborate step function and a renderer drawing each state.

### 1.1 Game state

The match state is a plain data object. For this project, minimally:

```
MatchState:
    clock_seconds: float              # 0 .. 5400 (90 min); or event-time
    ball: Ball(x, y, holder|None, in_flight, target, vx, vy)
    agents: list[Agent]               # 22 of them (11 per Team)
    possession_team: 'A' | 'B' | None
    phase: enum(kickoff, build_up, attack, shot, set_piece, transition, dead_ball)
    score: (int, int)
    rng: seeded Random                 # reproducibility — issue 009 AC
```

Each **Agent** wraps one **Placement** and carries live match data on top of the
static Character:

```
Agent:
    character: str                    # -> Player row (the Stats)
    team: 'A' | 'B'
    position: str                     # coarse Position: gk/def/mid/att
    fit: float                        # precomputed Fit for its Position
    x, y: float                       # current pitch coordinates
    home_x, home_y: float             # positional "anchor" it drifts back to
    stamina_now: float                # decays over the match
    booked: bool
    off: bool                         # sent off / injured
```

### 1.2 The pitch as coordinates

Model the pitch as a rectangle, e.g. **x ∈ [0, 105], y ∈ [0, 68]** (metres, real
pitch dimensions — this is exactly the coordinate system mplsoccer draws, so Phase 2
is free). Team A attacks toward x=105, Team B toward x=0. Everything — passing range,
shot distance, "space", offside — is then just geometry. Use metres, not abstract
zones, because it makes the decision math (distances, angles) natural and it maps
1:1 onto the visualiser. Coarse Positions become **anchor regions**: a defence Agent
has a low `home_x`, an attack Agent a high one.

### 1.3 A match is a sequence of state transitions

The whole match is: `state₀ → step → state₁ → step → state₂ → … → state_final`. Each
`step`:

1. **Perceive** — for the ball-holder, gather candidate actions; for everyone else,
   compute desired movement.
2. **Decide** — score each candidate, pick one (see §2).
3. **Resolve** — roll the RNG against a success probability; mutate the state (ball
   moves, possession flips, a goal, a foul).
4. **Advance** — move off-ball players a little, tick the clock, decay stamina.
5. **Record** — append any notable event to the log; snapshot state for Phase 2.

### 1.4 Time resolution — three options, pick per-phase

| Resolution | What it means | Cost | Fidelity |
|---|---|---|---|
| **Per-second tick** (1 Hz) | 5,400 steps/match | Cheap | Good enough for text; smooth-enough for viz at 5–10× playback |
| **Sub-second tick** (5–10 Hz) | Physics-y ball flight, interceptions mid-pass | 5–10× cost | FM-like smoothness; needed only for real ball physics |
| **Event-driven** ("possession-hop") | Jump straight from event to event, no fixed dt | Cheapest | No smooth animation; this is basically L1a Markov |

**Recommendation:** start **event-driven / coarse-tick hybrid**. Resolve football as
a sequence of _possessions_ and _actions_ (a pass takes ~1–3 simulated seconds, a
dribble ~2s), advancing the clock by the action's duration rather than a fixed dt.
This is dramatically simpler than a physics tick, produces a perfectly good text
commentary, and still yields time-stamped state snapshots you can interpolate for
animation later. Move to a true fixed sub-second tick only if/when you want the ball
to visibly curve and be intercepted in flight — that is a Phase 2+ luxury, not a
Phase 1 need. (This is the honest FM-gap: FM runs a real-time continuous physics
engine at high frequency. You do not need to, and should not try to, at first.)

---

## 2. Decision-making — the core of the question

This is what "the app plays the game for you" actually means: **every tick, each
Agent chooses an action.** There is no magic — it is a scoring function. Here are the
real techniques, ranked by complexity-vs-payoff for _this_ project.

### 2.1 Utility / expected-value scoring — **START HERE, highest payoff-per-effort**

The ball-holder enumerates its candidate actions and scores each by **expected
value**; the highest-scoring one wins (optionally softmax-sampled so it isn't
robotic). This single idea gets you 80% of FM-feel for 20% of the work, and it is
the technique most amateur-but-good engines actually use.

Candidate actions for the holder:

- **Shoot** — value ≈ `P(goal from here) × 1.0`. `P(goal)` is a function of distance
  and angle to goal, the shooter's `shooting` Stat, and the keeper's Fit. This _is_
  an xG model living inside the engine (see §4).
- **Pass to teammate T** — value ≈ `P(pass completes) × xT(T's location) × (1 + chem)`.
  `xT` is **expected threat**: how much more dangerous the ball is at T's location
  than here (§2.4). Pass completion falls with distance and with opponents near the
  lane; rises with passer `passing`/`vision` and receiver `positioning`.
- **Dribble** — value ≈ `P(beat nearest defender) × xT(slightly-advanced location)`.
  Driven by `dribbling`/`agility`/`pace` vs defender `tackling`/`pace`.
- **Hold / recycle** — a low, constant baseline value; wins when everything else is
  risky (under pressure, no outlet). Prevents suicidal forced actions.
- **Clear** (defenders under pressure) — high value when deep in own third and
  pressed; just launches the ball upfield and concedes possession safely.

The art is entirely in the **value functions and their weights** — and those weights
are your `MatchParams` sliders. This directly answers _"how does it decide when to
pass upfield vs shoot?"_: **shoot when the shot's expected value beats the best
pass's expected value.** A striker 6m out with a clear angle has a shot-EV that
dwarfs any pass; a midfielder 40m out has a near-zero shot-EV, so a forward pass
wins. Emergent, not scripted.

Off-ball movement (the _"make space"_ question) is the mirror image: each non-holder
also scores candidate _destinations_ and moves toward the best one (§2.4).

### 2.2 Finite state machines (FSM) — cheap structure, use for phases

An FSM is a set of states and transitions. Use it at two levels:

- **Match phase** (`kickoff → build_up → attack → shot → transition → set_piece`),
  which gates what actions are even sensible (you can't shoot during build-up in your
  own half).
- **Per-Agent role state** (`supporting / pressing / holding / recovering`), which
  shapes off-ball movement.

FSMs are trivial in Python (a dict of transitions, or `match`/`case`). They give you
readable structure with almost no cost. **Recommendation: yes, for phases and coarse
Agent states.** Don't over-nest them.

### 2.3 Behaviour trees (BT) — the FM-ish "proper" answer, defer

Behaviour trees are what most modern game AI (and, as far as is publicly understood,
FM-style engines conceptually) use for richer agent behaviour: a tree of
selectors/sequences ("if under pressure → clear; else if lane open → pass; else
dribble; else hold"). They are essentially a **more structured, prioritised form of
the utility scoring in §2.1**, and you can graduate to them once the flat scorer
feels limiting. **Recommendation: defer.** A flat utility scorer with good weights is
easier to tune and reason about for a first engine; adopt BTs only if branching logic
gets unwieldy. Libraries exist (`py_trees`) but you likely won't need one.

### 2.4 Space, pitch control, and expected threat (xT) — **the secret sauce for realism**

This is where football-specific analytics beats generic game AI, and where you should
invest _after_ §2.1 works.

- **Expected Threat (xT).** A value grid over the pitch: each cell holds "the
  probability a possession starting here ends in a goal, soon." Karun Singh's original
  xT and the socceraction library's implementations are the references. You can ship a
  **static xT grid** (a lookup table baked into the repo) as the `xT(location)` term in
  every pass/dribble value. This is the single highest-value addition to §2.1: it makes
  the engine _want to progress the ball toward goal_ without you scripting "go forward."

- **Pitch control / influence fields.** Model each Agent as projecting a region of the
  pitch it "controls" (a Gaussian/decaying field around it, stretched by `pace` in its
  facing direction). Summing the fields tells you, for any point, **which team would
  win the ball there**. Two payoffs:
  1. **Pass safety** = pitch control of your team along the passing lane and at the
     target — a principled replacement for the crude "opponents near the lane" term.
  2. **Off-ball movement** = each supporting Agent moves toward high-value space, i.e.
     a point that is _both_ high-xT _and_ under its own team's control (or contested in
     its favour). That is a computational definition of **"making space"**: run to where
     you'd receive it dangerously and safely. Defenders do the inverse — move to _deny_
     the opponent high control near your goal (closing space / marking).

  The academic reference is Spearman's pitch control / off-ball scoring model and the
  Friends of Tracking materials (see §3). You do not need their full physics; a
  distance-weighted influence field is enough and cheap.

- **EPV (expected possession value)** combines the two: value of an action = change in
  (pitch-control-weighted xT). This is the state of the art in analytics and a lovely
  north star, but a **static xT grid + a simple influence field is the pragmatic 90%.**

### 2.5 ML / RL — do not, for this project

Google Research Football exists precisely to train RL agents to play football, and
academic work (and Google's own) has produced agents via self-play. It is fascinating
and completely wrong for a hobby ratings tool: you'd need training infrastructure,
you'd lose the tight link between a Character's authored **Stats** and its behaviour
(the whole point of the app), and it is unexplainable and untunable-by-slider.
**Recommendation: inspiration only.** Keep the engine rule-based so that a good
`shooting` Stat visibly means "shoots more and scores more," which is what your users
want to see.

### 2.6 Ranking summary

| Technique | Complexity | Payoff for this project | Verdict |
|---|---|---|---|
| Utility / EV scoring | Low–Med | **Very high** | **Phase 1 core** |
| FSM (phases + agent states) | Low | Med (structure) | **Yes, thin** |
| Static xT grid | Low | **High** (ball progresses sensibly) | **Phase 1, add early** |
| Influence / pitch-control field | Med | High (off-ball, pass safety) | **Phase 1.5** |
| Behaviour trees | Med | Med | Defer |
| EPV (control × xT) | Med–High | High but marginal over xT | Later |
| ML / RL | Very High | Negative (untunable, opaque) | No — inspiration only |

---

## 3. Open-source engines and libraries — assess before adopting

**Verify each of these before relying on it** (see the note in §0). Grouped by how
you'd use them.

### 3.1 Simulation engines (adopt as core? mostly no)

- **Google Research Football (`gfootball`)** — a full physics-based 11v11 football
  environment (C++ engine, Python/Gym bindings) built by Google Research for
  reinforcement-learning research. Language: C++ core, Python API. License: Apache-2.0
  (verify). Maturity: high but **research-archived** — activity has wound down. Verdict:
  **inspiration / wrong shape.** It is heavy (a real game engine), aimed at training RL
  agents, and does not consume authored ratings. Not adaptable to a Streamlit ratings
  app. Worth looking at once for how it structures actions/observations. Repo:
  `github.com/google-research/football`.

- **ESMS — Electronic Soccer Management Simulator** — a classic C++ text-mode match
  engine that reads team/tactic files and prints a minute-by-minute commentary; it
  underpinned many old online management leagues. License: GPL (verify). Maturity:
  old, essentially unmaintained, but complete and _exactly the shape of your Phase 1
  goal_. Verdict: **best design reference for the text engine.** Read how it turns
  attribute contests + randomness into a readable commentary and a scoreline; do NOT
  link it (GPL, C++). Look for `eli-b`/community mirrors of ESMS / "ESMS++".

- **Bygfoot** — an open-source football management game (C, GTK) with its own match
  engine producing text/live results. License: GPL. Maturity: legacy. Verdict:
  **design reference only**, same reasons as ESMS.

- **Assorted JavaScript "football simulation engine" repos** — there are several
  hobby JS/TS repos (search terms: "football match simulation engine", "soccer
  simulation", results vary in quality; some are tick-based with 2D canvas rendering).
  Verdict: **worth browsing for architecture and for canvas-rendering ideas**, but
  quality and licensing are inconsistent and porting JS→Python is rarely worth it.
  Verify any specific repo before trusting it — I am **not confident** naming a single
  canonical one, so treat this as a search lead, not a recommendation.

- **Basketball GM / Football GM (`dumbmatt/bbgm`, `football-gm`)** — open-source sports
  management sims in JavaScript with entirely rating-driven, non-physics "possession
  engines." Not football (soccer), but the **possession-loop architecture is the
  single closest analogue to what you want** and is very readable. Verdict:
  **strong architectural reference** for a rating-driven, tick-light engine. Verify.

### 3.2 Analytics / decision-math libraries (adopt as building blocks — **yes**)

- **`socceraction`** (Python) — the library behind VAEP / xT / SPADL from KU Leuven's
  DTAI group. License: permissive (verify — MIT/Apache). Gives you **reference
  implementations and trained xT grids** you can bake into the engine as the
  `xT(location)` term (§2.4). Verdict: **pull the concept and possibly a static grid.**
  Repo: `github.com/ML-KULeuven/socceraction`.

- **Karun Singh's Expected Threat (xT)** — the original blog/notebook defining xT as a
  Markov grid. Verdict: **read it; it's the theory behind your pass-value term.**

- **Friends of Tracking** (David Sumpter et al.) — a YouTube/GitHub education series
  with notebooks for **pitch control (Spearman), xT, and pass models** in Python.
  Verdict: **your single best learning resource for §2.4.** Repo cluster:
  `github.com/Friends-of-Tracking-Data-FoTD/...`.

### 3.3 Visualisation libraries (adopt for Phase 2 — **yes**)

- **`mplsoccer`** (Python, matplotlib-based) — draws regulation pitches, heatmaps,
  passing networks; integrates with matplotlib animation. License: MIT (verify).
  Verdict: **the pitch renderer for Phase 2.** Its coordinate systems are why §1.2
  recommends metre coordinates. Repo: `github.com/andrewRowlinson/mplsoccer`.
- **Plotly** — animated scatter (`px.scatter(..., animation_frame=...)`) renders in
  Streamlit natively and gives a play/pause slider for free. Verdict: **easiest
  interactive Phase 2 option.**
- **`matplotsoccer`** — older, thinner alternative to mplsoccer. Reference only.

---

## 4. Mapping the engine onto THIS project's data

The engine must be a faithful downstream consumer of the authored **Stats**, **Fit**,
**Positions**, chemistry, and hidden Stats — that link is the product. Everything below
is a coefficient in a `MatchParams` dataclass (the §5 companion to `SimParams`).

### 4.1 Fit and coarse Position → anchors and baseline competence

- Each Agent's **Fit** for its **Position** is its baseline competence in that role.
  Use it where a full stat contest is overkill (e.g. a defender's general "am I in the
  right place" reliability), exactly as `team-comparison-methods.md` recommends Fit as
  a per-Placement summary.
- Coarse **Position** sets the Agent's `home_x/home_y` anchor and its default role
  state (defenders press/hold deep; attackers make forward runs). An empty **Defence**
  therefore literally leaves that pitch region unoccupied → the opponent's influence
  field dominates there → they progress and score. **"10 in attack" punishes itself in
  the geometry**, the same emergent-fairness property M1 has, now spatial.

### 4.2 Individual Stats → per-action success probabilities

Every value/success function pulls the relevant raw Stats (not just Fit — this is the
whole reason L1 "consumes everything"):

| Action / event | Attacker Stats | Defender / keeper Stats |
|---|---|---|
| Pass completion | `passing`, `vision` | opponent `interceptions`, `positioning` |
| Dribble past | `dribbling`, `agility`, `pace` | `tackling`, `pace`, `strength` |
| Shot → goal | `shooting`, `composure` | keeper `reflexes`, `handling`, `positioning_gk` |
| Aerial / hold-up | `strength` | `strength` |
| Off-ball getting open | `positioning`, `pace` | opponent `positioning` (marking) |
| Distribution from GK | `distribution` | — |

Map each contest to a probability with a logistic curve on the Stat difference, e.g.
`P = sigmoid(k * (attacker_stat − defender_stat) + bias)`, where `k` and `bias` are
`MatchParams` sliders. This mirrors how M1 maps a strength gap to xG via `slope`.

### 4.3 Hidden Stats — finally in play (issue 009's whole point)

- **`consistency` → per-action variance.** Before each contest, jitter the acting
  Character's effective Stat by noise whose _magnitude scales inversely with
  `consistency`_ (high consistency → tight, reliable; low → boom-or-bust). Slider:
  `consistency_variance`. This is where the RNG lives; it must be **seeded** (issue 009
  AC) so runs reproduce.
- **`aggression` → fouls / cards.** During tackles/pressing, roll a foul with
  probability rising in the defender's `aggression`; escalate to bookings/second-yellow.
  A sent-off Agent's anchor region goes unoccupied → spatial consequence. Slider:
  `foul_rate_per_aggression`.
- **`injury_resilience` → injuries.** On heavy tackles and as `stamina_now` drops, roll
  an injury with probability rising as `injury_resilience` falls; an injured Agent goes
  `off`. Slider: `injury_rate`.
- **`stamina` → fatigue drift.** Decay `stamina_now` each tick (faster for high-work
  Positions); low stamina degrades `pace`/success late-game — the source of late goals.

### 4.4 Chemistry — from flat multiplier to live per-pass buff

Today `link_up_partners` is a single attack multiplier (`chemistry_per_link`). In the
tick engine, **upgrade it to a live per-pass buff**: a pass _between two co-placed
link-up partners_ gets a bonus to completion probability and/or to the xT it unlocks.
This is `team-comparison-methods.md`'s stated "richest possible" synergy. Keep a
`chemistry_pass_bonus` slider; when the engine is aggregated it should reproduce a
chemistry effect of similar size to today's multiplier (§4.5).

### 4.5 The calibration bridge to M1/M2 — **do this, it's your safety net**

You already built M1/M2. That is not throwaway work — it becomes the **oracle** that
keeps the tick engine honest, and it satisfies issue 009's acceptance criterion
"*Monte Carlo aggregation yields outcome probabilities consistent with M1/M2*."

The bridge:

1. Take a set of fixture **Team** pairs spanning strong/weak/balanced/lopsided.
2. For each, compute M1/M2's `xG_A`, `xG_B` and P(win/draw/loss).
3. Run the tick engine **N seeded times** (Monte Carlo) on the same pairs; average
   goals-for = empirical xG, and win/draw/loss frequencies.
4. **Tune `MatchParams` until the tick engine's aggregate xG and outcome
   probabilities land close to M1/M2's** across the fixtures.

This gives you (a) a principled way to set otherwise-arbitrary coefficients, (b) a
regression test suite (assert aggregate xG within a tolerance band of M1/M2), and (c)
a clean story: _M1/M2 is the fast closed-form model; the tick engine is the detailed
model that reproduces it and adds narrative + variance._ They coexist — the tick
engine augments, it does not replace.

> Nuance to expect: the tick engine will naturally show slightly more draws and
> over-dispersion than independent Poisson — which is realistic (it's the very effect
> Dixon–Coles corrects for). Treat "consistent with M1/M2" as "same central
> tendency," not "identical distribution."

---

## 5. Phase 1 — concrete build plan (text engine)

Goal: **a seeded, rating-driven, per-possession engine that prints a readable
commentary and a scoreline, and that aggregates to M1/M2 xG.** No visuals yet.

### 5.1 Module layout (fits the repo)

A new module beside `simulation.py`, mirroring its "everything in a params dataclass"
style. Suggested single file to start (`match_engine.py`), split later:

```
match_engine.py
    MatchParams        (@dataclass — all coefficients/sliders)
    Ball, Agent, MatchState   (dataclasses)
    Event              (dataclass: clock, text, kind, actors)  -> the log
    build_agents(doc, players, weights) -> list[Agent]         # Placement -> Agent
    candidate_actions(state, holder) -> list[Action]
    score_action(state, action, params) -> float              # §2.1 EV
    resolve_action(state, action, params) -> list[Event]      # rolls seeded RNG
    off_ball_step(state, params)                               # §2.4 movement
    tick(state, params) -> list[Event]                         # one step
    play_match(doc_a, doc_b, players, weights, params, seed) -> MatchReport
    monte_carlo(doc_a, doc_b, ..., runs, seed) -> AggregateReport   # calibration
```

Reuse `TeamDoc`, `Placement`, `Player`, `position_mean_fits`, and `Player.fit` — no
schema change, still pure over two JSON docs + seed. `MatchReport` carries the final
score, the `list[Event]` log, and (Phase 2) the per-tick state frames.

### 5.2 The tick loop (v0 — smallest useful thing)

Deliberately crude first, to get an end-to-end match printing today:

1. Kick off; assign possession.
2. **Loop until 90:00:**
   - Find the ball-holder Agent.
   - `candidate_actions` → `score_action` each → pick best (later: softmax-sample).
   - `resolve_action`: roll seeded RNG vs success prob (from §4 Stat contests, jittered
     by `consistency`); on success move ball / advance; on failure flip possession.
   - If action was a shot: roll vs keeper → goal / save / miss; emit event, reset to
     kickoff or keeper distribution.
   - Roll fouls (`aggression`) and injuries (`injury_resilience`) on tackles.
   - Advance clock by the action's duration; decay stamina.
   - Append events.
3. Emit `MatchReport`.

**v0 simplifications that are fine to ship:** treat the pitch as ~6 coarse zones
instead of continuous metres; ignore true off-ball movement (Agents sit at anchors);
pass targets chosen among teammates in adjacent forward zones weighted by a baked xT
lookup. This alone produces a believable commentary and a scoreline.

### 5.3 Richer v1 (after v0 aggregates sanely to M1/M2)

- Continuous metre coordinates (§1.2).
- Real off-ball movement via an influence field (§2.4) — Agents seek high-xT,
  own-controlled space; defenders deny it.
- Pass safety from pitch control instead of the zone heuristic.
- Live chemistry per-pass buff (§4.4).
- Set pieces (corners/free kicks) as their own phase.

### 5.4 The text event log (the deliverable users see)

An `Event` has a clock, a kind, and pre-rendered text. Produce commentary like:

```
00:00  Kick-off. Bowser's XI get us underway.
00:14  Mario picks it up in midfield, looks up...
00:16  ...threads it wide to Peach on the right.
00:23  Peach drives at Ganondorf — beats him! (dribble 0.62)
00:27  Cross to Kirby, 8m out — SHOT...
00:27  ...tipped over by Bowser! Huge save (reflexes 4.5 vs shooting 3.0).
00:31  Corner to Mario's XI.
...
63:20  Fox goes into the book — reckless on Yoshi (aggression 4.0).
78:41  Donkey Kong limps off, looks like a hamstring (injury_resilience 1.5).
90:00  FULL TIME. Mario's XI 2–1 Bowser's XI  (xG 1.8–1.3)
```

Include the underlying numbers in parentheses behind a `verbose` flag — during
development they're gold for tuning, and they reinforce the "your Stats drive this"
story. A `MatchParams.commentary_detail` slider can dial verbosity.

### 5.5 Validation ideas (issue 009 acceptance criteria)

- **Seeded reproducibility:** same seed ⇒ identical `MatchReport`. Unit test asserts it.
- **M1/M2 consistency:** the §4.5 Monte Carlo bridge as a test — aggregate xG within
  tolerance of `expected_goals()` across fixture Teams.
- **Sanity invariants:** goals ≤ shots; possession sums to ~100%; no Agent leaves the
  pitch; a Team with an empty Defence concedes materially more (spatial fairness).
- **Monotonicity:** raising a Team's `shooting` Stats across the board should not
  _lower_ its average goals — a cheap property test that catches coefficient-sign bugs.
- **Determinism seam:** all randomness goes through `state.rng`; nothing calls the
  global `random`/`numpy` RNG. Makes the above tests possible.

---

## 6. Phase 2 — visuals (top-down 2D in a Streamlit app)

The key Streamlit fact: **Streamlit re-runs your whole script top-to-bottom on every
interaction.** It is not a game loop and fighting that is painful. So the golden rule:

> **Simulate first (record every tick's state into frames), then render the recording.
> Never drive the animation from the simulation live.**

Because §5's engine already produces per-tick state, Phase 2 is "draw a list of frames."

### 6.1 Options and tradeoffs

| Option | How | Streamlit fit | Effort | Verdict |
|---|---|---|---|---|
| **mplsoccer + matplotlib `FuncAnimation` → GIF/MP4** | Draw pitch once, animate 22 dots + ball over frames, export a video, `st.video`/`st.image` it | Excellent — render offline, display artefact; no rerun fight | Med | **Recommended default** — best-looking, uses the pitch lib you'd use anyway |
| **Plotly animated scatter** (`animation_frame`) | Put frames in a tidy DataFrame, Plotly gives play/pause + slider | Native `st.plotly_chart`; interactive scrubbing | Low | **Recommended for interactivity** — easiest, live in-browser |
| **`st.pyplot` in a loop with `time.sleep` + rerun** | Redraw each frame, sleep, rerun | Poor — janky, blocks, flickers | Low | Avoid except for a quick demo |
| **Custom HTML/Canvas Streamlit component** | Ship frames as JSON to a JS canvas/WebGL renderer | Best playback quality, most control | High | Only if you want FM-grade smoothness later |
| **pygame standalone window** | A separate desktop renderer reading the frame log | N/A in-browser | Med | Nice offline "match viewer"; not in the Streamlit page |

**Recommendation:** ship **Plotly animated scatter first** (fastest path to a moving
2D pitch with a scrub bar, zero video-encoding dependency), then upgrade to
**mplsoccer + `FuncAnimation` exported to MP4** for a polished "watch the match"
button. Both consume the exact same frame list. Interpolate between coarse ticks
(e.g. 1 Hz sim → 10 fps playback) for smoothness — a simple linear tween of positions.

### 6.2 Frame data contract

Keep Phase 1 and Phase 2 decoupled by defining the frame now: a `list[Frame]` where
`Frame = {t, ball: (x,y), agents: [{name, team, x, y, state}]}`. Phase 1 fills it;
Phase 2 renders it. This means the visualiser never touches the engine internals.

---

## 7. Staged roadmap (smallest useful → FM-level, with honest caveats)

| Stage | What you get | Effort | Honest note |
|---|---|---|---|
| **0. Frame contract + module skeleton** | `MatchParams`, dataclasses, seeded RNG seam | 0.5 day | Do first; unblocks everything |
| **1. v0 zone engine + text log** | A believable minute-by-minute commentary & scoreline from Fit/Stats | 2–4 days | **The big morale win** — a real match plays out in text |
| **2. Monte Carlo + M1/M2 calibration** | Tuned coefficients, regression tests, "consistent with M1/M2" ✓ | 1–2 days | Turns hand-waved numbers into defensible ones |
| **3. Hidden Stats live** | `consistency` variance, `aggression` fouls/cards, injuries | 1–2 days | Satisfies the core of issue 009 |
| **4. Continuous coords + static xT** | Ball progresses toward goal sensibly; metre pitch ready for viz | 2–3 days | Payoff/effort sweet spot for realism |
| **5. Plotly animated 2D pitch** | Watch the dots move; scrub bar | 1–2 days | First "wow" visual; Streamlit-native |
| **6. Influence field off-ball movement** | Runs into space, marking, pass safety | 3–5 days | Where it starts to _look_ like football |
| **7. mplsoccer MP4 match viewer** | Polished "watch match" export | 2–3 days | Diminishing returns begin here |
| **8. Sub-second physics, ball flight, set-piece detail, BTs** | FM-ish smoothness & richness | weeks–months | **Steep diminishing returns** |

### 7.1 The honest FM caveat

Football Manager's match engine is the product of a **large professional team over
~20 years**: a real-time continuous 3D physics engine, hundreds of interacting
attributes and roles, tactical instructions, morale/pressure systems, and years of
data-tuning. **You will not reach that, and you should not aim to.** A determined
hobbyist can very realistically reach **stages 1–6** and have something genuinely fun:
rating-driven, watchable, tunable, and clearly _your Characters_ playing. Stages 7–8
are where each increment costs disproportionately more for less perceived gain. The
right target is **"a believable, explainable, sliders-tunable match that visibly
reflects each Character's Stats,"** not "FM at home." Set expectations there and the
project stays fun instead of becoming a second job.

---

## 8. Sources (⚠ not live-verified this session — confirm before relying)

Engines / references:
- Google Research Football — `github.com/google-research/football`
- ESMS (Electronic Soccer Management Simulator) — search community mirrors / "ESMS++"
- Bygfoot football manager — `bygfoot.sourceforge.net` / community mirrors
- Basketball-GM / Football-GM (rating-driven possession sims, JS) — `github.com/dumbmatt/basketball-gm`, `github.com/dumbmatt/football-gm`

Decision math / analytics:
- socceraction (VAEP / xT / SPADL) — `github.com/ML-KULeuven/socceraction`
- Karun Singh, "Introducing Expected Threat (xT)" — `karun.in/blog/expected-threat.html`
- Friends of Tracking (pitch control, xT, pass models; Sumpter/Spearman) — `github.com/Friends-of-Tracking-Data-FoTD`
- William Spearman, "Beyond Expected Goals" / pitch control (research paper)

Visualisation:
- mplsoccer — `github.com/andrewRowlinson/mplsoccer` / `mplsoccer.readthedocs.io`
- Plotly animations (`animation_frame`) — `plotly.com/python/animations/`

Prior in-repo research this builds on:
- `docs/research/team-comparison-methods.md` (S1–L1a ladder, M1/M2, Dixon–Coles/Hattrick/FM/OOTP grounding)
- `docs/research/simulation-design-decisions.md` (`SimParams` defaults & rationale)
- `docs/issues/009-stochastic-match-engine.md` (acceptance criteria this plan satisfies)
