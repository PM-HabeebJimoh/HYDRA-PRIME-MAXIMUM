"""
spec.py — v02M constants, every one traceable to a measurement or a source.

v02M is NOT v01T. It shares no code, no data files and no assumptions.

WHY v02M EXISTS
---------------
v01T was a leveraged symmetric straddle. Its expected value is provably zero
before costs for every choice of stop/target (see V02M_THESIS.md, Theorem 1),
and resolving it on real 1-minute OHLC gave 16.67% win rate / -6.45% ROI.

v02M attacks the goal from the axis that actually produces high win rates in
the real world: many small, repeated, market-neutral captures.

THE TARGET
----------
    WR  > 80%   measured at DAY level (Virtu's own unit of account)
    ROI > 1000% per month
    DD  < 4%

THE ARITHMETIC OF THE TARGET (derived in m2/goal.py, not asserted here)
    required daily return       = 11^(1/30) - 1 = 8.321%/day
    at daily vol 2.0%           -> daily Sharpe 4.16
    daily Sharpe 4.16           -> daily WR ~ 100%, 4-sigma day still positive
    annualized Sharpe required  = 66

BENCHMARK CORRECTION
    Medallion fund-level Sharpe ~ 2.0   (capacity-constrained, $10B)
    Virtu execution-level Sharpe ~ 50   (derived from SEC S-1: 1,237 winning
                                         days out of 1,238; per-TRADE WR 50.4%)
    66 is Virtu-class. It is not a record-breaking number at execution level.

SOURCE: Virtu Financial S-1 (SEC, 2014): "we had only one losing trading day
during the period depicted, a total of 1,238 trading days."
"""

from __future__ import annotations

# ---------------------------------------------------------------- the goal ---
GOAL_MONTHLY_ROI = 10.0          # 1000% = 10x profit = 11x terminal
GOAL_TERMINAL_MULT = 11.0
GOAL_WIN_RATE = 0.80             # measured at DAY level
GOAL_MAX_DD = 0.04
GOAL_DAYS = 30

# ------------------------------------------------------- measured, not assumed ---
# From m2/correlation.py on real July 2026 daily data, 5 instruments.
MEASURED_DIRECTIONAL_RHO = 0.8505   # raw asset-return correlation
MEASURED_RESIDUAL_RHO = 0.4438      # after beta-hedging vs BTC
# N_eff at 111 instruments given those rhos:
#   directional -> 1.17    residual -> 2.23

# ------------------------------------------------------------------ economics ---
# Maker-side economics. The sign flip vs v01T is the point: v01T paid 4bp taker
# per side; a maker EARNS the rebate or at worst pays ~0.
MAKER_FEE_BPS = -0.5      # negative = rebate (KuCoin/Binance VIP maker tiers)
TAKER_FEE_BPS = 4.0       # what v01T was paying, kept for contrast
ADVERSE_SELECTION_HAIRCUT = 0.15   # fraction of gross capture lost to informed flow

# ----------------------------------------------------------------- capacity ---
# The binding constraint. Market impact begins eroding capture above roughly
# 0.1% of an instrument's daily volume.
MAX_VOLUME_PARTICIPATION = 0.001
IMPACT_FLOOR_PARTICIPATION = 0.0005

# --------------------------------------------------------------- risk rails ---
MAX_INVENTORY_PCT = 0.02      # never hold more than 2% of equity net delta
MAX_LEVERAGE = 3              # NOT 50. Inventory is hedged, not levered.
KILL_SWITCH_DD = 0.03         # halt at 3%, before the 4% goal breach
INITIAL_CAPITAL = 10_000.0
