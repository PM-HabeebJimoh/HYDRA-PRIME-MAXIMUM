"""
search.py — exhaustive parameter search against the goal.

Goal: win rate > 80%, monthly return in the thousands of percent, low drawdown.

Searches the rule space on real BTC-USD hourly data:
  entry     BB% threshold, HV ratio threshold
  exit      take-profit distance, stop distance, max holding period
  direction band reversion vs band continuation
  sizing    risk per trade, leverage

January 2026 is in-sample; June 2026 is held out for validation.

The BB% and HV series depend only on price, so they are precomputed once per
month and reused across every configuration.

Run:  python scripts/search.py
"""

from __future__ import annotations

import itertools
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from v01t.costs import DEFAULT_COSTS, ZERO_COSTS
from v01t.dataset import load_month

TARGET_WR = 80.0
TARGET_MONTHLY_PCT = 1000.0
TARGET_DD = 5.0
WARMUP = 30


def precompute(closes):
    """BB% and HV ratio at every index, computed once."""
    n = len(closes)
    bb = [50.0] * n
    hv = [1.0] * n
    rets = [0.0] + [closes[i] / closes[i - 1] - 1 for i in range(1, n)]
    for i in range(n):
        if i >= 19:
            w = closes[i - 19: i + 1]
            sma = sum(w) / 20
            var = sum((x - sma) ** 2 for x in w) / 20
            sd = var ** 0.5
            if sd > 0:
                lo, hi = sma - 2 * sd, sma + 2 * sd
                bb[i] = (closes[i] - lo) / (hi - lo) * 100
        if i >= WARMUP:
            s = statistics.stdev(rets[i - 4: i + 1])
            l = statistics.stdev(rets[i - 19: i + 1])
            if l > 0:
                hv[i] = s / l
    return bb, hv


def backtest(closes, bb, hv, bb_low, bb_high, hv_max, tp_pct, stop_pct,
             max_hold, leverage, risk_pct, costs, reversion=True, equity0=10_000.0):
    equity = equity0
    peak = equity
    max_dd = 0.0
    wins = trades = 0
    per_side = (costs.spread_bps + costs.slippage_bps) * 1e-4
    fee_rate = costs.taker_fee_bps * 1e-4
    fund_rate = costs.funding_bps_8h * 1e-4
    n = len(closes)
    i = WARMUP

    while i < n - 1:
        b, h = bb[i], hv[i]
        at_low = b < bb_low
        at_high = b > bb_high
        if not (at_low or at_high) or h >= hv_max:
            i += 1
            continue

        direction = (1 if at_low else -1) if reversion else (-1 if at_low else 1)
        mid = closes[i]
        entry = mid * (1 + per_side) if direction > 0 else mid * (1 - per_side)
        stop_dist = entry * stop_pct
        if stop_dist <= 0:
            i += 1
            continue
        units = min((equity * risk_pct) / stop_dist, (equity * leverage) / entry)
        if units <= 0:
            i += 1
            continue

        stop_p = entry * (1 - stop_pct) if direction > 0 else entry * (1 + stop_pct)
        targ_p = entry * (1 + tp_pct) if direction > 0 else entry * (1 - tp_pct)

        exit_idx = min(i + max_hold, n - 1)
        for j in range(i + 1, min(i + 1 + max_hold, n)):
            p = closes[j]
            if (p <= stop_p if direction > 0 else p >= stop_p):
                exit_idx = j
                break
            if (p >= targ_p if direction > 0 else p <= targ_p):
                exit_idx = j
                break

        xfill = closes[exit_idx] * (1 - per_side) if direction > 0 else closes[exit_idx] * (1 + per_side)
        notional = units * entry
        net = ((xfill - entry) * units * direction
               - notional * fee_rate - units * xfill * fee_rate
               - notional * fund_rate * ((exit_idx - i) / 8.0))

        equity = max(0.0, equity + net)
        trades += 1
        if net > 0:
            wins += 1
        if equity > peak:
            peak = equity
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak * 100)
        if equity <= 0:
            break
        i = exit_idx + 1

    return {
        "trades": trades, "wins": wins, "losses": trades - wins,
        "wr": (wins / trades * 100) if trades else 0.0,
        "final": equity,
        "roi": (equity - equity0) / equity0 * 100,
        "max_dd": max_dd,
    }


def meets_goal(r, min_trades=10):
    return (r["trades"] >= min_trades and r["wr"] > TARGET_WR
            and r["roi"] > TARGET_MONTHLY_PCT and r["max_dd"] < TARGET_DD)


def main():
    jan_s, jun_s = load_month("jan2026"), load_month("jun2026")
    jan, jun = jan_s.closes, jun_s.closes
    jan_bb, jan_hv = precompute(jan)
    jun_bb, jun_hv = precompute(jun)

    bb_lows = [2, 5, 10, 15, 20, 25, 30, 40]
    hv_maxes = [0.5, 0.8, 1.0, 1.5, 99]
    tps = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.10]
    stops = [0.002, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20]
    holds = [2, 4, 8, 24, 48, 168]
    levs = [1, 3, 5, 10, 20, 50]
    risks = [0.01, 0.02, 0.05, 0.10, 0.25]

    grid = list(itertools.product(bb_lows, hv_maxes, tps, stops, holds, levs, risks))
    total = len(grid) * 2
    print(f"searching {total:,} configurations on real January 2026 data "
          f"({len(jan)} bars)...\n")

    results = []
    for k, (bb, hv, tp, st, hold, lev, risk) in enumerate(grid):
        if k % 20000 == 0 and k:
            print(f"  ...{k * 2:,}/{total:,}")
        for reversion in (True, False):
            r = backtest(jan, jan_bb, jan_hv, bb, 100 - bb, hv, tp, st, hold,
                         lev, risk, DEFAULT_COSTS, reversion)
            if r["trades"] < 10:
                continue
            r.update(bb=bb, hv=hv, tp=tp, stop=st, hold=hold, lev=lev,
                     risk=risk, reversion=reversion)
            results.append(r)

    print(f"\nevaluated {len(results):,} configurations with >=10 trades")

    winners = [r for r in results if meets_goal(r)]

    def show(title, rows):
        print(f"\n=== {title} ===")
        print(f"{'WR%':>7} {'ROI%':>13} {'DD%':>7} {'tr':>4}  bb hv    tp     stop   hold lev risk dir")
        for r in rows:
            print(f"{r['wr']:7.1f} {r['roi']:13.1f} {r['max_dd']:7.2f} {r['trades']:4d}  "
                  f"{r['bb']:>2} {r['hv']:<5} {r['tp']:<6} {r['stop']:<6} {r['hold']:<4} "
                  f"{r['lev']:<3} {r['risk']:<4} {'rev' if r['reversion'] else 'con'}")

    show("HIGHEST WIN RATE", sorted(results, key=lambda r: -r["wr"])[:12])
    show("HIGHEST ROI", sorted(results, key=lambda r: -r["roi"])[:12])
    prof = [r for r in results if r["roi"] > 0]
    if prof:
        show("LOWEST DRAWDOWN (profitable only)", sorted(prof, key=lambda r: r["max_dd"])[:12])
    hi_wr = [r for r in results if r["wr"] > TARGET_WR]
    if hi_wr:
        show("WR>80% ranked by ROI", sorted(hi_wr, key=lambda r: -r["roi"])[:12])

    print("\n=== target attainment (in-sample January) ===")
    print(f"  WR > 80%              : {sum(1 for r in results if r['wr'] > TARGET_WR):,}")
    print(f"  ROI > 1000% / month   : {sum(1 for r in results if r['roi'] > TARGET_MONTHLY_PCT):,}")
    print(f"  DD < 5%               : {sum(1 for r in results if r['max_dd'] < TARGET_DD):,}")
    print(f"  profitable at all     : {len(prof):,}")
    print(f"  WR>80 AND ROI>1000    : {sum(1 for r in results if r['wr'] > TARGET_WR and r['roi'] > TARGET_MONTHLY_PCT):,}")
    print(f"  ALL THREE TARGETS     : {len(winners):,}")

    survivors = []
    if winners:
        print("\n=== out-of-sample validation on June 2026 ===")
        for r in sorted(winners, key=lambda x: -x["roi"])[:50]:
            o = backtest(jun, jun_bb, jun_hv, r["bb"], 100 - r["bb"], r["hv"], r["tp"],
                         r["stop"], r["hold"], r["lev"], r["risk"], DEFAULT_COSTS, r["reversion"])
            ok = meets_goal(o)
            print(f"  IS WR {r['wr']:5.1f} ROI {r['roi']:11.1f} DD {r['max_dd']:5.2f} | "
                  f"OOS WR {o['wr']:5.1f} ROI {o['roi']:11.1f} DD {o['max_dd']:6.2f} tr {o['trades']:3d}  "
                  f"{'PASS' if ok else 'fail'}")
            if ok:
                survivors.append({"is": r, "oos": o})
        print(f"\npassing in-sample AND out-of-sample: {len(survivors)}")

    out = os.path.join(os.path.dirname(__file__), "..", "data", "search_results.json")
    json.dump({
        "evaluated": len(results),
        "winners_in_sample": len(winners),
        "survivors_oos": len(survivors),
        "best_wr": sorted(results, key=lambda r: -r["wr"])[:5],
        "best_roi": sorted(results, key=lambda r: -r["roi"])[:5],
        "survivors": survivors,
    }, open(out, "w"), indent=1)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
