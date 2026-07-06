# Team-vs-Team Comparison & Match Simulation: Methods Research

_Research report for issue 004 (team-vs-team comparison). Uses the CONTEXT.md
vocabulary throughout: **Character**, **Stat**, **Category**, **Position**,
**Fit**, **Team**, **Placement**._

## Executive summary

We can rank the whole design space on a **small → medium → large scope** ladder,
from a static average of **Fit** scores up to a full stochastic match engine. The
single most important design fact is that a **Team** has free **Position** counts
(a "10 in attack, 0 defence" Team is buildable), so any purely additive or averaged
metric either rewards or punishes lopsided Teams for the wrong reasons. Real
football games solve this the same way: **EA FC** reports separate ATT/MID/DEF
line ratings, **Hattrick** literally pits each attacking sector's rating against the
opposing defensive sector, and the statistical literature (Dixon–Coles bivariate
Poisson, Elo, xG chains) reduces a team to an **attack strength** and a **defence
strength** and lets them meet. **Recommendation: ship the tentative per-Position
mean now as a baseline, then implement the ADR-0001 matchup model (Attack fed by
Midfield vs opponent Defence + Goalkeeper → expected goals) as the real answer.**
The matchup model is where fairness "emerges" instead of being bolted on, it is
directly grounded in how Hattrick and Poisson-xG models work, and it is a clean
staging point on the road to the eventual stochastic engine that `state_template.yaml`
was clearly authored for.

---

## Framing: what makes this hard

Three properties of our domain constrain every method below:

1. **Free Position counts.** A **Team** is 11 **Placements** with exactly one
   Goalkeeper and otherwise unconstrained counts. A metric must not make "10 in
   attack" look strong (mass) or weak (missing-line penalty) _by rule_ — the best
   designs let the weakness of an empty **Defence** show up naturally when it is
   tested against the opponent's Attack.
2. **Fit is the natural per-Placement input.** `Player.fit(weights)` already turns a
   Character's 0–5 **Stats** into a 0–5 suitability for a **Position**, hidden Stats
   excluded, weights editable/global in the `position_weight` table. Every method
   should consume Fit rather than re-deriving from raw Stats, so the editable-weights
   architecture keeps paying off.
3. **Teams are ephemeral JSON.** Per ADR-0001 there is no Team table. Any comparison
   must run in-session over two loaded JSON documents. This favours pure functions
   over Team state; it rules out anything needing persisted history (e.g. learned
   Elo) unless we synthesise ratings on the fly.

Two data assets are underused by the simplest methods and are the whole point of the
richer ones:

- **`link_up_partners`** — per-Character synergy list, described in
  `state_template.yaml` as "passing buffs". Chemistry, in EA FC terms.
- **Hidden Stats** `consistency` (per-match variance) and `injury_proneness` — by
  design excluded from Fit, and only meaningful once a method rolls dice.

---

## The scope ladder

### SMALL SCOPE

#### S1. Per-Position mean Fit + overall mean _(current tentative pick)_

**How it works.** For each of the four **Positions**, average the **Fit** of the
**Placements** assigned to that Position; also take the mean of all 11 Placements'
Fit as an overall number. Overlay the two Teams on the existing four-axis radar.

**Data consumed.** Fit only (per Placement, at its assigned Position). No synergy, no
hidden Stats.

**Effort/scope.** Trivial. A few lines over the loaded JSON; directly satisfies the
issue-004 acceptance criteria and the radar-overlay requirement. Fully pure, fits
ephemeral JSON perfectly.

**Pros.** Cheap, explainable, visualises natively on the radar, deterministic.

**Cons.** A **mean** hides squad depth and ignores that lines interact. It says
nothing about who beats whom.

**"10 in attack" fairness.** Handled _acceptably by accident_: the Defence axis is
computed over zero Placements → 0 (or undefined), so a defence-less Team visibly
craters on that axis. But an all-attack Team can still show a high Attack mean and
"win" the eye test on that axis, because the metric never tests Attack _against_ a
defence. Fairness is cosmetic, not structural.

**Synergy.** None. `link_up_partners` unused.

**Architecture fit.** Excellent. Pure function, editable weights flow straight
through Fit.

_Real-game analogue:_ this is essentially **EA FC's ATT/MID/DEF line ratings** —
averages of player overalls in each part of the pitch — minus their weighting
tweaks. ([FUTBIN](https://www.futbin.com/players),
[EA Forums](https://forums.ea.com/discussions/fc-24-general-discussion-en/how-are-the-team-ratings-for-each-part-of-the-squad-attmiddef-being-calculat/7731493))

#### S2. Per-Position sum Fit (mass-based)

**How it works.** Sum rather than average Fit per Position line.

**Data consumed.** Fit only.

**Effort/scope.** Trivial (swap `mean` for `sum`).

**Pros.** Rewards squad depth in a line.

**Cons.** **Actively broken for our domain.** More bodies = bigger number, so "10 in
attack" wins Attack by construction. Directly conflicts with the fairness
requirement.

**"10 in attack" fairness.** Fails — it _rewards_ the pathological build.

**Synergy.** None.

**Architecture fit.** Fine mechanically, wrong incentives. Include only as a
documented rejected option.

#### S3. Single overall Team number

**How it works.** One scalar per Team (mean of 11 Fits, or a weighted blend of the
line means), compared head-to-head.

**Data consumed.** Fit only.

**Effort/scope.** Trivial.

**Pros.** Dead simple ranking; good for a leaderboard.

**Cons.** Throws away all shape — a balanced Team and a lopsided one can tie. No
per-Position insight, no radar story.

**"10 in attack" fairness.** Poorly handled; a strong-but-unbalanced Team scores well.

**Synergy.** Could fold in a flat chemistry bonus, but crude.

**Architecture fit.** Fine, but under-delivers on the issue's per-Position + overall
requirement.

_Real-game analogue:_ **EA FC overall Squad Rating** (`SR = (SUM + CF) / 18` with an
above-average correction factor) and **Hattrick's HatStats**
(`3×Midfield + Attack + Defence`). Note both games _also_ keep the line breakdown —
nobody ships only the scalar. ([FIFA UTeam](https://fifauteam.com/fc-25-squad-rating-guide/),
[Hattrick Rating wiki](https://wiki.hattrick.org/wiki/Rating))

---

### MEDIUM SCOPE

#### M1. Matchup model → expected goals (xG) _(ADR-0001 intended direction)_

**How it works.** Reduce each Team to two derived strengths and let them meet, in
both directions:

- **Attack strength** = the Attack line's Fit, _supplied/amplified by_ the Midfield
  line (midfield creates the chances). E.g. `atk = f(mean Attack Fit, mean Midfield
  Fit)`.
- **Defence resistance** = Defence line Fit combined with the single Goalkeeper's Fit.
- Team A's Attack strength is tested against Team B's Defence resistance to yield an
  **expected-goals** number `xG_A`; symmetrically `xG_B`. Map the pair to a scoreline
  / win-draw-loss probability.

**Data consumed.** Fit per line (Attack, Midfield, Defence, Goalkeeper) — so all four
Positions matter and interact. `link_up_partners` enters as a **chemistry multiplier**
on Attack/Midfield (see below). Hidden Stats still excluded (they belong to L1).

**Effort/scope.** Medium. Pure functions over the two JSON docs; needs a small tuned
mapping (line strengths → xG). No persistence, no schema change. A day or two of work
plus tuning, testable with fixture Teams.

**Pros.** This is the design's sweet spot: it produces a **scoreline / probability**
users can read as "who wins", it makes the four Positions genuinely interdependent,
and it is the natural staging point before a full engine.

**Cons.** Needs a calibrated strength→xG curve (no ground truth data, so it is a
judgement call). Deterministic unless you add variance (that is L1's job).

**"10 in attack" fairness — the key win.** Fairness **emerges from the matchup**, not
from a rule. An all-attack Team has enormous Attack strength but ~zero Defence
resistance and no Goalkeeper contribution, so it concedes heavily: it might score 5
but ship 6. The metric punishes imbalance through the mechanic of being scored on,
exactly as ADR-0001 intends. This is precisely how **Hattrick** works — each attack
sector rating is compared to the _opposing_ defence sector, and midfield dominance
decides how many chances you even get. ([Hattrick Match engine](https://wiki.hattrick.org/wiki/Match_engine),
[Midfield](https://wiki.hattrick.org/wiki/Midfield))

**Synergy — the natural home for `link_up_partners`.** Count the link-up pairs that
are actually co-placed in the Attack/Midfield lines and apply a chemistry multiplier
to Attack strength. This mirrors **EA FC Ultimate Team chemistry**, where links between
compatible players raise effective ratings. ([FUTBIN players](https://www.futbin.com/players),
[Recharge FC26 squad builder](https://www.recharge.com/blog/en-gb/fc-26-squad-builder-ai-powered-chemistry-focused))

**Architecture fit.** Excellent — pure, in-session, editable weights flow through Fit
into the line strengths. The two xG numbers can still drive a radar overlay _plus_ a
headline scoreline.

_Statistical grounding:_ this is a lightweight, deterministic cousin of the
**Dixon–Coles bivariate Poisson** model, which reduces each team to an attack
parameter (expected goals scored) and a defence parameter (expected goals conceded)
and computes every scoreline from those. Our line-Fit values _are_ the attack/defence
parameters. ([Dixon–Coles / bivariate Poisson](http://article.sapub.org/10.5923.j.ajms.20201003.01.html),
[xG + Poisson modelling](https://www.jsr.org/index.php/path/article/download/1116/906/6318))

#### M2. Poisson scoreline distribution on top of M1

**How it works.** Take `xG_A`, `xG_B` from M1 as Poisson rate parameters and compute
the full probability grid of scorelines (0-0, 1-0, ...), hence P(win)/P(draw)/P(loss)
and an "expected points" number. Optionally use the **bivariate** form (a shared term
for correlated scoring / the low-score correction Dixon–Coles adds).

**Data consumed.** Same as M1 (the two xG numbers). No extra data — it is a
distribution _over_ M1's output.

**Effort/scope.** Small increment on M1 — a closed-form Poisson PMF, no simulation
loop. Deterministic and fully testable.

**Pros.** Turns a single scoreline into calibrated probabilities without a stochastic
engine; great for a "Team A wins 58%" readout and for ranking Teams by expected
points.

**Cons.** Poisson assumes goal independence and a specific variance; real football is
slightly over-dispersed (hence Dixon–Coles). For a hobby tool this is a non-issue.

**"10 in attack" fairness.** Inherits M1's emergent fairness.

**Synergy.** Inherits M1's chemistry multiplier.

**Architecture fit.** Excellent — still a pure function.

_Grounding:_ this is the standard **Poisson / bivariate-Poisson goal model** used
across the prediction literature and by open-source tournament models (Elo →
Dixon–Coles → Monte Carlo). ([Bivariate Poisson study](http://article.sapub.org/10.5923.j.ajms.20201003.01.html),
[World Cup 2026 model repo](https://github.com/Hicruben/world-cup-2026-prediction-model))

#### M3. Role-weighted line ratings (FM-style attribute weighting)

**How it works.** Instead of one weight set per coarse Position, keep the FM idea of
_per-role_ attribute weights so that, when Position is later refined to named
positions (CB/ST/…), each named position gets its own weighting — a finer Fit.
Line ratings then aggregate named-position Fits. This is not a comparison method by
itself; it is a **refinement of the Fit input** that M1/M2 consume.

**Data consumed.** Raw Stats via extra weight sets; still surfaces as Fit.

**Effort/scope.** Medium, and _optional/future_. It is mostly a data/weights change
plus the named-Position refinement CONTEXT.md already anticipates ("lines" become
groupings of positions).

**Pros.** Sharper per-Placement inputs; keeps the door open to named positions
without changing the comparison math above it.

**Cons.** More weights to author and tune; premature before the coarse model is
proven.

**Fairness / synergy / architecture.** All inherited from whatever comparison method
sits on top (M1/M2). Fits the `position_weight` table pattern directly — just more
rows.

_Grounding:_ **Football Manager** gives each player a per-role star rating from
weighted key/preferable attributes, and since FM21 the editor exposes per-position
attribute weights — the same pattern as our `position_weight` table, one level finer.
([FM role abilities](https://www.fmscout.com/a-guide-to-player-role-abilities-in-football-manager.html),
[FM Current Ability guide](https://www.fmscout.com/a-guide-to-current-ability-in-football-manager.html),
[Attributes explained](https://www.passion4fm.com/football-manager-player-attributes/))

---

### LARGE SCOPE

#### L1. Full stochastic match engine _(the `state_template.yaml` endpoint)_

**How it works.** Simulate a match event-by-event: contest possession (midfield
battle), generate chances, take shots (`shooting` vs Goalkeeper `reflexes`/`handling`/
`positioning_gk`), award fouls/cards from `aggression`, apply per-match variance from
`consistency`, and roll injuries from `injury_proneness` during heavy tackles / low
`stamina`. Run once for a narrative match, or **Monte Carlo** it thousands of times
for a probability distribution. Every Stat description in `state_template.yaml` maps to
a mechanic here — this data was authored for exactly this.

**Data consumed.** _Everything._ All 0–5 Stats (not just those in Fit), both hidden
Stats (`consistency`, `injury_proneness` finally do work), `link_up_partners` as a
live passing buff, and Fit as a convenient per-Placement summary where a full stat
contest is overkill.

**Effort/scope.** Large. A real state machine (possession → zone → chance → shot →
save/goal/rebound → set pieces → cards → injuries), tunable probabilities, an RNG
seam for reproducible tests, and Monte Carlo aggregation. Weeks, not days. Still runs
in-session over two JSON docs, so it stays compatible with ephemeral Teams.

**Pros.** Maximum richness and narrative ("Mario booked in the 63rd, Kirby limps off").
Uses the whole dataset. Monte Carlo gives honest win probabilities. This is the
game the data was built for.

**Cons.** Heaviest to build, hardest to tune and to keep _fair_ and _stable_,
slowest to run (mitigate with a seed + capped iterations). Overkill for the immediate
issue-004 need of "compare two Teams". Determinism requires a seeded RNG or you lose
testability.

**"10 in attack" fairness.** Best-in-class and fully emergent: an all-attack Team
loses midfield battles, gets countered into an empty defence, and its lone specialist
concerns evaporate — the scoreline tells the truth with no fairness rule at all.

**Synergy.** Richest possible: `link_up_partners` buffs each simulated pass between
co-placed partners, not just a flat multiplier.

**Architecture fit.** Compatible (pure over two JSON docs, seeded RNG) but a large new
subsystem. Wants its own module and a strong test harness.

_Grounding:_ this mirrors **Hattrick's** possession→zone→attack-vs-defence loop taken
to full event resolution, **Football Manager's** per-event attribute calculations, and
the **OOTP** philosophy of _ratings-driven_ (not stats-driven) simulation — OOTP even
carries a literal `injury_proneness`-style rating and randomises within it, which is
strikingly close to our hidden Stats. Monte Carlo aggregation is the standard way such
engines produce probabilities. ([Hattrick match engine](https://wiki.hattrick.org/wiki/Match_engine),
[FM attributes in match](https://www.passion4fm.com/football-manager-player-attributes/),
[OOTP ratings-based sim](https://grokipedia.com/page/Out_of_the_Park_Baseball),
[Monte Carlo World Cup sim](https://vegeorge94.medium.com/monte-carlo-simulation-of-2022-fifa-world-cup-fa9c08b9e652))

#### L1a. Markov-chain / possession-flow variant

A lighter large-scope option: model the match as a **Markov chain** over pitch zones
(build-up → final third → shot → goal/turnover), with transition probabilities driven
by line Fit and chemistry. Cheaper than full event simulation, richer than M2, and it
yields xG analytically (steady-state) or by simulation. A reasonable "L1 without the
narrative" if the full engine proves too costly. ([Markov/possession modelling context](https://www.sciencedirect.com/science/article/abs/pii/S0169207009001708))

---

## Comparison table

| Method | Scope | Data needed | "10 in attack" fairness | Synergy (`link_up_partners`) | Effort | Real-game analogue |
|---|---|---|---|---|---|---|
| S1 Per-Position mean Fit + overall | Small | Fit only | Cosmetic (empty line shows 0; attack still flatters) | None | Trivial | EA FC ATT/MID/DEF lines |
| S2 Per-Position sum Fit | Small | Fit only | **Fails** — rewards mass | None | Trivial | (rejected) |
| S3 Single overall number | Small | Fit only | Poor — imbalance can win | Flat bonus at best | Trivial | EA FC Squad Rating, Hattrick HatStats |
| M1 Matchup → xG | Medium | Line Fit (all 4 Positions) + chemistry | **Emergent** (scored on) | Multiplier on Attack/Mid | Medium | Hattrick sectors; Dixon–Coles params |
| M2 Poisson scoreline dist. | Medium | M1's two xG numbers | Emergent (via M1) | Via M1 | Small on top of M1 | Bivariate Poisson / xG models |
| M3 Role-weighted Fit (future) | Medium | Extra weight sets | Inherited | Inherited | Medium (optional) | FM role/attribute weighting |
| L1 Stochastic engine | Large | **All Stats + hidden + synergy** | Best, fully emergent | Live per-pass buff | High | Hattrick/FM/OOTP + Monte Carlo |
| L1a Markov possession | Large | Line Fit + chemistry as transitions | Emergent | Transition modifier | Med-High | Possession/Markov models |

---

## Recommended staged path

The methods are a genuine ladder — each stage produces a working comparison and feeds
the next.

1. **Ship S1 now** (per-Position mean Fit + overall mean, radar overlay). It satisfies
   every issue-004 acceptance criterion immediately, gives users a visual, and costs
   almost nothing. Label it explicitly as the **baseline**, not the final answer.
2. **Build M1 (matchup → xG) next** as the real comparison. This is ADR-0001's stated
   intent, it is where the "10 in attack" problem solves itself, and it is directly
   grounded in Hattrick and Dixon–Coles. Reuse the S1 line means as its inputs, so S1
   is not thrown away — it becomes the raw material for M1.
3. **Layer M2 (Poisson scoreline distribution) on M1** cheaply to turn a single xG pair
   into P(win)/P(draw)/P(loss) and expected points. Small increment, big
   interpretability gain.
4. **Introduce `link_up_partners` as a chemistry multiplier** at the M1/M2 stage (count
   co-placed partners in Attack/Midfield). Keep it a single tunable coefficient at
   first.
5. **Defer M3 and L1.** Treat M3 (finer role weights) as the companion to the future
   named-Position refinement CONTEXT.md anticipates. Treat L1 (stochastic engine) as
   the long-term endpoint the Stats were authored for — start it only once M1/M2 have
   proven the strength model and only with a seeded RNG + test harness. L1a (Markov) is
   the fallback if full event-sim is too costly.

### Concrete next step for issue 004

Resolve the HITL decision **in favour of shipping S1 as an explicit baseline while
committing to M1 as the target model.** Update the issue-004 checkbox "Decision
recorded" accordingly. Then, when M1 is designed and locked, **update ADR-0001**: its
Consequences section currently says the comparison method "is not yet locked" and
sketches the matchup model as intended direction — record M1 (Attack fed by Midfield vs
opponent Defence + Goalkeeper → xG, with `link_up_partners` as a chemistry multiplier,
Poisson scoreline layer optional) as the accepted method, note S1 as the shipped
baseline it supersedes, and flag L1 as the deferred long-term endpoint.

---

## Sources

- EA FC line ratings (ATT/MID/DEF): [EA Forums](https://forums.ea.com/discussions/fc-24-general-discussion-en/how-are-the-team-ratings-for-each-part-of-the-squad-attmiddef-being-calculat/7731493), [FUTBIN](https://www.futbin.com/players)
- EA FC squad rating formula & chemistry: [FIFA UTeam FC25 guide](https://fifauteam.com/fc-25-squad-rating-guide/), [Recharge FC26 squad builder](https://www.recharge.com/blog/en-gb/fc-26-squad-builder-ai-powered-chemistry-focused)
- Football Manager attributes / role ability / weighting: [FM role abilities](https://www.fmscout.com/a-guide-to-player-role-abilities-in-football-manager.html), [FM Current Ability](https://www.fmscout.com/a-guide-to-current-ability-in-football-manager.html), [Attributes explained](https://www.passion4fm.com/football-manager-player-attributes/)
- Hattrick match engine (sector matchups, midfield battle, HatStats): [Match engine](https://wiki.hattrick.org/wiki/Match_engine), [Midfield](https://wiki.hattrick.org/wiki/Midfield), [Rating](https://wiki.hattrick.org/wiki/Rating), [Decoding Hattrick (arXiv)](https://arxiv.org/pdf/2504.09499)
- OOTP ratings-driven simulation (incl. injury-proneness rating): [Grokipedia OOTP](https://grokipedia.com/page/Out_of_the_Park_Baseball), [OOTP simulation manual](https://manuals.ootpdevelopments.com/index.php?man=ootp16&page=simulation_module)
- Bivariate Poisson / Dixon–Coles goal models: [Predictive modelling with bivariate Poisson](http://article.sapub.org/10.5923.j.ajms.20201003.01.html), [xG + Poisson](https://www.jsr.org/index.php/path/article/download/1116/906/6318), [Poisson regression results](https://www.mdpi.com/2076-3417/14/16/7230)
- Elo + Monte Carlo match simulation: [Elo for match prediction (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S0169207009001708), [Monte Carlo World Cup sim](https://vegeorge94.medium.com/monte-carlo-simulation-of-2022-fifa-world-cup-fa9c08b9e652), [Elo+Dixon-Coles+Monte Carlo model](https://github.com/Hicruben/world-cup-2026-prediction-model)
