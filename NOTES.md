# NOTES.md — decision log

Source of truth for decisions. Newest at top. Format: date · who · decision · why.

## Open items
- [ ] **DIRECTION DECISION (Ashwin + Joon, 2026-10-07 evening):** adopt the measurement-audit story ("What Combine sensors add — and don't") with the Report Card as centerpiece? See "Usability layer" + `reports/writeup_outline.md` scorecard.
- [ ] Cheap tests before locking (≤2 h each): (a) DB transition drill → in-game change-of-direction on coverage snaps; (b) Gauntlet splits → WR outcomes; (c) game-speed index figure for WR/TE only.
- [ ] Fig 7 = Report Card figure; bootstrap CIs on ICCs and ΔR².
- [ ] Public Kaggle notebook that regenerates every figure from `data/derived/*.csv` (owner: TBD).
- [x] Joon on the Kaggle team and the GitHub repo (2026-10-07).
- [x] Kaggle team formed (Ashwin joined, invite sent). Data downloaded, converted.
- [x] Gate passed (see below). Linkage v0 run.

## Broad screen (2026-10-07) — what the Combine tracking actually predicts
Code: `features.py` (generic kinematics for every drill + test-retest ICC), `outcomes_all.py` (all groups: pass rush, pass pro, receiving incl. separation-over-expected and YAC-over-expected, in-game top speed/accel from 8.8M frames, career), `screen.py` (4,637 partial-Spearman tests controlling weight + draft pick, BH-FDR per group). Outputs in `data/derived/{drill_reliability,screen}.csv`.

**Reliability (ICC, players with ≥2 attempts):** 40-yd dash top speed 0.985 (n=375); DB BACK_PEDAL_AND_TRANSITION duration 0.90, trough speed 0.84, max accel 0.81 (n=119); 40 t_20yd 0.73; Gauntlet t_20yd 0.69; PASS_RUSH_DRILL trough speed 0.71. Almost everything else < 0.5 → a single rep of most position drills is mostly noise. Hoop drill = 1 rep, unmeasurable.

**Survivors (q<0.10, |ρ|>0.3): 23 of 4,637.** Nothing for EDGE pressure, OL pass pro, or receiver separation-over-expected.
- Combine → in-game top speed (ig_s_p95), partial ρ, tracking vs stopwatch: WR s_peak +0.41 vs forty −0.37; TE s_peak +0.53 vs forty −0.44; EDGE first-second accel (a_mean_1s) +0.41 / t_10yd −0.33 vs forty −0.23 / ten split −0.14; DB ≈ 0.2 both; OL/IDL ≈ 0.1–0.25. → **Sensor beats stopwatch, and *which* part of the 40 matters is position-specific (top speed for WR/TE, acceleration for EDGE).**
- WR YAC over expected vs 40 top speed: −0.54 (q 0.044). Faster WRs underperform NGS xYAC. Likely because xYAC already prices in speed at the catch → the residual rewards elusiveness/vision, which no Combine drill measures. Non-obvious; must be framed carefully.
- IDL pressure rate (n=24): tracking t_10yd −0.61, 40 a_max +0.56, lateral wave-drill speed +0.53, 3-cone −0.81 (n≈10). q 0.30 — suggestive only.
- DB transition drill → in-game lateral accel +0.32 (q 0.09). Movement-to-movement only; the data has no DB production metrics.

## 40-yd dash decomposition + nested translation models (2026-10-07, later)
Code: `forty.py` (mono-exponential sprint fit per attempt: vmax, tau, model splits, v10/v20), `translation.py` (nested LOO-R² models: controls / +stopwatch / +sensor / +both, by group; stage-2 production). Outputs `data/derived/forty_*.csv`, `translation_stage{1,2}.csv`.
- Fit quality: median RMSE 0.16 yd/s over 793 attempts. Model-implied 40 time vs official forty r = 0.945 (+0.26 s offset: tracking onset precedes the clock). **vmax vs official forty r = −0.965** → the stopwatch 40 is a top-speed test. ICC: vmax 0.96, v10 0.92, v20 0.98, t40 0.87; tau 0.34 (unusable). Acceleration = v10 residualized on vmax.
- **Stage 1 correction:** with proper nested models the sensor does NOT beat the stopwatch for in-game movement in any group (LOO-R² difference ≈ 0 everywhere). Within-group predictability of in-game top speed is low anyway: WR 0.37, EDGE 0.21 (mostly weight/draft), OL/IDL/DB/TE ≈ 0. In-game accel metrics ≈ unpredictable from the Combine. The earlier screen read ("sensor +0.41 vs stopwatch −0.37") was noise — retracted.
- **Stage 2 (production):** EDGE pressure rate (n=31): vmax β=+0.19/SD (p .002) AND acceleration-independent-of-top-speed β=+0.13/SD (p .009); sensor deviance 76.7 < stopwatch 79.5 < controls 85.9. EDGE quick-pressure: same pattern (accel_resid p .017). IDL (n=22): both significant but stopwatch fits better. WR YAC-oe: vmax β −0.37 (p .007) but the single stopwatch forty predicts it better out of sample. OL pressure allowed: nothing.

## DB transition drill → in-game change of direction (2026-10-07, late) — `db_transition.py`
- In-game COD signature per DB on coverage snaps (REG, snap → pass_arrived): max decel at speed, max re-accel, lateral accel, trough ratio; medians over ≥40 plays. 74 DBs with the drill; 64 with the 40 too.
- **Null.** Nested LOO-R² for all four in-game COD outcomes is *lower* with the drill features than with controls alone (e.g. decel −0.05 → −0.15). The only reliable position drill does not predict measurable game movement.
- Career-snap correlations (drill max accel −0.36, p .002) point the wrong way and mix CB/FS/SS roles — not claimed.
- **Paper point: reliable ≠ valid.** Report Card verdicts now split "RELIABLE + TRANSFERS" vs "RELIABLE, transfer unproven". Today nothing earns the former.
- ICCs now carry bootstrap 95% CIs (`drill_reliability.csv`), shown on Fig 8 (Report Card figure).

## Scout-facing layer (2026-10-07, late) — `usability.py`, fig7
- **Measurement error per feature** (`measurement_error.csv`): SEM = SD·√(1−ICC); 90% one-rep band; minimum detectable difference MDD = 1.96·√2·SEM; both also in within-position percentile points. Headline: one-rep 90% band is ±8 pctile pts for 40 top speed, ±18 for the DB transition features, ±29–44 for everything else usable. MDD: two prospects must differ by 18 pctile pts on top speed, 37–52 on most other features, before the gap is real.
- **Prospect cards with bands** (`prospect_cards_bands.csv`, 475 players × 20 features): value, within-group percentile (time features flipped so higher = better), percentile band shrinking with reps (SEM/√k). Fig 7 = one card; the sell for usability.
- **Hidden-talent test** (`hidden_talent.csv`): residual(feature | draft pick, class) vs residual(career snaps / starts | draft pick, class), 56 cells. Best p = .028 → chance. Combine sensors do not identify players who out-play their draft slot in this data. State it plainly in the writeup; the brief asks.

## Usability layer (2026-10-07, evening) — `reportcard.py`
Ashwin's steer: the entry lives or dies on how usable it is. Built three artifacts:
- **Combine Sensor Report Card** (`data/derived/report_card.csv`): 67 drill×feature rows. ICC, Spearman-Brown reps to reach ICC 0.8, redundancy with stopwatch, incremental transfer to game speed over (weight, draft, forty), best production link, verdict. Tally: USE 3 (all DB back-pedal-transition: time, trough speed, max accel) · REDUNDANT with stopwatch 2 (40 top speed, trough) · USE WITH 2–4 REPS 15 · NEEDS 5–6 REPS 11 · DON'T USE 36. Incremental transfer to in-game speed over the stopwatch ≈ 0 for every feature.
- **Prospect cards** (`prospect_cards.csv`): 510 players × trusted features as within-position percentiles. Currently only the 3 DB features qualify — which is itself the message.
- **Game-speed index** (`game_speed_index.csv`): in-game top speed residual on Combine vmax within group. Within-group r is low (WR 0.48, TE 0.45, EDGE 0.28, DB 0.20, OL 0.17, IDL 0.06) → only meaningful for WR/TE; OL/IDL top speed is role-driven. Use as a descriptive figure for skill positions only.
- Writeup implication: Section 6 becomes the report card itself (Fig 7), and the recommendations to the league office are concrete rep counts per drill.

## Stage-2 retraction + figures (2026-10-07, evening)
- **Retracted:** the EDGE pressure "sensor acceleration" result. The snaps-as-trials binomial GLM ignores player-level overdispersion; player-level robust OLS gives vmax p=0.50, accel_resid p=0.43 (n=31). Stage 2 now = one row per player, OLS HC3 + snap-weighted WLS, standardized betas with CIs (`translation_stage2.csv`).
- Surviving production signals: IDL pressure ↑ with 40 speed (stopwatch +0.97 SD, sensor vmax +0.55 SD, n=22); WR YAC-oe ↓ with top speed (−0.46 SD, n=44). Seven other cells null.
- Six figures rendered in `reports/figures/` (fig1–fig6); writeup outline + rubric scorecard in `reports/writeup_outline.md`. Audit story scores 7.2/10 on our own rubric grading; next-best alternative 5.6.

## Direction ranking vs judging rubric — REVISED after nested models
**Story that the data actually supports: "What Combine sensors add — and don't."**
1. The 40 is top speed (r² .93 vs stopwatch); re-timing it with sensors adds no incremental validity for game speed. (Non-obvious, clean, big n.)
2. Most position drills are not reliable enough to evaluate a player from 1–2 reps (ICC map). Hoop drill curvature is the worked example: unmeasurable (1 rep) and non-transferring.
3. Where sensors DO add: separating acceleration from top speed for pass rushers — the independent acceleration component predicts EDGE pressure beyond the stopwatch and draft slot. One actionable sensor number.
4. WR YAC-over-expected falls with top speed (xYAC already prices speed) — figure, carefully framed.
Rubric fit: Football — "which drills to trust, which number to pull" is week-to-week usable in draft season; DS — reliability + nested out-of-sample models + honest nulls; Viz — speed-curve small multiples, ICC heatmap, nested-R² bars, EDGE partial plot.

## Direction ranking vs judging rubric (ORIGINAL, superseded above)
1. **"Stopwatch vs sensor: what the 40 tracking adds, by position" — RECOMMENDED.** Foundation = reliability audit (which sensor features are even measurable); stage 1 = Combine → in-game speed/accel (n≈450, reliable instrument, sensor beats stopwatch, position-specific); stage 2 = production where it exists (IDL pressure via first-step burst; WR YAC-oe paradox). Hoop-drill null as the cautionary example. Fits host example #3 (drill translation). Viz: speed-curve small multiples by position, ICC heatmap, Combine-vs-game scatter, translation funnel. Risk: crowded idea; differentiate with reliability + in-game movement outcomes nobody else will compute.
2. Measurement audit alone — top DS score, weaker Football score; better as the foundation of #1.
3. IDL first-step burst → pressure — strong effects, n=24; a section of #1, not a standalone.
4. Hoop drill-translation (negative) — one paragraph + one figure in #1.
5. WR YAC-oe paradox — one figure in #1; model-artifact risk.
6. Route break → separation-over-expected — null (all partials ≈ 0). Drop.
7. DB transition drill — reliable instrument, no production outcome in data. Appendix at most.
8. OL drills → pass protection — noise. Drop.

## Linkage v0 results (2026-10-07) — bend does not transfer
Code: `src/bdb27/linkage.py` (binomial GLM, controls = weight, arm length, draft overall pick; partial Spearman; bootstrap CI; LOO deviance), `src/bdb27/ingame.py` (in-game curvature-at-speed on pass-rush snaps from game tracking, snap → release window).
- Controls changed from (10-yd split, weight, arm) to (weight, arm, draft pick) because 14/63 rushers skipped the 40. Draft pick = "what scouts already concluded"; the question becomes "does the drill add to the draft slot?"
- **EDGE (n=39):** bend_index partial ρ = +0.01 vs pressure rate, LOO deviance +8.2 (worse). bend_s_mean, bend_dur, move_time, asym_s all ≈ 0. What *does* add: ten_yd_split (partial ρ −0.44, LOO −12.2), ngs_athleticism_score (+0.36, LOO −2.4). Same picture for quick_pressure and sack rate.
- **IDL (n=24):** move_time partial ρ −0.62 (LOO −12.5), exit_s_peak +0.62 (LOO −15.3), also on sack rate (−8.7 / −9.6). bend_index +0.35 ns (LOO +7.2). Straight-line components carry the signal, not curvature. Fragile n.
- **Combine → in-game movement (EDGE):** bend_index → in-game ac_med ρ +0.10 raw / −0.09 partial. ten_yd_split → in-game ac ρ −0.74 raw / −0.42 partial. In-game s·ω is speed-dominated; the hoop drill's curvature does not show up on Sundays.
- Idea #1 quick check (WR/TE, n=64 with ≥30 REG targets): raw mean separation is confounded — forty partial ρ +0.29 (slower = more separation), route-drill reaccel −0.35, peak lateral accel −0.46. Any separation outcome must be modeled over expectation (route, depth, cushion, man/zone, alignment) first.

## Decisions

### 2026-10-07 · Ashwin (via Claude) · Idea: "Bend → pressure" (Idea #2)
- Metric: bend from Combine `RUN_THE_HOOP_DRILL` tracking — segment arc A / loop B / arc C by alternating yaw-rate sign (|ω| ≥ 0.6 rad/s, s ≥ 1.5 yd/s); per segment speed, median centripetal accel s·ω, fitted radius, duration; plus drill time, exit sprint peak, hoop-1 vs hoop-2 asymmetry. Code: `src/bdb27/bend.py`, tests in `tests/test_bend.py`.
- Outcome: per-player NFL pass-rush production from `player_play` — pressure rate, quick-pressure rate, sack rate, median time_to_pressure, median get-off. Pass-rush snap := `player_get_off` not null. Code: `src/bdb27/outcomes.py`.
- Why: narrower than the host's listed examples (less crowded), "bend" is scouting vocabulary with no public tracking metric, and three ready-made NGS outcome columns exist. Fallback = Idea #1 if the gate fails.
- Baseline to beat: `combine_results.ngs_athleticism_score`, plus stopwatch 3-cone / 10-yd split, weight, arm length.

### 2026-10-07 · Ashwin (via Claude) · Repo conventions
- Python package `bdb27` (not `bdb` — shadows stdlib debugger). Polars for all data work; Parquet cache in `data/parquet/`.
- `data/` is gitignored and must stay that way (Rules §2.4.b data security; CC BY-NC 4.0).
- Repo must be publishable under an OSI license if we win (Rules §2.5) → MIT license, no non-OSI deps.
- Pre/postseason plays allowed as supporting evidence (host, discussion 746425); default analysis uses REG only.

### 2026-10-07 · Competition facts (from Kaggle, see project doc `competition-brief.md`)
- Analytics writeup only; no prediction track. One submission per team. Deadline **Jan 6, 2027 11:59 PM UTC**.
- Writeup ≤2,000 words, <10 figures/tables (writeup only), embedded visuals, attached public Kaggle notebook.
- Scoring: Football 30 / Data Science 30 / Writeup 20 / Viz 20. Open track (we're grad students).

## Gate results (2026-10-07)
- RUN_THE_HOOP_DRILL: 119 attempts, 109 players, all `combine_position == DL`. **1 attempt per player** (10 have 2) → the "≥2 attempts" criterion was wrong; dropped.
- 106 hoop players have ≥1 pass-rush snap; 78 have ≥100 (all seasons incl. PRE); **63 have ≥100 REG-season pass-rush snaps** (DE 23, DT 22, OLB 16, NT 2). 58 have ≥200 (all seasons).
- Pass-rush snap := `player_get_off` not null → 44,002 rows. `time_to_pressure` populated on only 3,804 rows (pressures), `quick_pressure` 3,763.
- **Decision: gate passed, stay on bend.** Sample is small; the writeup must lean on effect sizes + CIs, not p-values.

## Data facts learned
- `games.csv` has `season_type` PRE as well as REG/POST (PRE undocumented). outcomes.py defaults to REG only.
- Nulls are R-style `NA`. Timestamps parse to Datetime[ms] — use `.dt.epoch("us")`, never cast-to-int assumptions.
- Hoop drill geometry (see reports/figures/hoop_paths_sample.png): approach → arc A around hoop 1 (~90°) → full loop B around hoop 2 (238° ± 16°, fitted radius 1.32 ± 0.14 yd) → arc C back around hoop 1 (~100°) → ~6 yd sprint out. Total moving time 7.1 ± 0.4 s. Standardized across 2023–25.
- Game tracking only contains the 510 cohort players (no opponents/ball).

## First-look correlations (Spearman, n=63, ≥100 REG rush snaps; * p<.05)
| feature | pressure_rate | quick_pressure_rate | sack_rate | get_off_median |
|---|---|---|---|---|
| move_time (drill time) | −0.40* | −0.41* | −0.46* | +0.54* |
| bend_dur (time turning) | −0.31* | −0.34* | −0.30* | +0.34* |
| bend_s_mean | +0.26* | +0.18 | +0.20 | −0.20 |
| bend_index (median a_c) | +0.16 | +0.24 | +0.22 | −0.19 |
| forty | −0.45* | −0.50* | −0.38* | +0.67* |
| ten_yd_split | −0.44* | −0.52* | −0.37* | +0.67* |
| combine_weight | −0.33* | −0.45* | −0.34* | +0.65* |
| ngs_athleticism_score | +0.31* | +0.26* | +0.15 | −0.17 |
Read: raw drill time beats the a_c "bend index"; weight/forty confound DT vs EDGE. Next step is the within-EDGE, controlled comparison.
