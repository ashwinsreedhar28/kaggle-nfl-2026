"""Week-1 inventory. Answers the go/no-go gate for the bend idea:
how many DL/EDGE have >=2 hoop attempts AND >=100 pass-rush snaps?

    python -m bdb27.eda
"""
from __future__ import annotations

import polars as pl

from .paths import DERIVED, PQ


def load(name: str) -> pl.LazyFrame:
    return pl.scan_parquet(PQ / f"{name}.parquet")


def drill_inventory() -> pl.DataFrame:
    ct = load("combine_tracking").filter(pl.col("entity_type") == "PLAYER")
    cr = load("combine_results").select("nfl_id", "combine_position")
    inv = (
        ct.group_by("draft_year", "drill_type", "drill_name", "nfl_id", "attempt")
        .agg(pl.len().alias("frames"))
        .join(cr, on="nfl_id", how="left")
        .group_by("drill_type", "drill_name", "combine_position")
        .agg(
            pl.col("nfl_id").n_unique().alias("players"),
            pl.len().alias("attempts"),
            pl.col("frames").median().alias("median_frames"),
        )
        .sort("drill_type", "drill_name", "combine_position")
        .collect()
    )
    return inv


def pass_rush_snaps() -> pl.DataFrame:
    """Pass-rush snap = player_get_off is populated (NGS only computes it for rushers)."""
    pp = load("player_play")
    return (
        pp.filter(pl.col("player_get_off").is_not_null())
        .group_by("nfl_id")
        .agg(
            pl.len().alias("rush_snaps"),
            pl.col("time_to_pressure").is_not_null().sum().alias("pressures"),
            pl.col("sack").sum().alias("sacks"),
        )
        .collect()
    )


def gate(min_attempts: int = 2, min_snaps: int = 100) -> pl.DataFrame:
    ct = load("combine_tracking").filter(
        (pl.col("entity_type") == "PLAYER") & (pl.col("drill_name").str.contains("HOOP"))
    )
    hoop = ct.group_by("nfl_id").agg(pl.col("attempt").n_unique().alias("hoop_attempts")).collect()
    rs = pass_rush_snaps()
    pos = load("combine_results").select("nfl_id", "combine_position").collect()
    g = hoop.join(rs, on="nfl_id", how="inner").join(pos, on="nfl_id", how="left")
    ok = g.filter((pl.col("hoop_attempts") >= min_attempts) & (pl.col("rush_snaps") >= min_snaps))
    print(f"hoop drill players: {hoop.height}; with rush snaps: {g.height}; "
          f"pass gate (>={min_attempts} attempts, >={min_snaps} snaps): {ok.height}")
    print(ok.group_by("combine_position").agg(pl.len()).sort("combine_position"))
    return g


def main() -> None:
    inv = drill_inventory()
    inv.write_csv(DERIVED / "drill_inventory.csv")
    with pl.Config(tbl_rows=200, tbl_cols=10):
        print(inv)
    g = gate()
    g.write_csv(DERIVED / "bend_gate.csv")


if __name__ == "__main__":
    main()
