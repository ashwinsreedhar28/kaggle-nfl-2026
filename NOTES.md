# NOTES.md — decision log

Source of truth for decisions. Newest at top. Format: date · who · decision · why.

## Open items
- [ ] Form the Kaggle team (Ashwin + Joonyeoup) **before** either of us shares code. Private code sharing outside a Kaggle Team is disqualifying (Rules §3.5.d, §3.6.a).
- [ ] Download data (`scripts/download_data.sh`) → `make prep` → `make eda`. Fill in the gate numbers below.
- [ ] Week-1 gate (by Oct 13): ≥60 DL/EDGE with ≥2 hoop attempts AND ≥100 REG pass-rush snaps → stay on bend. Otherwise pivot to Idea #1 (break quality → separation).

## Decisions

### 2026-10-07 · Ashwin (via Claude) · Idea: "Bend → pressure" (Idea #2)
- Metric: bend from Combine `RUN_THE_HOOP_DRILL` tracking — speed retention through the arc, sustained centripetal accel (s·ω), fitted arc radius, exit re-acceleration. Code: `src/bdb27/bend.py`.
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

## Gate results
_(fill after `make eda`)_
- hoop drill players: —
- with pass-rush snaps: —
- passing gate: — (by combine_position: —)
