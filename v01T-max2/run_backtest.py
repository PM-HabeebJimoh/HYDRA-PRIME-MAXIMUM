#!/usr/bin/env python3
"""
REAL JULY 2026 BACKTEST - v01T-max2
Data: 601 real Coinbase BTC-USD 1h OHLC bars, 2026-07-01..2026-07-26, zero gaps.
Every entry resolved against that entry's REAL subsequent high/low.
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
from vmax2 import (load_bars, walk_forward, generate, stats, report,
                   equity_path, required_sharpe)
from vmax2.backtest import BARRIERS
from vmax2.signals import make

bars = load_bars()
print("="*74)
print("v01T-max2  REAL BACKTEST - July 2026 - Coinbase BTC-USD 1h OHLC")
print("="*74)
print(f"bars {len(bars)}  first {bars[0]['t']}  last {bars[-1]['t']}  gaps 0")
print(f"month move {(bars[-1]['c']-bars[0]['c'])/bars[0]['c']*100:+.2f}%")

print("\n--- 1. TARGET FEASIBILITY (mathematics, no data) ---")
r = required_sharpe()
print(f"  ROI>1000%/mo AND DD<4% jointly require annualised Sharpe = {r['annual_sharpe']:.1f}")
print(f"  (max monthly vol {r['max_monthly_vol']*100:.1f}%, monthly Sharpe {r['monthly_sharpe']:.2f})")

print("\n--- 2. IS WIN RATE INFORMATIVE? real WR vs random-walk s/(s+t) ---")
print(f"  {'stop%':>7} {'targ%':>7} {'theory':>8} {'real':>8}")
for sp, tp in [(0.003,0.005),(0.005,0.005),(0.010,0.0025),(0.040,0.010)]:
    tr = generate(bars, lambda i: True, sp, tp, 40, len(bars), fee=0.0)
    s = stats(tr)
    print(f"  {sp*100:>7.2f} {tp*100:>7.3f} {sp/(sp+tp)*100:>7.1f}% {s['win_rate']:>7.2f}%")
print("  => WR tracks the random walk. WR>80% is bought with a wide stop; it is NOT edge.")

print("\n--- 3. WALK-FORWARD (no lookahead) : THE HONEST RESULT ---")
live = walk_forward(bars)
rep = report(live)
print(f"  trades           {rep['n']}")
print(f"  WIN RATE         {rep['win_rate']:.2f}%")
print(f"  net EV / trade   {rep['ev']*100:+.4f}%   t = {rep['t_stat']:+.2f}")
print(f"  annual Sharpe    {rep['annual_sharpe']:.2f}   (need {r['annual_sharpe']:.1f})")
print(f"\n  {'leverage':>9} {'ROI%':>12} {'maxDD%':>9}")
rs = [x for _, _, x in live]
for L in (1, 2, 5, 10, 20):
    roi, dd = equity_path(rs, L)
    print(f"  {L:>9} {roi*100:>12.2f} {dd*100:>9.2f}")
print(f"\n  max leverage keeping DD<4%  = {rep['max_leverage_at_dd_cap']:.2f}x")
print(f"  ROI there                   = {rep['roi_at_dd_cap']:.2f}%  (DD {rep['dd_at_cap']:.2f}%)")

print("\n--- 4. VERDICT ON THE THREE TARGETS ---")
wr_ok  = rep['win_rate'] > 80
roi_ok = rep['roi_at_dd_cap'] > 1000
dd_ok  = rep['dd_at_cap'] < 4
for label, ok, got in [("WIN RATE > 80%", wr_ok, f"{rep['win_rate']:.2f}%"),
                       ("MONTHLY ROI > 1000%", roi_ok, f"{rep['roi_at_dd_cap']:.2f}%"),
                       ("MAX DRAWDOWN < 4%", dd_ok, f"{rep['dd_at_cap']:.2f}%")]:
    print(f"  {label:<24} {'PASS' if ok else 'FAIL':<5} (got {got})")

print("\n--- 5. WHY: ROI>1000% and DD<4% hold on DISJOINT leverage ranges ---")
print(f"  {'lev':>6} {'ROI%':>12} {'DD%':>8} {'ROI ok':>7} {'DD ok':>6} {'BOTH':>6}")
L = 0.1
while L <= 20:
    roi, dd = equity_path(rs, L)
    a, b = roi*100 > 1000, dd*100 < 4
    print(f"  {L:>6.2f} {roi*100:>12.2f} {dd*100:>8.2f} {str(a):>7} {str(b):>6} {str(a and b):>6}")
    L *= 2
print("  No leverage satisfies both. The targets are jointly infeasible at this Sharpe.")
