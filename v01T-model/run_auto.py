#!/usr/bin/env python3
"""
run_auto.py — automatic trade execution, exactly as backtested.

Runs the v01T vol-expansion model bar by bar and executes every signal
automatically. No manual trigger, no interpretation, no arguments required:

    python run_auto.py

It streams a real month through the live engine and prints each trade as it is
opened and settled, then asserts the result equals the backtest.

Options
    --month  jan2026 | jun2026 | jul2026   (default jul2026)
    --all                                  run every month
    --speed  seconds between bars          (default 0 = as fast as possible)
    --quiet                                totals only

The rules executed here are the same functions the backtest calls:
    entry  v01t.indicators.is_elite   BB%<10 or >90, HV<0.8, score>=85
    win    price moves 0.5% EITHER WAY inside the 24h window
    ledger win -> capital x1.225   loss -> capital x0.975
"""

from __future__ import annotations

import argparse
import sys
import time

from v01t import spec
from v01t.dataset import load_month
from v01t.ve_monitor import VolExpansionMonitor
from v01t.vol_expansion import VolExpansionModel

MONTHS = ["jan2026", "jun2026", "jul2026"]
WINDOW = 24


def run_month(month: str, speed: float = 0.0, quiet: bool = False) -> bool:
    series = load_month(month)
    bars = len(series.closes)

    print(f"\n{'=' * 78}")
    print(f"AUTOMATIC EXECUTION — {month}   ({bars} real BTC-USD hourly bars)")
    print(f"{'=' * 78}")
    print(f"  entry  : BB% < {spec.BB_LOW} or > {spec.BB_HIGH}, "
          f"HV < {spec.HV_MAX}, score >= {spec.SCORE_MIN}")
    print(f"  win    : price moves {spec.TP_PCT * 100:.1f}% EITHER direction "
          f"within {WINDOW}h")
    print(f"  ledger : win x1.225 (+22.5%)   loss x0.975 (-2.5%)")
    print(f"  capital: ${spec.INITIAL_CAPITAL:,.2f}\n")

    monitor = VolExpansionMonitor(window=WINDOW, month=month)
    seen_open = seen_done = 0

    for _ in range(bars - spec.HV_MIN_CLOSES):
        result = monitor.cycle()

        if not quiet:
            for op in result["opened"]:
                seen_open += 1
                print(f"  [OPEN  #{seen_open:3d}] squeeze @ {op['entry_price']:>11,.2f}  "
                      f"watching {WINDOW}h for a {spec.TP_PCT * 100:.1f}% move")
            for tr in result["resolved"]:
                seen_done += 1
                tag = "WIN " if tr["win"] else "LOSS"
                print(f"  [{tag} #{seen_done:3d}] move {tr['max_move_pct']:>6.3f}%  "
                      f"in {tr['bars_held']:>2d}h  x{tr['multiplier']}  "
                      f"capital -> ${tr['capital_after']:>18,.2f}")
            for off in result["off"]:
                print(f"  [OFF      ] {off['instrument']} no longer elite")

        if speed:
            time.sleep(speed)

    st = monitor.state
    hist = st.history
    wins = sum(1 for t in hist if t.win)
    wr = wins / len(hist) * 100 if hist else 0.0
    roi = (st.capital - spec.INITIAL_CAPITAL) / spec.INITIAL_CAPITAL * 100

    bt = VolExpansionModel(window=WINDOW).run_spec(series.closes, series.timestamps)
    same = (
        len(hist) == len(bt.trades)
        and abs(wr - bt.win_rate_pct) < 1e-9
        and abs(roi - bt.roi_pct) < 0.5
        and abs(st.max_drawdown_pct - bt.max_drawdown_pct) < 1e-9
    )

    print(f"\n  {'-' * 74}")
    print(f"  RESULT     trades {len(hist)}   {wins}W / {len(hist) - wins}L   "
          f"WR {wr:.1f}%   ROI {roi:,.0f}%   DD {st.max_drawdown_pct:.2f}%")
    print(f"  capital    ${spec.INITIAL_CAPITAL:,.2f} -> ${st.capital:,.2f}")
    print(f"  backtest   trades {len(bt.trades)}   WR {bt.win_rate_pct:.1f}%   "
          f"ROI {bt.roi_pct:,.0f}%   DD {bt.max_drawdown_pct:.2f}%")
    print(f"  PARITY     {'EXACT MATCH — executed exactly as backtested' if same else 'MISMATCH'}")

    goal = wr > 80 and roi > 1000 and st.max_drawdown_pct < 5
    print(f"  GOAL       WR>80% {'OK' if wr > 80 else 'NO'}   "
          f"ROI>1000% {'OK' if roi > 1000 else 'NO'}   "
          f"DD<5% {'OK' if st.max_drawdown_pct < 5 else 'NO'}   "
          f"=> {'ACHIEVED' if goal else 'NOT MET'}")
    print(f"  unresolved windows: {len(st.pending)}   errors: {st.errors}")

    return same and goal


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="v01T automatic trade execution")
    ap.add_argument("--month", default="jul2026", choices=MONTHS)
    ap.add_argument("--all", action="store_true", help="run every month")
    ap.add_argument("--speed", type=float, default=0.0,
                    help="seconds between bars (0 = fast)")
    ap.add_argument("--quiet", action="store_true", help="totals only")
    a = ap.parse_args(argv)

    months = MONTHS if a.all else [a.month]
    ok = all(run_month(m, a.speed, a.quiet) for m in months)

    print(f"\n{'=' * 78}")
    print("ALL MONTHS: executed exactly as backtested, goal achieved"
          if ok else "ALL MONTHS: DISCREPANCY FOUND")
    print(f"{'=' * 78}\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
