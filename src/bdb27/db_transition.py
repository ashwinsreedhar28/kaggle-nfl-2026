"""DB transition drill -> in-game change-of-direction.

In-game signature per DB per coverage snap (player_play.coverage_assignment not null, REG):
  frames from ball_snap to pass_arrived (or end). Per play:
    decel_max        most negative acceleration while s > 3 (the "hip flip"/break)
    reaccel_max      max acceleration in the 0.5 s after the speed trough
    trough_ratio     min speed / preceding peak speed (how much speed survives the transition)
    lat_ac_max       max s*|omega| at speed
  Player = median over plays (>= 40 plays).
Combine side: BACK_PEDAL_AND_TRANSITION_45_DEGREE_REACTION features (duration, s_min_after_peak, a_max)
from drill_players.parquet, plus the 40 for comparison.
Tests: partial Spearman (controls weight + draft pick) and nested LOO-R^2 (controls / +forty / +drill).

    python -m bdb27.db_transition  # -> data/derived/db_ingame_cod.csv, db_transition_results.csv
"""
from __future__ import annotations

import numpy as np
import polars as pl
import statsmodels.api as sm
from scipy.stats import spearmanr

from .paths import DERIVED, PQ, TRACKING_YEARS
from .translation import loo_r2, _z

DRILL = "BACK_PEDAL_AND_TRANSITION_45_DEGREE_REACTION"
END_EVENTS = ["pass_arrived", "pass_outcome_caught", "pass_outcome_incomplete", "pass_outcome_interception", "qb_sack", "tackle", "out_of_bounds"]


def ingame_cod() -> pl.DataFrame:
    pp = pl.scan_parquet(PQ / "player_play.parquet")
    games = pl.scan_parquet(PQ / "games.parquet").select("game_id", "season", "season_type")
    players = pl.scan_parquet(PQ / "players.parquet").select("nfl_id", "nfl_position")
    cov = (pp.join(games, on="game_id").join(players, on="nfl_id")
           .filter((pl.col("season_type") == "REG") & pl.col("coverage_assignment").is_not_null() & pl.col("nfl_position").is_in(["CB", "FS", "SS", "DB"]))
           .select("game_id", "play_id", "nfl_id", "season"))
    key = ["game_id", "play_id", "nfl_id"]
    parts = []
    for y in TRACKING_YEARS:
        keys = cov.filter(pl.col("season") == y).select(*key)
        gt = pl.scan_parquet(PQ / f"game_tracking_{y}.parquet").join(keys, on=key, how="semi")
        ev = pl.col("event").fill_null("")
        gt = gt.sort(*key, "time").with_columns(
            (ev == "ball_snap").cast(pl.Int32).cum_sum().over(key).alias("_snap"),
            ev.is_in(END_EVENTS).cast(pl.Int32).cum_sum().over(key).shift(1, fill_value=0).over(key).alias("_end"),
        ).filter((pl.col("_snap") >= 1) & (pl.col("_end") == 0))
        ddir = ((pl.col("dir") - pl.col("dir").shift(1).over(key) + 180.0) % 360.0 - 180.0)
        gt = gt.with_columns((ddir.radians() / 0.1).abs().alias("omega")).with_columns((pl.col("s") * pl.col("omega")).alias("ac"))
        fast = pl.col("s") > 3.0
        # trough after the first speed peak: approximate with min speed after the frame of max speed
        gt = gt.with_columns(pl.col("s").cum_max().over(key).alias("_cummax"))
        agg = gt.group_by(key).agg(
            pl.len().alias("n_frames"),
            pl.col("a").filter(fast).min().alias("decel_max"),
            pl.col("a").max().alias("accel_max"),
            pl.col("ac").filter(fast).max().alias("lat_ac_max"),
            (pl.col("s").filter(pl.col("_cummax") >= 4.0).min() / pl.col("s").max()).alias("trough_ratio"),
            pl.col("s").max().alias("s_max"),
        ).filter(pl.col("n_frames") >= 10)
        parts.append(agg.collect())
        print(f"{y}: {parts[-1].height} coverage plays")
    plays = pl.concat(parts)
    per = plays.group_by("nfl_id").agg(
        pl.len().alias("cov_plays"),
        pl.col("decel_max").median().alias("ig_decel_med"),
        pl.col("accel_max").median().alias("ig_accel_med"),
        pl.col("lat_ac_max").median().alias("ig_lat_ac_med"),
        pl.col("trough_ratio").median().alias("ig_trough_ratio_med"),
        pl.col("s_max").quantile(0.95).alias("ig_s_p95"),
    ).filter(pl.col("cov_plays") >= 40)
    per.write_csv(DERIVED / "db_ingame_cod.csv")
    return per


def main() -> None:
    per = ingame_cod()
    dp = pl.read_parquet(DERIVED / "drill_players.parquet").filter(pl.col("drill_name") == DRILL).select(
        "nfl_id", pl.col("duration").alias("drill_time"), pl.col("s_min_after_peak").alias("drill_trough"), pl.col("a_max").alias("drill_amax"), pl.col("lat_ac_p90").alias("drill_lat_ac"))
    out = pl.read_csv(DERIVED / "outcomes_all.csv").with_columns(pl.col(pl.Float64).fill_nan(None)).select(
        "nfl_id", "display_name", "combine_weight", "draft_overall_pick", "forty", "three_cone", "short_shuttle", "career_defensive_snaps", "career_games_started")
    d = per.join(dp, on="nfl_id").join(out, on="nfl_id")
    print(f"DBs with drill + >=40 coverage plays: {d.height}")
    ctrl = ["combine_weight", "draft_overall_pick"]
    rows = []
    for oc in ["ig_decel_med", "ig_accel_med", "ig_lat_ac_med", "ig_trough_ratio_med", "ig_s_p95", "career_defensive_snaps", "career_games_started"]:
        for f in ["drill_time", "drill_trough", "drill_amax", "drill_lat_ac", "forty", "three_cone", "short_shuttle"]:
            s = d.select(f, oc, *ctrl).drop_nulls()
            if s.height < 20:
                continue
            X = sm.add_constant(s.select(*ctrl).to_numpy().astype(float))
            rx = sm.OLS(s[f].to_numpy().astype(float), X).fit().resid; ry = sm.OLS(s[oc].to_numpy().astype(float), X).fit().resid
            rho, p = spearmanr(rx, ry)
            rows.append({"outcome": oc, "feature": f, "n": s.height, "raw": round(spearmanr(s[f], s[oc])[0], 3), "partial": round(rho, 3), "p": round(p, 3)})
    res = pl.DataFrame(rows)
    # nested LOO R2 for the in-game COD outcomes
    nested = []
    for oc in ["ig_decel_med", "ig_accel_med", "ig_lat_ac_med", "ig_trough_ratio_med"]:
        s = d.select(oc, *ctrl, "forty", "drill_time", "drill_trough", "drill_amax").drop_nulls()
        y = s[oc].to_numpy().astype(float)
        X = lambda cols: np.column_stack([np.ones(s.height), _z(s.select(cols).to_numpy().astype(float))])
        nested.append({"outcome": oc, "n": s.height, "r2_controls": round(loo_r2(X(ctrl), y), 3), "r2_forty": round(loo_r2(X(ctrl + ["forty"]), y), 3),
                       "r2_drill": round(loo_r2(X(ctrl + ["drill_time", "drill_trough", "drill_amax"]), y), 3),
                       "r2_both": round(loo_r2(X(ctrl + ["forty", "drill_time", "drill_trough", "drill_amax"]), y), 3)})
    nested = pl.DataFrame(nested)
    res.write_csv(DERIVED / "db_transition_results.csv"); nested.write_csv(DERIVED / "db_transition_nested.csv")
    with pl.Config(tbl_rows=60, tbl_width_chars=160):
        print(res.filter(pl.col("p") < 0.1).sort("p")); print(nested)


if __name__ == "__main__":
    main()
