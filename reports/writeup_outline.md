# What Combine sensors add — and don't
### A measurement audit of Combine tracking against three NFL seasons

*Draft outline v0 — 2026-10-07. Target ≤2,000 words, ≤9 figures/tables. Every number below is from `data/derived/` and reproducible via the Makefile.*

---

## 0. One-paragraph pitch (for the two of us)
Everyone else will build a new sensor metric and claim it predicts the NFL. We ask the prior question: **which Combine sensor measurements are reliable enough to rate a player, and which of them transfer to Sundays — beyond what the stopwatch and the draft board already know?** The answers are clean, mostly non-obvious, and directly actionable for a scouting department: trust these numbers, ignore those, and stop expecting new information from re-timing the 40.

## 1. Introduction (~200 words)
- Combine evaluation = stopwatch + tape measure for decades; optical tracking now records every drill at 10 Hz.
- The host's question: where does tracking add context? Our framing: a sensor metric is useful only if it is (a) repeatable, (b) not redundant with what we already measure, (c) linked to NFL movement or production.
- Data: 510 prospects (2023–25), 6,310 drill attempts, 8.8M in-game frames, per-snap NGS production metrics. Regular season only unless stated.

## 2. The 40 is a top-speed test (~250 words) — **Fig 1**
- Mono-exponential sprint fit per attempt (793 runs; median RMSE 0.16 yd/s). Model-implied 40 time vs official clock r = 0.945.
- **Sensor top speed vs official 40 time: r = −0.965.** 93% of the variance in the stopwatch number is top speed.
- Acceleration (speed at 10 yd given top speed) is a small, separate component: ICC 0.92 for v10 but it explains little once vmax is known.
- Fig 1A: median speed-distance curves by position — curves are near-parallel; positions differ in ceiling, not shape.
- Implication: tracking the 40 re-measures the stopwatch. Decomposing it is interesting physiology, not new scouting information (Section 5 tests this).

## 3. Which drills can be measured at all? (~300 words) — **Fig 2**
- Test-retest ICC for every sensor feature on every drill with ≥2 attempts per player (375 players on the 40, 119 on the DB transition drill, 137 on the Gauntlet…).
- Reliable (ICC ≥ 0.8): 40 top speed (0.98), DB back-pedal-transition drill time (0.90), its trough speed (0.84) and max accel (0.81).
- Moderate (0.5–0.75): 40 and Gauntlet split times, PASS_RUSH_DRILL trough speed (0.71).
- Unreliable (< 0.5): nearly every other position-drill feature — Line Drill, Short Shuttle, Short Zone Breaks, Pass Rush Drop, Three-Cone speed features.
- Worked example — Run-the-Hoop (DL): one rep per player, so reliability is undefined; its curvature "bend index" does not correlate with in-game curvature at speed (r ≈ 0.1) or with pressure (r ≈ 0.1) — **Fig 5**.
- Implication: a single rep of most position drills is noise. Either add reps or stop using those numbers for evaluation.

## 4. Does Combine movement show up in game movement? (~300 words) — **Fig 3**
- Outcome: each player's in-game top speed (95th pct of per-play max) and max acceleration, from all tracked plays.
- Nested leave-one-out models within position group: weight + draft slot → + stopwatch → + sensor.
- In-game top speed is only moderately predictable within position: WR R² 0.37, EDGE 0.20, TE 0.08, IDL/OL/DB ≈ 0.
- **Sensor adds nothing over the stopwatch** in any group (ΔR² ≈ 0). In-game acceleration is essentially unpredictable from the Combine.
- Implication: within a position, how fast a player runs on Sundays is mostly not a Combine question.

## 5. Does Combine speed predict production? (~300 words) — **Fig 4, Fig 6**
- One row per player, robust OLS, standardized effects with 95% CIs, adjusted for weight and draft slot. Nine group×outcome cells.
- Two signals, seven nulls:
  - IDL pressure rate rises with 40 speed (stopwatch +0.97 SD; sensor top speed +0.55 SD; n=22).
  - WR YAC over NGS-expected **falls** with top speed (−0.46 SD; n=44). xYAC already prices in speed at the catch, so the residual rewards what the 40 doesn't measure.
  - EDGE pressure/quick-pressure/sack, OL pressure allowed, WR separation-over-expected and EPA/target: CIs span zero.
- Methods note (one sentence, DS-score bait): a snaps-as-trials binomial GLM gives p < .01 on the EDGE cells — it is wrong (player-level overdispersion); the player-level model is what we report.

## 6. What a scouting department should do with this (~250 words)
1. Treat the sensor 40 as the stopwatch 40 — don't pay for a second number.
2. Pull reliable drill features only: 40 top speed; DB transition time/trough/accel; Gauntlet splits. Discard single-rep agility features or demand 2+ reps.
3. For interior DL, straight-line speed remains the Combine's most transferable trait.
4. For receivers, use top speed to set YAC expectations, not to project YAC over expectation.
5. "Bend" is not measurable from the current hoop drill.

## 7. Limitations (~150 words)
- n per cell 22–94; draft classes have 1–3 seasons of exposure; survivorship (no game data for players who never played); in-game movement is situational; career outcomes confounded by draft slot (we adjust for it); only cohort players are tracked in games (no opponents).

## Figure list (≤9)
| # | File | Content | Status |
|---|---|---|---|
| 1 | fig1_forty_curves.png | A: median speed curves by group; B: vmax vs official 40 (r −0.965) | done |
| 2 | fig2_reliability.png | ICC heatmap drills × features | done |
| 3 | fig3_nested_r2.png | LOO-R² bars: controls / +stopwatch / +sensor, by group | done |
| 4 | fig4_production_forest.png | Standardized production effects, 9 cells × 3 features | done |
| 5 | fig5_hoop_null.png | Hoop bend index vs in-game curvature & pressure | done |
| 6 | fig6_yac_paradox.png | WR YAC-oe vs top speed | done |
| 7 | report_card.csv → table/figure | Combine Sensor Report Card: ICC · reps to 0.8 · redundancy · transfer · verdict (67 rows; show the ~30 non-DON'T-USE rows) | data done, figure todo |
| 8 | hoop drill path / speed-curve anatomy | one illustrative tracking figure for the reader who hasn't seen the data | optional |

## Open questions for the two of us
- Is a mostly-"negative" audit a winning Big Data Bowl entry? Judges score "would teams use this week-to-week" — the recommendations section has to carry that.
- Should the DB transition drill (the one reliable position drill) get its own section? It has no production outcome in the data, only in-game lateral accel (ρ ≈ 0.3).
- Appendix notebook: one public Kaggle notebook that regenerates every figure from the CSVs. Who owns it?

## Rubric scorecard — our own grading, host weights (Football 30 / DS 30 / Writeup 20 / Viz 20)
Scores 0–10 as a skeptical NFL-club analyst would give them *today*, on evidence in hand. Weighted = Σ score × weight / 10.

| Direction | Football (30) | Data Science (30) | Writeup (20) | Viz (20) | **Weighted /10** | Why |
|---|---|---|---|---|---|---|
| **A. Measurement audit: "what sensors add — and don't"** (Sections 2–6) | 6 | 8 | 7 | 8 | **7.2** | Football: actionable *as policy* (which numbers to trust, how many reps) but not a week-to-week metric; "uniqueness" high. DS: reliability + nested OOS models + honest nulls + the overdispersion catch; loses points for n=22–44 cells. Viz: heatmap, forest, nested bars are strong forms. |
| B. IDL straight-line speed → pressure (Section 5 cell) | 5 | 4 | 6 | 6 | 5.1 | Real effect (+0.97 SD) but n=22 and the stopwatch already has it — nothing new to buy. |
| C. WR YAC-over-expected paradox (Fig 6) | 5 | 5 | 6 | 7 | 5.6 | Non-obvious and tidy, but a single scatter; model-artifact risk (xYAC prices speed). Works as a section, not a paper. |
| D. Hoop-drill bend → pressure (original pick) | 3 | 4 | 5 | 6 | 4.3 | Null result on 1-rep drill; only survives as the worked example inside A. |
| E. DB transition drill (only reliable position drill) | 4 | 5 | 5 | 6 | 4.9 | ICC 0.90, 119 players × 2 reps — but no DB production metric in the data; movement-to-movement ρ ≈ 0.3. Appendix. |
| F. Route break → separation-over-expected | 2 | 4 | 4 | 5 | 3.6 | All partials ≈ 0 after modeling route/depth/cushion/coverage. Drop. |
| G. "Sensor beats stopwatch" (my earlier #1, retracted) | 5 | 2 | 5 | 7 | 4.5 | Would have been a false claim — ΔR² ≈ 0. Listed so we remember why it died. |
| H. OL drills → pass protection | 2 | 3 | 4 | 5 | 3.3 | Noise. Drop. |

**Where A loses points and how to buy them back**
- Football 6→7: add a concrete "Combine report card" artifact — for each drill feature, a trust tier (reliable / moderate / don't use) and the one position it transfers for. That is something a scout uses.
- DS 8→9: bootstrap the ICCs and the ΔR² so every headline number carries an interval; pre-register the nine production cells so the forest plot can't be accused of cherry-picking.
- Writeup 7→8: lead with the three recommendations, not the nulls; the word "negative" never appears.
- Viz 8→9: one anatomy figure (a real 40 track with the fitted curve, and a hoop path) so a reader who has never seen tracking data gets it in five seconds.

**Alternatives worth one more cheap test before we commit (≤2 h each)**
1. DB transition drill → in-game change-of-direction signature on coverage snaps (we have `coverage_assignment`; outcome = DB's own decel/re-accel near `pass_forward`). If ρ > 0.4 it earns a section and lifts Football.
2. Gauntlet splits (ICC 0.57–0.69) → WR in-game top speed / YAC-oe. Cheap; if null, it strengthens Section 4's claim.
3. Within-player Combine→game *speed gap* (game top speed − Combine vmax) by position: a "game speed" index. Descriptive, viz-friendly, no inference needed; could be Fig 7.
