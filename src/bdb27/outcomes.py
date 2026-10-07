"""Per-player NFL pass-rush outcomes from player_play.csv.

Pass-rush snap := player_get_off is not null (NGS populates get-off only for
rushers). Outcomes per player, regular season by default (REG), optionally
including POST (host allows it as supporting evidence).

    python -m bdb27.outcomes
"""
from __future__ import annotations

import polars as pl

from .paths import DERIVED, PQ

MIN_RUSH_SNAPS = 100


def pass_rush_outcomes(season_types: tuple[str, ...] = ("REG",)) -> pl.DataFrame:
    pp = pl.scan_parquet(PQ / "player_play.parquet")
    games = pl.scan_parquet(PQ / "games.parquet").select("game_id", "season", "season_type", "week")
    rush = (
        pp.join(games, on="game_id", how="left")
        .filter(pl.col("season_type").is_in(list(season_types)))
        .filter(pl.col("player_get_off").is_not_null())
        .filter(pl.col("play_nullified_by_penalty") != "Y")
    )
    per_player = rush.group_by("nfl_id").agg(
        pl.len().alias("rush_snaps"),
        pl.col("season").n_unique().alias("seasons"),
        pl.col("time_to_pressure").is_not_null().mean().alias("pressure_rate"),
        pl.col("quick_pressure").fill_null(0).mean().alias("quick_pressure_rate"),
        pl.col("unblocked_pressure").fill_null(0).mean().alias("unblocked_pressure_rate"),
        pl.col("sack").fill_null(0).mean().alias("sack_rate"),
        pl.col("time_to_pressure").median().alias("ttp_median"),
        pl.col("time_to_qb_hurry").median().alias("tth_median"),
        pl.col("player_get_off").median().alias("get_off_median"),
        pl.col("blitzing").cast(pl.Int8).mean().alias("blitz_share"),
        pl.col("lined_up_position").mode().first().alias("lined_up_mode"),
    )
    # per-season rows too, so we can model within-class and check year effects
    per_season = rush.group_by("nfl_id", "season").agg(
        pl.len().alias("rush_snaps"),
        pl.col("time_to_pressure").is_not_null().mean().alias("pressure_rate"),
        pl.col("quick_pressure").fill_null(0).mean().alias("quick_pressure_rate"),
        pl.col("sack").fill_null(0).mean().alias("sack_rate"),
        pl.col("time_to_pressure").median().alias("ttp_median"),
        pl.col("player_get_off").median().alias("get_off_median"),
    )
    return per_player.collect(), per_season.collect()


def main() -> None:
    career, seasons = pass_rush_outcomes()
    career.write_csv(DERIVED / "rush_outcomes_career.csv")
    seasons.write_csv(DERIVED / "rush_outcomes_season.csv")
    elig = career.filter(pl.col("rush_snaps") >= MIN_RUSH_SNAPS)
    print(f"rushers: {career.height}; with >= {MIN_RUSH_SNAPS} REG rush snaps: {elig.height}")
    print(elig.select("rush_snaps", "pressure_rate", "quick_pressure_rate", "sack_rate", "ttp_median", "get_off_median").describe())


if __name__ == "__main__":
    main()
