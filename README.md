# NFL Big Data Bowl 2027 — What Combine sensors add, and don't

Team: Ashwin Sreedhar, Joonyeoup Kim · Open track · Deadline **Jan 6, 2027, 11:59 PM UTC**
Competition: https://www.kaggle.com/competitions/nfl-big-data-bowl-2027

**Question:** which Combine sensor measurements are reliable enough to rate a prospect, and which of them transfer to
NFL movement or production beyond what the stopwatch and the draft board already know?

**Current answer (2026-10-07):** the 40 is a top-speed test (sensor top speed vs official time r = −0.965); most
position-drill sensor features are not repeatable from 1–2 reps; only the DB back-pedal-transition drill is reliable
from a single rep; and within a position the Combine barely predicts in-game movement at all. Deliverable = a
**Combine Sensor Report Card** telling a scouting department which numbers to trust, how many reps make the others
usable, and which to ignore.

## Start here
1. `NOTES.md` — decision log, newest first. Read all of it before touching code.
2. `reports/writeup_outline.md` — writeup structure, figure list, rubric scorecard, open questions.
3. `reports/figures/fig1…fig6.png` — current draft figures.
4. `data/derived/report_card.csv` — the usable artifact (after running the pipeline).

## Setup
```bash
git clone https://github.com/ashwinsreedhar28/kaggle-nfl-2026.git && cd kaggle-nfl-2026
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
Data (2.3 GB) is gitignored: download "Download All" from the competition Data tab and unzip so the CSVs sit in
`data/raw/` (not in a subfolder). Then:
```bash
make prep          # CSV -> Parquet (data/parquet/), ~30 s
make features      # per-attempt kinematics for every drill + test-retest ICC
make outcomes_all  # per-player NFL outcomes, all position groups (incl. in-game movement from 8.8M frames)
make forty         # sprint-model decomposition of the 40 (vmax, acceleration, splits)
make screen        # 4,637-test partial-correlation screen with FDR
make translation   # nested out-of-sample models: controls / +stopwatch / +sensor; production effects
make reportcard    # Combine Sensor Report Card, prospect cards, game-speed index
make figures       # reports/figures/*.png
make test
```
Older modules kept for the record: `bend.py`, `linkage.py`, `ingame.py`, `outcomes.py`, `eda.py` (the hoop-drill
"bend" idea — tested and retired, see NOTES.md).

## Layout
```
src/bdb27/   kinematics.py · prep.py · features.py · outcomes_all.py · forty.py · screen.py · translation.py · reportcard.py · figures.py
reports/     writeup_outline.md, figures/
tests/       synthetic-geometry tests
data/        gitignored — never commit competition data
```

## Rules we must not break
- Private code sharing is only allowed inside the Kaggle Team → both members on the Kaggle team before repo access.
- Never commit or redistribute the data (CC BY-NC 4.0, Rules §2.4.b).
- Winner license is open source (MIT here); only OSI-licensed dependencies.
- Writeup ≤2,000 words, <10 figures, attached public Kaggle notebook, one submission per team.
