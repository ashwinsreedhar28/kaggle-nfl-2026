# NFL Big Data Bowl 2027 — Bend → Pressure

Team: Ashwin Sreedhar, Joonyeoup Kim. Competition: https://www.kaggle.com/competitions/nfl-big-data-bowl-2027

**Question:** does *bend* — the ability to carry speed through a tight arc, measured from 10 Hz tracking of the Combine
`RUN_THE_HOOP_DRILL` — predict NFL pass-rush production (pressure rate, time-to-pressure, sacks) beyond stopwatch drills
and the NGS athleticism score?

Decisions and status live in [NOTES.md](NOTES.md). Rules/data brief is in the Claude project (`competition-brief.md`).

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
# Kaggle API token at ~/.kaggle/kaggle.json, rules accepted on kaggle.com, then:
make data      # download + unzip (~2.3 GB) into data/raw/
make prep      # CSV -> Parquet (data/parquet/)
make eda       # drill inventory + bend go/no-go gate  -> data/derived/
make bend      # per-attempt and per-player bend metrics
make outcomes  # per-player pass-rush outcomes
make test
```

## Layout
```
src/bdb27/      kinematics.py (shared), bend.py (Combine metric), outcomes.py (NFL outcomes), eda.py, prep.py
scripts/        download_data.sh
notebooks/      exploratory notebooks (keep outputs stripped)
reports/        writeup draft + figures
tests/          synthetic-geometry tests for the bend metric
data/           gitignored — never commit competition data
```

## Rules we must not break
- Private code sharing is only allowed inside the Kaggle Team → merge on Kaggle first.
- Never commit or redistribute the data (CC BY-NC 4.0, Rules §2.4.b).
- Winner license is open source (MIT here); only OSI-licensed dependencies.
- Writeup ≤2,000 words, <10 figures, attached public Kaggle notebook, one submission per team.
