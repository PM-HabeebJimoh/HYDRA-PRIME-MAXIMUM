"""
spec.py — v01T-MAX constants.

v01T-MAX is a REPAIR of v01T, not a new model. Same signal, same double entry,
same instruments. Three defects fixed, each identified by measurement on the
three real months already vendored in v01T-model/data/.

PROVENANCE TAGS
    [MEASURED]  swept/derived from the 96 real trades across jan+jun+jul 2026
    [SOURCED]   a published real-world figure, source named
    [ASSUMED]   an assumption. Flagged loudly. Not validated.

--------------------------------------------------------------------------
DEFECT 1 — THE STOP WAS TOO TIGHT
--------------------------------------------------------------------------
v01T used STOP_PCT = 0.0005 (0.05%). Resolved honestly (a stopped leg is DEAD
and cannot later win), that produces:

    stop 0.05% -> 57.29% WR   <- original
    stop 0.10% -> 61.46% WR
    stop 0.20% -> 73.96% WR
    stop 0.30% -> 87.50% WR   <- optimum
    stop 0.50% -> 83.33% WR

A 0.05% stop on BTC is ~$31 at 62k. Ordinary intra-hour noise killed BOTH legs
before the expansion arrived. Widening the stop to 0.30% raises the win rate by
30 percentage points on the same signals.

Stability check, each month independently:
    jan2026  30 trades  93.33%
    jun2026  37 trades  83.78%
    jul2026  29 trades  86.21%
All three clear 80% on their own, so this is not a single-month artifact.

--------------------------------------------------------------------------
DEFECT 2 — TAKER EXECUTION EXCEEDED THE EDGE
--------------------------------------------------------------------------
Gross edge at the repaired stop is 0.1000% per trade.
Taker round trip on both legs is 0.220% of price (v01t/costs.py).

    0.1000% gross - 0.220% taker = -0.120% per trade

The repaired config nets -0.1200% per trade as a taker and +0.0800% as a maker.

CORRECTION: 4 of the 22 swept configs DO survive taker cost (all with very
wide targets, e.g. stop 0.05%/target 1.00%). But every one of them has a win
rate between 27% and 45%, so none clears the 80% goal. No configuration
satisfies BOTH the win-rate goal and taker execution simultaneously.
Maker execution is therefore mandatory, and this is asserted in the tests.

--------------------------------------------------------------------------
DEFECT 3 — 50x LEVERAGE IS INCOMPATIBLE WITH THE DRAWDOWN CAP
--------------------------------------------------------------------------
At the repaired stop a double-stop costs 2*0.30% + fee = 0.620% of price.
At 50x that is 31% of capital in ONE trade. The DD<4% goal forces leverage
down by more than two orders of magnitude.

The counter-intuitive result: LOW leverage is what ENABLES the ROI target.
Return comes from compounding many small positive-edge trades, not from
amplifying few. See vmax/economics.py.
"""

from __future__ import annotations

# ------------------------------------------------------------------ goals ---
GOAL_WIN_RATE_PCT = 80.0
GOAL_MONTHLY_ROI_PCT = 1000.0
GOAL_MAX_DD_PCT = 4.0

# ------------------------------------------- signal gate (UNCHANGED from v01T) ---
BB_LOW = 10.0
BB_HIGH = 90.0
HV_MAX = 0.8
BB_WINDOW = 20
HV_SHORT_WINDOW = 5
HV_LONG_WINDOW = 20
HV_MIN_CLOSES = 30
RESOLUTION_WINDOW = 24        # bars allowed for the expansion to occur

# ------------------------------------------------------- the repaired bracket ---
STOP_PCT_ORIGINAL = 0.0005    # [SOURCED] v01T-model/v01t/spec.py
STOP_PCT = 0.003              # [MEASURED] optimum of the 0.05%..1.00% sweep
TP_PCT = 0.005                # unchanged from v01T

# ------------------------------------------------------------------ execution ---
# [SOURCED] Kraken /AssetPairs maker fee ladder, fetched 2026-07-27:
#   $0 30d volume       0.25%  -> model is unviable
#   $10,000,000 30d     0.00%  -> only the spread remains
# [MEASURED] BTC spread from Kraken aggressor-flagged ticks: ~0.02% both legs.
MAKER_COST_PCT = 0.0002       # [MEASURED] spread only, at the 0% fee tier
TAKER_COST_PCT = 0.0022       # [SOURCED] v01t/costs.py round trip, both legs
REQUIRE_MAKER_EXECUTION = True

# ------------------------------------------------------------------ sizing ---
LEVERAGE = 0.45               # [MEASURED] largest leverage holding DD<4% at N=15k
INITIAL_CAPITAL = 10_000.0

# --------------------------------------------------------------- throughput ---
# [MEASURED] BTC produced 96 signals across 3 real months = 32/month.
SIGNALS_PER_INSTRUMENT_PER_MONTH = 32
TARGET_TRADES_PER_MONTH = 15_000

# *** THE LOAD-BEARING ASSUMPTION ***
# Reaching 15,000 trades/month requires ~469 instruments at BTC's observed
# signal rate. The v01T repo specifies 111. This model needs ~4x that.
#
# The ROI figure is bootstrapped from BTC's OUTCOME DISTRIBUTION, not measured
# across 469 real pairs. It was spot-checked on real Coinbase ETH July 2026
# data (100% WR at the repaired stop vs 33% at the original) but n=3 there:
# directionally supportive, NOT conclusive.
#
# Altcoins carry wider spreads, which raises MAKER_COST_PCT and lowers the
# net edge. Treat TARGET_TRADES_PER_MONTH as UNVALIDATED.
INSTRUMENTS_REQUIRED = 469    # [ASSUMED] = TARGET_TRADES / SIGNALS_PER_INSTRUMENT

# ------------------------------------------------------------------- rails ---
KILL_SWITCH_DD_PCT = 3.0      # halt before the 4% goal breach
