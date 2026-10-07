"""In-game bend for the DL cohort: curvature-at-speed on pass-rush snaps.

For each pass-rush snap (player_get_off not null) we take frames from ball_snap
to the pass-release/sack event and compute the rusher's yaw rate and centripetal
acceleration s*|omega|. Per player we summarize the per-play maxima.

    python -m bdb27.ingame   # -> data/derived/ingame_bend_players.csv
"""
from __future__ import annotations

import polars as pl

from .paths import DERIVED, PQ, TRACKING_YEARS

END_EVENTS = ["pass_forward", "qb_sack", "qb_strip_sack", "pass_shovel", "handoff", "run", "qb_slide", "lateral"]


def rush_frames(year: int, rush_keys: pl.LazyFrame) -> pl.LazyFrame:
    gt = pl.scan_parquet(PQ / f"game_tracking_{year}.parquet")
    gt = gt.join(rush_keys, on=["game_id", "play_id", "nfl_id"], how="semi")
    key = ["game_id", "play_id", "nfl_id"]
    ev = pl.col("event").fill_null("")
    gt = gt.sort(*key, "time").with_columns(
        (ev == "ball_snap").cast(pl.Int32).cum_sum().over(key).alias("_after_snap"),
        # counts END events strictly before this frame, so the end frame itself is kept
        ev.is_in(END_EVENTS).cast(pl.Int32).cum_sum().over(key).shift(1, fill_value=0).over(key).alias("_ends_before"),
    )
    gt = gt.filter((pl.col("_after_snap") >= 1) & (pl.col("_ends_before") == 0))
    ddir = ((pl.col("dir") - pl.col("dir").shift(1).over(key) + 180.0) % 360.0 - 180.0)
    return gt.with_columns(
        (ddir.radians() / 0.1).abs().alias("omega"),
    ).with_columns((pl.col("s") * pl.col("omega")).alias("ac"))


def per_play(frames: pl.LazyFrame) -> pl.LazyFrame:
    key = ["game_id", "play_id", "nfl_id"]
    return frames.group_by(key).agg(
        pl.len().alias("n_frames"),
        pl.col("s").max().alias("s_max"),
        pl.col("ac").filter(pl.col("s") > 3.0).max().alias("ac_max_at_speed"),
        pl.col("ac").filter(pl.col("s") > 3.0).quantile(0.9).alias("ac_p90_at_speed"),
        pl.col("omega").filter(pl.col("s") > 3.0).max().alias("omega_max_at_speed"),
        pl.col("dis").sum().alias("path_yds"),
    ).filter(pl.col("n_frames") >= 10)


def main() -> None:
    pp = pl.scan_parquet(PQ / "player_play.parquet")
    games = pl.scan_parquet(PQ / "games.parquet").select("game_id", "season", "season_type")
    rush = (
        pp.join(games, on="game_id")
        .filter((pl.col("season_type") == "REG") & pl.col("player_get_off").is_not_null())
        .select("game_id", "play_id", "nfl_id", "season", pl.col("time_to_pressure").is_not_null().alias("pressure"))
    )
    plays = []
    for y in TRACKING_YEARS:
        keys = rush.filter(pl.col("season") == y).select("game_id", "play_id", "nfl_id")
        plays.append(per_play(rush_frames(y, keys)).collect())
        print(f"{y}: {plays[-1].height} rush plays with frames")
    plays = pl.concat(plays).join(rush.collect(), on=["game_id", "play_id", "nfl_id"])
    plays.write_parquet(DERIVED / "ingame_rush_plays.parquet")
    players = plays.group_by("nfl_id").agg(
        pl.len().alias("plays"),
        pl.col("s_max").median().alias("ig_s_max_med"),
        pl.col("ac_max_at_speed").median().alias("ig_ac_med"),
        pl.col("ac_max_at_speed").quantile(0.9).alias("ig_ac_p90"),
        pl.col("omega_max_at_speed").median().alias("ig_omega_med"),
        pl.col("path_yds").median().alias("ig_path_med"),
        pl.col("pressure").mean().alias("pressure_rate_chk"),
    )
    players.write_csv(DERIVED / "ingame_bend_players.csv")
    print(players.describe())


if __name__ == "__main__":
    main()
