"""Writeup figures. Static PNGs into reports/figures/.

    python -m bdb27.figures
"""
from __future__ import annotations

import numpy as np
import polars as pl
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statsmodels.api as sm

from .paths import DERIVED, FIGS, PQ
from .screen import GROUPS

# validated reference palette (dataviz skill)
C = {"blue": "#2a78d6", "orange": "#eb6834", "aqua": "#1baf7a", "yellow": "#eda100", "magenta": "#e87ba4", "violet": "#4a3aa7"}
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
GROUP_COLOR = {"WR": C["blue"], "TE": C["orange"], "EDGE": C["aqua"], "IDL": C["yellow"], "OL": C["magenta"], "DB": C["violet"]}

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 10, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": SURF, "axes.facecolor": SURF,
    "axes.titlecolor": INK, "axes.titleweight": "bold", "axes.titlesize": 11, "legend.frameon": False,
})


def group_of(pos: str) -> str | None:
    for g, ps in GROUPS.items():
        if pos in ps:
            return g
    return None


def fig1_forty_curves():
    """Speed vs distance in the 40, by position group, plus vmax vs stopwatch."""
    ct = pl.scan_parquet(PQ / "combine_tracking.parquet").filter(
        (pl.col("entity_type") == "PLAYER") & (pl.col("drill_name") == "FORTY_YARD_DASH")).sort("event_id", "time").collect()
    pos = pl.read_parquet(PQ / "players.parquet").select("nfl_id", "nfl_position")
    ct = ct.join(pos, on="nfl_id")
    grid = np.arange(0, 40.5, 0.5)
    curves = {}
    for (ev,), g in ct.group_by(["event_id"]):
        grp = group_of(g["nfl_position"][0])
        if grp is None:
            continue
        s = g["s"].to_numpy(); x, y = g["x"].to_numpy(), g["y"].to_numpy()
        on = int(np.argmax(s >= 1.0)); d = np.hypot(x - x[on], y - y[on]); d[:on] = 0
        if d.max() < 38:
            continue
        curves.setdefault(grp, []).append(np.interp(grid, d[on:], s[on:]))
    fp = pl.read_csv(DERIVED / "forty_players.csv").drop_nulls(["forty", "vmax"])

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1.25, 1]})
    ends = {}
    for grp in ["WR", "DB", "TE", "EDGE", "IDL", "OL"]:
        arr = np.array(curves.get(grp, []))
        if not len(arr):
            continue
        med = np.median(arr, 0)
        a1.plot(grid, med, color=GROUP_COLOR[grp], lw=2, label=f"{grp} (n={len(arr)})")
        ends[grp] = (med[-1], len(arr))
    # direct labels, pushed apart vertically by >= 0.45 yd/s
    order = sorted(ends, key=lambda g: ends[g][0]); ys = [ends[g][0] for g in order]
    for i in range(1, len(ys)):
        ys[i] = max(ys[i], ys[i - 1] + 0.45)
    for g, yy in zip(order, ys):
        a1.text(40.8, yy, f"{g} (n={ends[g][1]})", color=GROUP_COLOR[g], va="center", fontsize=8.5, fontweight="bold")
    a1.set_xlabel("distance from onset (yd)"); a1.set_ylabel("speed (yd/s)"); a1.set_xlim(0, 47); a1.set_ylim(0, 11.5)
    a1.set_title("A  Median 40-yd speed curve by position group")
    a1.axvline(10, color=GRID, lw=1); a1.text(10.3, 0.4, "10-yd split", color=MUTED, fontsize=8)
    a2.scatter(fp["vmax"], fp["forty"], s=14, color=C["blue"], alpha=0.55, edgecolor=SURF, lw=0.5)
    r = np.corrcoef(fp["vmax"], fp["forty"])[0, 1]
    b = np.polyfit(fp["vmax"], fp["forty"], 1); xs = np.linspace(fp["vmax"].min(), fp["vmax"].max(), 50)
    a2.plot(xs, np.polyval(b, xs), color=INK2, lw=1.2)
    a2.set_xlabel("sensor top speed vmax (yd/s)"); a2.set_ylabel("official 40-yd time (s)")
    a2.set_title("B  The stopwatch 40 is a top-speed test")
    a2.text(0.03, 0.06, f"r = {r:+.3f}   n = {fp.height} players", transform=a2.transAxes, color=INK2, fontsize=9)
    fig.tight_layout(); fig.savefig(FIGS / "fig1_forty_curves.png", dpi=160); plt.close(fig)


def fig2_reliability():
    """ICC heatmap: drills (rows) x features (cols)."""
    rel = pl.read_csv(DERIVED / "drill_reliability.csv").filter(pl.col("icc").is_not_nan() & (pl.col("players") >= 20))
    feats = ["duration", "s_peak", "t_10yd", "t_20yd", "a_max", "a_mean_1s", "s_min_after_peak", "lat_ac_p90"]
    labels = ["drill time", "top speed", "time to 10 yd", "time to 20 yd", "max accel", "accel, first 1 s", "speed trough", "lateral accel p90"]
    drills = (rel.filter(pl.col("feature").is_in(feats)).group_by("drill_name").agg(pl.col("icc").max().alias("m"), pl.col("players").first())
              .sort("m", descending=True))
    M = np.full((drills.height, len(feats)), np.nan)
    for i, dn in enumerate(drills["drill_name"]):
        for j, f in enumerate(feats):
            v = rel.filter((pl.col("drill_name") == dn) & (pl.col("feature") == f))["icc"]
            if len(v):
                M[i, j] = max(v[0], 0)
    fig, ax = plt.subplots(figsize=(10, 0.42 * drills.height + 1.6))
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("seq", SEQ)
    im = ax.imshow(M, cmap=cmap, vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(feats))); ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_yticks(range(drills.height))
    ax.set_yticklabels([f"{d.replace('_', ' ').title()[:34]}  (n={n})" for d, n in zip(drills["drill_name"], drills["players"])], fontsize=8.5)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            if not np.isnan(M[i, j]):
                ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=7.5, color="white" if M[i, j] > 0.55 else INK)
    ax.grid(False); ax.set_title("Test-retest reliability (ICC) of sensor features, drills with ≥2 attempts per player", loc="left")
    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02); cb.set_label("ICC (0 = noise, 1 = perfectly repeatable)")
    fig.tight_layout(); fig.savefig(FIGS / "fig2_reliability.png", dpi=160); plt.close(fig)


def fig3_nested_r2():
    s1 = pl.read_csv(DERIVED / "translation_stage1.csv").filter(pl.col("outcome") == "ig_s_p95").filter(pl.col("group") != "ALL")
    s1 = s1.filter(pl.col("group").is_in(["WR", "TE", "EDGE", "IDL", "OL", "DB"]))
    order = ["WR", "TE", "EDGE", "IDL", "OL", "DB"]
    s1 = s1.with_columns(pl.col("group").cast(pl.Enum(order))).sort("group")
    fig, ax = plt.subplots(figsize=(9, 4.2))
    xs = np.arange(s1.height); w = 0.26
    for k, (col, lab, color) in enumerate([("r2_controls", "weight + draft slot", MUTED), ("r2_stopwatch", "+ stopwatch 40 / 10-yd", C["orange"]), ("r2_sensor", "+ sensor top speed & acceleration", C["blue"])]):
        vals = np.clip(s1[col].to_numpy(), 0, None)
        ax.bar(xs + (k - 1) * w, vals, w * 0.92, color=color, label=lab)
        for x, v in zip(xs, vals):
            ax.text(x + (k - 1) * w, v + 0.01, f"{v:.2f}", ha="center", fontsize=7.5, color=INK2)
    ax.set_xticks(xs); ax.set_xticklabels([f"{g}\n(n={n})" for g, n in zip(s1["group"], s1["n"])])
    ax.set_ylabel("leave-one-out R²  (in-game top speed, p95 of plays)"); ax.set_ylim(0, 0.5)
    ax.set_title("Predicting a player's in-game top speed within his position group", loc="left")
    ax.legend(loc="upper right", fontsize=9); ax.grid(axis="x", visible=False)
    fig.tight_layout(); fig.savefig(FIGS / "fig3_nested_r2.png", dpi=160); plt.close(fig)


def fig4_production_forest():
    """Standardized effect (per SD) of Combine speed on production, by group, with 95% CI."""
    s2 = pl.read_csv(DERIVED / "translation_stage2.csv")
    s2 = s2.filter(pl.col("feature").is_in(["forty", "vmax", "accel_resid"]))
    labels = {"forty": "stopwatch 40 time", "vmax": "sensor top speed", "accel_resid": "sensor acceleration | top speed"}
    colors = {"forty": C["orange"], "vmax": C["blue"], "accel_resid": C["aqua"]}
    cells = [("EDGE", "pressure_rate", "EDGE pressure rate"), ("EDGE", "quick_pressure_rate", "EDGE quick-pressure rate"),
             ("EDGE", "sack_rate", "EDGE sack rate"), ("IDL", "pressure_rate", "IDL pressure rate"),
             ("OL", "pressure_allowed_rate", "OL pressure allowed"), ("WR", "sep_oe", "WR separation over expected"),
             ("WR", "yac_oe", "WR YAC over expected"), ("WR", "epa_per_target", "WR EPA per target"), ("TE", "yac_oe", "TE YAC over expected")]
    fig, ax = plt.subplots(figsize=(10, 0.62 * len(cells) + 1.4))
    yt, yl = [], []
    for i, (g, oc, lab) in enumerate(cells):
        y0 = len(cells) - 1 - i
        for k, feat in enumerate(["forty", "vmax", "accel_resid"]):
            r = s2.filter((pl.col("group") == g) & (pl.col("outcome") == oc) & (pl.col("feature") == feat))
            if not r.height:
                continue
            yy = y0 + (1 - k) * 0.22
            b, lo, hi = r["beta_sd"][0], r["ci_lo"][0], r["ci_hi"][0]
            if feat == "forty":  # flip sign so "faster" points the same way as the sensor features
                b, lo, hi = -b, -hi, -lo
            ax.plot([lo, hi], [yy, yy], color=colors[feat], lw=2, solid_capstyle="round")
            ax.plot(b, yy, "o", color=colors[feat], ms=6, mec=SURF, mew=0.8)
        n = s2.filter((pl.col("group") == g) & (pl.col("outcome") == oc))["n"]
        yt.append(y0); yl.append(f"{lab}  (n={n[0] if len(n) else '—'})")
    ax.axvline(0, color="#c3c2b7", lw=1); ax.set_yticks(yt); ax.set_yticklabels(yl, fontsize=9)
    ax.set_xlabel("effect of being faster: SD of outcome per SD of feature, adjusted for weight & draft slot (95% CI)")
    ax.grid(axis="y", visible=False)
    for feat in ["forty", "vmax", "accel_resid"]:
        ax.plot([], [], "o-", color=colors[feat], label=labels[feat])
    ax.legend(loc="lower right", fontsize=8.5, ncol=1)
    ax.set_title("Combine speed vs. production, after weight and draft slot: two signals, seven nulls", loc="left")
    fig.tight_layout(); fig.savefig(FIGS / "fig4_production_forest.png", dpi=160); plt.close(fig)


def fig5_hoop_null():
    a = pl.read_csv(DERIVED / "analysis_table.csv").with_columns(pl.col(pl.Float64).fill_nan(None))
    ig = pl.read_csv(DERIVED / "ingame_bend_players.csv")
    e = a.join(ig, on="nfl_id").filter(pl.col("group") == "EDGE").select("bend_index", "ig_ac_med", "pressure_rate", "rush_snaps").drop_nulls()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for ax, oc, lab in zip(axes, ["ig_ac_med", "pressure_rate"], ["in-game curvature at speed (median per-play max s·ω, yd/s²)", "pressure rate"]):
        y = e[oc].to_numpy() * (100 if oc == "pressure_rate" else 1)
        ax.scatter(e["bend_index"], y, s=np.sqrt(e["rush_snaps"].to_numpy()) * 1.6, color=C["orange"], alpha=0.65, edgecolor=SURF, lw=0.6)
        rho = np.corrcoef(e["bend_index"], y)[0, 1]
        ax.text(0.03, 0.93, f"r = {rho:+.2f}  (n={e.height})", transform=ax.transAxes, color=INK2, fontsize=9)
        ax.set_xlabel("Combine hoop-drill bend index (median centripetal accel, yd/s²)"); ax.set_ylabel(lab)
    fig.suptitle("Run-the-Hoop 'bend' does not show up on Sundays (EDGE, one Combine rep per player)", x=0.02, ha="left", fontsize=11, fontweight="bold", color=INK)
    fig.tight_layout(); fig.savefig(FIGS / "fig5_hoop_null.png", dpi=160); plt.close(fig)


def fig6_yac():
    d = pl.read_csv(DERIVED / "translation_table.csv").with_columns(pl.col(pl.Float64).fill_nan(None))
    w = d.filter((pl.col("group") == "WR") & (pl.col("targets") >= 30)).select("display_name", "yac_oe", "vmax", "targets").drop_nulls()
    fig, ax = plt.subplots(figsize=(7, 4.4))
    ax.scatter(w["vmax"], w["yac_oe"], s=np.sqrt(w["targets"].to_numpy()) * 1.6, color=C["blue"], alpha=0.65, edgecolor=SURF, lw=0.6)
    fit = sm.OLS(w["yac_oe"].to_numpy(), sm.add_constant(w["vmax"].to_numpy())).fit()
    xs = np.linspace(w["vmax"].min(), w["vmax"].max(), 50); pr = fit.get_prediction(sm.add_constant(xs)).summary_frame()
    ax.fill_between(xs, pr["mean_ci_lower"], pr["mean_ci_upper"], color=C["blue"], alpha=0.15, lw=0); ax.plot(xs, pr["mean"], color=C["blue"], lw=2)
    ax.axhline(0, color=GRID, lw=1)
    rho = np.corrcoef(w["vmax"], w["yac_oe"])[0, 1]
    ax.text(0.03, 0.06, f"r = {rho:+.2f}, p = {fit.pvalues[1]:.3f}, n = {w.height} WR with ≥30 targets", transform=ax.transAxes, color=INK2, fontsize=9)
    ax.set_xlabel("Combine top speed vmax (yd/s)"); ax.set_ylabel("YAC over NGS expected (yd per target)")
    ax.set_title("Faster receivers under-run their expected YAC", loc="left")
    fig.tight_layout(); fig.savefig(FIGS / "fig6_yac_paradox.png", dpi=160); plt.close(fig)


def fig7_prospect_card(nfl_id: int | None = None):
    """One prospect, every usable sensor feature as a within-position percentile with its one-rep 90% band."""
    c = pl.read_csv(DERIVED / "prospect_cards_bands.csv")
    if nfl_id is None:  # pick a 2025 DB with the three trusted features
        ok = c.filter((c["group"] == "DB") & (c["draft_year"] == 2025) & c["drill"].str.contains("BACK_PEDAL")).group_by("nfl_id").len().filter(pl.col("len") == 3)
        nfl_id = int(ok["nfl_id"][0])
    p = c.filter(pl.col("nfl_id") == nfl_id).filter(~pl.col("verdict").str.starts_with("REDUNDANT") | (pl.col("feature") == "top speed"))
    tier = {"USE": 0, "REDUNDANT with stopwatch": 0}
    p = p.with_columns(pl.col("verdict").replace_strict(tier, default=1).alias("tier")).sort("tier", "pctile_hi", descending=[False, True])
    name, pos, pick = p["display_name"][0], p["nfl_position"][0], p["draft_overall_pick"][0]
    fig, ax = plt.subplots(figsize=(9, 0.5 * p.height + 1.8))
    for i, r in enumerate(p.to_dicts()):
        y = p.height - 1 - i
        trusted = r["tier"] == 0
        col = C["blue"] if trusted else MUTED
        ax.plot([r["pctile_lo"], r["pctile_hi"]], [y, y], color=col, lw=6, alpha=0.25, solid_capstyle="round")
        ax.plot(r["pctile"], y, "o", color=col, ms=9, mec=SURF, mew=1)
        ax.text(102, y, f'{int(r["pctile"])}  ({int(r["pctile_lo"])}–{int(r["pctile_hi"])})', va="center", fontsize=9, color=INK2, family="monospace")
        lab = f'{r["drill"].replace("_", " ").title().replace("45 Degree Reaction", "")[:30]} · {r["feature"]}'
        ax.text(-3, y, lab + ("" if trusted else f'   [{r["verdict"].lower()}]'), ha="right", va="center", fontsize=9, color=INK if trusted else MUTED)
    ax.set_xlim(0, 100); ax.set_ylim(-0.7, p.height - 0.3); ax.set_yticks([]); ax.grid(axis="y", visible=False)
    ax.axvline(50, color=GRID, lw=1); ax.set_xlabel(f"percentile among {p['group'][0]} prospects, 2023–25 (higher = better); band = 90% one-rep range")
    ax.set_title(f"{name}  ·  {pos}  ·  pick {pick}  ·  Combine sensor card", loc="left", pad=28)
    ax.plot([], [], "o", color=C["blue"], label="trusted from one rep"); ax.plot([], [], "o", color=MUTED, label="needs more reps to trust")
    ax.legend(loc="lower left", fontsize=8.5, ncol=2, bbox_to_anchor=(0, 1.005), frameon=False)
    fig.tight_layout(); fig.savefig(FIGS / "fig7_prospect_card.png", dpi=160, bbox_inches="tight"); plt.close(fig)


def main() -> None:
    for f in (fig1_forty_curves, fig2_reliability, fig3_nested_r2, fig4_production_forest, fig5_hoop_null, fig6_yac, fig7_prospect_card):
        f(); print("ok", f.__name__)


if __name__ == "__main__":
    main()
