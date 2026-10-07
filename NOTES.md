# NOTES.md — decision log

Source of truth for decisions. Newest at top. Format: date · who · decision · why.

## Open items
- [ ] **DIRECTION DECISION (Ashwin + Joon):** hoop-drill bend failed the signal tests (see "Linkage v0 results"). Options on the table:
  1. Drill-translation writeup on Run-the-Hoop: "scouted as a bend test, the tracking says its predictive content is straight-line burst/time, and mainly for interior DL." Cheap (code exists), honest, narrow; risk = small n (IDL 24) and a semi-negative headline.
  2. Pivot to Idea #1 (route-drill break → separation). Needs a separation-over-expected model first (raw separation is confounded: every athletic trait correlates *negatively* with it). ~15–20 h outcome build; crowded idea space.
  3. Pivot to a 40-yd-dash / acceleration-profile idea: the one trait that clearly transfers in our data is speed (10-yd split → in-game curvature-at-speed ρ = −0.74 within EDGE). Sensor-derived acceleration curve vs stopwatch splits, across all 5 position groups (n≈400), with in-game top speed / acceleration as the movement outcome and position-specific production as the football outcome. Host's "drill translation" example; bigger n; reuses the kinematics + ingame pipeline.
- [ ] Joonyeoup accepts the Kaggle team invite; then add him to the GitHub repo (not before — Rules §3.5.d, §3.6.a).
- [x] Kaggle team formed (Ashwin joined, invite sent). Data downloaded, converted.
- [x] Gate passed (see below). Linkage v0 run.

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
