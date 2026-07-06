# Simulation design decisions

What I built for the team-vs-team epic, the decisions I made, and why — so you and
your friends can tweak the numbers later. Everything tunable lives in
`SimParams` in `simulation.py` and is exposed as sliders on the **Team vs Team**
page. Vocabulary per CONTEXT.md (Character, Position, Fit, Team, Placement).

## What shipped

- **S1 — baseline** (issue 004): per-Position mean Fit + overall mean, radar overlay
  and a per-line table. Kept as a quick static read.
- **M1 — matchup → expected goals** (issue 005): the real verdict.
- **M2 — Poisson outcome** (issue 006): P(win/draw/loss), likely score, expected points.
- **Chemistry** (issue 007): `link_up_partners` boost in the creative lines.

## What I deferred, and why

- **008 — role-weighted Fit / named positions:** deferred. It expands the Position
  model, the builder UI, and the glossary — a genuine product step that cuts against
  "simplicity wins". The coarse four-Position model is the everyday tool.
- **009 — full stochastic match engine:** deferred. M1+M2 already give a scoreline
  and probabilities at a fraction of the complexity. This stays the long-term
  endpoint the hidden Stats (consistency/aggression/injury_proneness) were built for.

Both are ready-to-pick-up issues; nothing about the current design blocks them.

## The model, in plain terms

Football isn't "my midfield vs your midfield" — it's my attack against your defence.
So each Team is reduced to two numbers, and they meet:

1. **Attack rating** = its Attack Fit, supplied by its Midfield.
   `attack = (att·attack_weight + mid·midfield_supply_weight) / (attack_weight + midfield_supply_weight)`
   then multiplied by the chemistry boost.
2. **Resistance** = its Defence + Goalkeeper, shielded by its Midfield.
   `resistance = (def·defence_weight + gk·goalkeeper_weight + mid·midfield_shield_weight) / (sum of those weights)`
3. **Expected goals**, each direction:
   `xG_A = max(xg_floor, base_xg + slope·(attack_A − resistance_B))`
4. **Outcome:** goals ~ Poisson(xG); combine both sides over a 0–10 score grid to get
   P(win/draw/loss), the most likely scoreline, and expected points (3·win + draw).

**Why "10 in attack" loses without a rule:** a Team with no defenders and no midfield
has near-zero `resistance` (only the keeper contributes), so the opponent's xG
balloons; and its own `attack` is docked because midfield supply is 0. The imbalance
punishes itself — exactly how Hattrick's sector matchups and Dixon–Coles attack/
defence-strength Poisson models behave.

## Chemistry

`link_up_partners` is per-Character synergy ("passing buffs"). We count unique
partner **pairs both placed in the creative lines** (Midfield or Attack) and boost
that Team's attack rating by `chemistry_per_link` per pair. Kept to the creative
lines because the data frames synergy as passing/attacking, and kept as a single
coefficient for simplicity. EA FC's Ultimate Team chemistry is the analogue.

## Default coefficients (all slider-tunable)

| Param | Default | Meaning | Raise it to… |
|---|---|---|---|
| `base_xg` | 1.3 | goals for an evenly-matched game | make games higher-scoring |
| `slope` | 0.55 | how hard a strength gap swings xG | reward dominance more |
| `xg_floor` | 0.05 | minimum xG (there's always a chance) | — |
| `attack_weight` | 1.0 | attack line's share of attack rating | — (anchor) |
| `midfield_supply_weight` | 0.5 | how much midfield feeds the attack | make midfield matter more going forward |
| `defence_weight` | 1.0 | defence's share of resistance | — (anchor) |
| `goalkeeper_weight` | 0.6 | keeper's share of resistance | make a great keeper decisive |
| `midfield_shield_weight` | 0.4 | midfield's defensive contribution | reward midfield control |
| `chemistry_per_link` | 0.05 | attack boost per creative link-up pair | make synergy swingy |

Only a subset (base_xg, slope, midfield supply, goalkeeper share, chemistry) is on
the page as sliders to avoid overwhelm; the rest are easy to expose later.

## Honest caveats

- **No ground truth.** The strength→xG mapping is hand-calibrated intuition, not
  fitted to data. The sliders exist precisely so you can tune it to feel right.
- **Independent Poisson** slightly under-counts draws (the Dixon–Coles correction
  fixes this); skipped for simplicity.
- **Score grid truncated at 10 goals**, so probabilities sum to ~0.999999 — negligible.
- Sliders are **session-only** (not persisted). If you want to save a preferred set,
  that's a small follow-up (store in the DB or a JSON preset).
