# What Combine Sensors Add — and Don't
### A measurement audit of Combine tracking against three NFL seasons

*Draft v1 — 2026-10-07. Target ≤2,000 words, ≤9 figures. Every number regenerates from the Makefile; see the attached notebook.*

---

## The question a scouting department actually has

Every February, 10 Hz optical tracking records every Combine drill. By April, a club's analytics staff must decide which of those numbers go on the draft board next to the stopwatch times they already trust. Most Big Data Bowl entries will propose a new sensor metric and show that it correlates with something. We asked the prior question: **which Combine sensor measurements are reliable enough to rate a prospect at all, which ones duplicate what the stopwatch already says, and which transfer to how a player moves or produces on Sundays — beyond what his draft slot already told you?**

The answer is a *Combine Sensor Report Card* (Figure 8) plus a prospect card format (Figure 7) that a department could adopt as-is: for each of 56 drill-level sensor features, a trust tier, the number of reps needed to make it trustworthy, and how far a single rep can move a prospect's percentile. Along the way the data answers three questions scouts argue about, and the answers are not the obvious ones.

**Data.** 510 prospects from the 2023–25 classes; 6,310 Combine drill attempts; 316k player-plays with Next Gen Stats production metrics; 8.8M in-game tracking frames. Regular season only unless stated. Draft classes have 1–3 seasons of exposure, so every production analysis adjusts for draft slot and class.

## 1. The 40 is a top-speed test

We fit the standard sprint model, v(t) = v_max(1 − e^(−(t−t₀)/τ)), to all 793 tracked 40-yard dashes (median fit error 0.16 yd/s). The model-implied finish time reproduces the official clock at r = 0.945. More to the point, **sensor top speed alone correlates with the official 40 time at r = −0.965** (Figure 1B): 93% of the variance in the number scouts have used for fifty years is a single quantity, top speed. Position groups differ in the ceiling, not the shape of the curve (Figure 1A). Decomposing the 40 further — acceleration, splits, the fitted time constant — is real physiology but, as Sections 3–4 show, not new scouting information.

## 2. Most position drills cannot be measured from one or two reps

Reliability is the precondition for everything else: a number that changes when the same athlete repeats the drill cannot rank athletes. For every drill with two or more attempts per player we computed the test–retest intraclass correlation of each sensor feature, with bootstrap intervals (Figure 2; 375 players on the 40, 119 on the DB back-pedal-transition drill, 137 on the Gauntlet).

Three features clear ICC 0.8 on their own: 40-yard top speed (0.98) and, from the DB back-pedal-and-transition drill, total time (0.90), speed trough (0.84) and maximum acceleration (0.81). Another fifteen sit between 0.5 and 0.75 and become usable with two to four reps (Spearman–Brown). **Thirty-six of 56 features — the Short Shuttle, Line Drill, Short Zone Breaks, Pass Rush Drop, and nearly every acceleration or lateral-acceleration feature of a route or agility drill — have ICC below 0.5 from a single rep.** They are mostly noise about the athlete.

The Run-the-Hoop drill for defensive linemen is the worked example. It is run once per player, so its reliability is undefined; and its curvature "bend" index — the quantity scouts would hope it measures — correlates at r ≈ 0.1 with both a rusher's in-game curvature at speed and his pressure rate (Figure 5).

## 3. Within a position, the Combine barely predicts game movement — and the sensor adds nothing to the stopwatch

Does a prospect's Combine movement show up in his game movement? We took each player's in-game top speed (95th percentile of per-play maxima across all tracked plays) and compared nested leave-one-out models within each position group: weight + draft slot; plus the stopwatch 40 and 10-yard split; plus sensor top speed and acceleration-beyond-top-speed (Figure 3).

In-game top speed is only moderately predictable even for receivers (R² 0.37), weakly for edge rushers (0.20, mostly size and draft slot), and essentially not at all for tight ends, interior linemen, offensive linemen or defensive backs. In no group does the sensor model beat the stopwatch model — the difference in out-of-sample R² is within ±0.03 everywhere. In-game acceleration and lateral acceleration are unpredictable from any Combine measure. The 40, timed by a stopwatch, already contains whatever the sensor 40 knows about game speed.

The same holds for the one reliable position drill. The DB back-pedal-transition features predict none of four in-game change-of-direction measures on coverage snaps (n = 64; adding them lowers out-of-sample R²). **Reliable is necessary, not sufficient.**

## 4. Production: two signals, seven nulls

We tested nine position × outcome cells, one row per player, robust OLS adjusted for weight and draft slot, reporting standardized effects with confidence intervals (Figure 4). Faster interior defensive linemen generate more pressure (stopwatch 40: +0.97 SD per SD, n = 22). Faster receivers produce *less* yards-after-catch over the NGS expectation (−0.46 SD, n = 44; Figure 6) — expected YAC already prices in speed at the catch, so the residual rewards what the 40 does not measure. Edge pressure, quick-pressure and sack rates, offensive-line pressure allowed, receiver separation-over-expected and EPA per target: intervals span zero.

Two methods notes judges should know. A snaps-as-trials binomial model reports p < 0.01 on the edge cells; it is wrong, because it ignores player-level overdispersion, and we discarded it. And a 4,637-test screen of every drill feature against every outcome, FDR-controlled, returned 23 survivors — fewer than the two production signals above would lead you to hope, and none for edge pressure, pass protection or separation.

We also tested the brief's "hidden talent" hypothesis directly: does any reliable sensor feature identify players who out-play their draft slot in career snaps or starts? Across 56 feature × position cells the best p-value is 0.028 — chance.

## 5. What to do with this: the Report Card and the prospect card

Figure 8 is the deliverable. For each sensor feature worth collecting it gives the reliability of one rep with its interval, the reps needed to reach ICC 0.8, how far one rep can move a prospect's within-position percentile (90% band), the minimum percentile gap between two prospects that is a real difference, redundancy with the stopwatch, and a verdict. Three concrete rules fall out:

**Rule 1 — treat the sensor 40 as the stopwatch 40.** Top speed is the stopwatch (|r| 0.97). Do not pay for, or over-interpret, a second number. One rep pins a prospect's top-speed percentile to ±8 points; two prospects need an 18-point gap before the difference is real.

**Rule 2 — one rep of a position drill is not an evaluation.** The usable position-drill features have one-rep 90% bands of ±29–44 percentile points and minimum detectable differences of 37–52 points: a single rep cannot tell a 30th-percentile athlete from a 70th. The fix is operational, not analytical — run two to four reps, and the Report Card says which drills become usable at which count. The 36 "don't use" features should not appear on a board at all.

**Rule 3 — put the band on the card.** Figure 7 shows a 2025 safety's sensor card: every usable feature as a within-position percentile with the band one rep implies. Blue features can be read at face value; grey ones say "needs more reps." The format prevents the most common failure in Combine evaluation — a scout reacting to a one-rep number that is mostly measurement error.

And one honest caveat for the league office: the DB back-pedal-transition drill is the most repeatable position drill in the Combine and the one we would most like to recommend. It is reliable; we could not show it transfers. Collecting two reps of the agility drills, so transfer can be tested properly, is the single change that would make next year's sensor data more useful than this year's.

## Limitations

Position-group samples are 22–94 players; the 2025 class has one season of outcomes against three for 2023; players who never saw the field have no game data (survivorship); in-game top speed is situational and role-driven, which is why offensive and interior linemen are near-unpredictable; career outcomes are confounded by draft slot, which we adjust for but cannot remove; only the 510 cohort players are tracked in games, so no opponent-relative metrics can be rebuilt from frames.

## Figures
1. Median 40-yd speed curve by position; sensor top speed vs official 40 (r −0.965).
2. Test–retest reliability (ICC) of sensor features by drill.
3. Leave-one-out R² for in-game top speed: controls / +stopwatch / +sensor, by position.
4. Standardized production effects of Combine speed, nine cells, 95% CIs.
5. Run-the-Hoop bend index vs in-game curvature and pressure (EDGE).
6. Receiver YAC over expected vs top speed.
7. Prospect sensor card with one-rep bands.
8. Combine Sensor Report Card.

*Code: github.com/ashwinsreedhar28/kaggle-nfl-2026 (MIT).*
