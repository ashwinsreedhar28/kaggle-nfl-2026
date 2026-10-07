"""CSV -> Parquet conversion. Run once after scripts/download_data.sh.

    python -m bdb27.prep

Game tracking files (up to 975 MiB) are streamed with Polars' lazy scanner so
this works on a laptop with ~8 GB RAM.
"""
from __future__ import annotations

import sys
import time

import polars as pl

from .paths import PQ, RAW, SMALL_FILES, TRACKING_YEARS


def _convert(name: str) -> None:
    src = RAW / f"{name}.csv"
    dst = PQ / f"{name}.parquet"
    if not src.exists():
        print(f"  skip {name}: {src} missing")
        return
    t0 = time.time()
    lf = pl.scan_csv(src, infer_schema_length=10_000, try_parse_dates=False)
    # tracking timestamps: ISO 8601 with milliseconds -> Datetime
    if "time" in lf.collect_schema().names():
        lf = lf.with_columns(
            pl.col("time").str.to_datetime("%Y-%m-%dT%H:%M:%S%.3f", strict=False)
        )
    lf.sink_parquet(dst, compression="zstd")
    print(f"  {name}: {time.time() - t0:.1f}s -> {dst.stat().st_size / 2**20:.0f} MiB")


def main(names: list[str] | None = None) -> None:
    names = names or [*SMALL_FILES, "combine_tracking", *[f"game_tracking_{y}" for y in TRACKING_YEARS]]
    print("Converting CSV -> Parquet")
    for n in names:
        _convert(n)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
