from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PQ = ROOT / "data" / "parquet"
DERIVED = ROOT / "data" / "derived"
FIGS = ROOT / "reports" / "figures"

for p in (RAW, PQ, DERIVED, FIGS):
    p.mkdir(parents=True, exist_ok=True)

TRACKING_YEARS = (2023, 2024, 2025)
SMALL_FILES = ("players", "combine_results", "player_career_successes", "games", "player_play")
