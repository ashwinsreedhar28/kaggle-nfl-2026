"""Per-player NFL outcomes for every position group (REG season only).

Blocks:
  pass rush (DL/EDGE)      rush_snaps, pressure_rate, quick_pressure_rate, sack_rate, get_off_median
  pass pro (OL/TE)         pp_snaps, pressure_allowed_rate, peak_ppa_mean, sack_allowed_rate
  receiving (WR/TE)        targets, sep_mean, sep_oe (separation over expected*), yac_oe, epa_per_target
  in-game movement (all)   ig_plays, ig_s_p95 (top speed), ig_amax_med, ig_lat_ac_p90
  career                   snaps, games started, draft pick
*sep_oe: residual of separation_at_pass_forward on route, pass_length, cushion, man/zone,
 receiver_alignment, lined_up_position, down/distance (OLS with categorical dummies).

    python -m bdb27.outcomes_all   # -> data/derived/outcomes_all.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import polars as pl
import statsmodels.formula.api as smf

from .paths import DERIVED, PQ, TRACKING_YEARS


def _reg_plays() -> pl.LazyFrame:
    pp = pl.scan_parquet(PQ / "player_play.parquet")
    g = pl.scan_parquet(PQ / "games.parquet").select("game_id", "season", "season_type")
    return pp.join(g, on="game_id").filter((pl.col("season_type") == "REG") & (pl.col("play_nullified_by_penalty") != "Y"))


def pass_rush(pp: pl.LazyFrame) -> pl.DataFrame:
    return (pp.filter(pl.col("player_get_off").is_not_null()).group_by("nfl_id").agg(
        pl.len().alias("rush_snaps"),
        pl.col("time_to_pressure").is_not_null().mean().alias("pressure_rate"),
        pl.col("quick_pressure").fill_null(0).mean().alias("quick_pressure_rate"),
        pl.col("sack").fill_null(0).mean().alias("sack_rate"),
        pl.col("player_get_off").median().alias("get_off_median"),
    ).collect())


def pass_pro(pp: pl.LazyFrame) -> pl.DataFrame:
    return (pp.filter(pl.col("pass_rushers_encountered").is_not_null()).group_by("nfl_id").agg(
        pl.len().alias("pp_snaps"),
        pl.col("pressure_allowed").cast(pl.Int8).mean().alias("pressure_allowed_rate"),
        pl.col("peak_pressure_probability_allowed").mean().alias("peak_ppa_mean"),
        pl.col("sack_allowed").fill_null(0).mean().alias("sack_allowed_rate"),
        pl.col("time_to_pressure_allowed").median().alias("ttpa_median"),
    ).collect())


def receiving(pp: pl.LazyFrame) -> pl.DataFrame:
    tg = pp.filter((pl.col("target") == True) & pl.col("separation_at_pass_forward").is_not_null()).select(
        "nfl_id", "separation_at_pass_forward", "route_ran", "pass_length", "cushion", "team_coverage_man_zone",
        "receiver_alignment", "lined_up_position", "down", "yards_to_go", "yards_after_catch", "expected_yards_after_catch",
        "expected_points_added", "pass_result", "in_motion_at_ball_snap",
    ).collect()
    df = tg.to_pandas()
    df["route_ran"] = df["route_ran"].fillna("UNK"); df["team_coverage_man_zone"] = df["team_coverage_man_zone"].fillna("UNK")
    df["receiver_alignment"] = df["receiver_alignment"].fillna("UNK"); df["lined_up_position"] = df["lined_up_position"].fillna("UNK")
    df["pass_length"] = df["pass_length"].fillna(df["pass_length"].median()); df["cushion"] = df["cushion"].fillna(df["cushion"].median())
    m = smf.ols("separation_at_pass_forward ~ C(route_ran) + pass_length + I(pass_length**2) + cushion + C(team_coverage_man_zone) "
                "+ C(receiver_alignment) + C(lined_up_position) + C(down) + yards_to_go + C(in_motion_at_ball_snap)", data=df).fit()
    df["sep_oe"] = m.resid
    print(f"separation model R^2 = {m.rsquared:.3f} on {len(df)} targets")
    df["yac_oe"] = df["yards_after_catch"] - df["expected_yards_after_catch"]
    out = df.groupby("nfl_id").agg(targets=("sep_oe", "size"), sep_mean=("separation_at_pass_forward", "mean"), sep_oe=("sep_oe", "mean"),
                                    yac_oe=("yac_oe", "mean"), epa_per_target=("expected_points_added", "mean"),
                                    catch_rate=("pass_result", lambda x: (x == "C").mean())).reset_index()
    return pl.from_pandas(out)


def ingame_movement() -> pl.DataFrame:
    key = ["game_id", "play_id", "nfl_id"]
    parts = []
    for y in TRACKING_YEARS:
        gt = pl.scan_parquet(PQ / f"game_tracking_{y}.parquet").sort(*key, "time")
        ddir = ((pl.col("dir") - pl.col("dir").shift(1).over(key) + 180.0) % 360.0 - 180.0)
        gt = gt.with_columns((ddir.radians() / 0.1).abs().alias("omega")).with_columns((pl.col("s") * pl.col("omega")).alias("ac"))
        parts.append(gt.group_by(key).agg(
            pl.col("s").max().alias("s_max"), pl.col("a").max().alias("a_max"),
            pl.col("ac").filter(pl.col("s") > 3.0).max().alias("lat_ac_max"), pl.col("dis").sum().alias("path"),
        ).collect())
    plays = pl.concat(parts)
    return plays.group_by("nfl_id").agg(
        pl.len().alias("ig_plays"),
        pl.col("s_max").quantile(0.95).alias("ig_s_p95"), pl.col("s_max").median().alias("ig_s_med"),
        pl.col("a_max").median().alias("ig_amax_med"), pl.col("lat_ac_max").quantile(0.9).alias("ig_lat_ac_p90"),
    )


def main() -> None:
    pp = _reg_plays()
    base = pl.read_parquet(PQ / "players.parquet").join(pl.read_parquet(PQ / "combine_results.parquet").drop("draft_year"), on="nfl_id") \
        .join(pl.read_parquet(PQ / "player_career_successes.parquet"), on="nfl_id")
    out = base
    for blk in (pass_rush(pp), pass_pro(pp), receiving(pp), ingame_movement()):
        out = out.join(blk, on="nfl_id", how="left")
    out = out.with_columns(pl.col("draft_overall_pick").fill_null(260))
    out.write_csv(DERIVED / "outcomes_all.csv")
    print(out.select("nfl_id", "rush_snaps", "pp_snaps", "targets", "ig_plays").describe())


if __name__ == "__main__":
    main()
