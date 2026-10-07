# NOTES.md — decision log

Source of truth for decisions. Newest at top. Format: date · who · decision · why.

## Open items
- [ ] Joonyeoup accepts the Kaggle team invite; then add him to the GitHub repo (not before — Rules §3.5.d, §3.6.a).
- [ ] Linkage model v0: does bend add over forty / 10-yd split / weight / NGS athleticism **within EDGE (DE/OLB)**? Mixed model or ridge with position-group control; bootstrap CIs. n≈63 total, ~39 EDGE — be honest about power.
- [ ] Decide outcome: pressure_rate (n≈63, well-populated) vs ttp_median (only ~3.8k pressure rows total) — pressure_rate is primary, ttp secondary.
- [ ] Reliability: hoop drill is 1 attempt/player, so no within-player ICC. Use PASS_RUSH_DRILL (217 attempts / 114 players, ~2 each) or FOUR_BAG_AGILITY as a second bend/COD measure for convergent validity.
- [x] Kaggle team formed (Ashwin joined, invite sent). Data downloaded, converted.
- [x] Gate passed (see below).

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
