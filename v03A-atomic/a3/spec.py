"""
spec.py — v03A-ATOMIC constants.

EVERY constant below carries a provenance tag:

    [MEASURED]  taken from a real published figure, source named
    [DERIVED]   computed in code from MEASURED values
    [ASSUMED]   an assumption. Flagged loudly. Not validated on-chain.

v03A shares NO code, NO data and NO assumptions with v01T or v02M.

--------------------------------------------------------------------------
WHY v03A EXISTS — the structural break
--------------------------------------------------------------------------
v01T (straddle), v02M (market maker) and every directional variant share
one hidden form:

    profit = YOUR_CAPITAL x leverage x edge
    => required_notional = equity x required_return / edge
    => a TURNOVER MULTIPLE of your own capital
    => bounded by venue volume  -> capacity wall

Measured on real Kraken data, that wall required 103.4% of the entire
venue's daily BTC volume. A 1,034x shortfall against the impact cap.

ATOMIC MEV BREAKS THE FORM. The trade capital is BORROWED via flash loan
and repaid inside the same transaction. Therefore:

    profit_per_trade = f(opportunity size)   <- INDEPENDENT of your capital
    your_capital     = gas/tip reserve ONLY

Your equity is no longer the denominator of the trade. The capacity
constraint stops scaling with your account size.

--------------------------------------------------------------------------
THE THREE DRAWDOWN SOURCES, ENUMERATED EXHAUSTIVELY
--------------------------------------------------------------------------
  1. failed-bundle gas  -> $0   private bundles. Flashbots primary source.
  2. trading loss       -> $0   atomic revert; contract reverts unless
                                profit > gas, so net/win is always positive.
  3. fixed infra burn   -> THE ONLY REMAINING TERM.

Source (Flashbots Auction docs, fetched 2026-07-27, verbatim):
  "uses a first-price sealed-bid auction which allows users to privately
   communicate their bid and granular transaction order preference
   WITHOUT PAYING FOR FAILED BIDS."
  "Failed trade privacy: Losing bids are NEVER INCLUDED IN A BLOCK."
Contrast, public mempool:
  "The all-pay nature of the auction results in FAILED BIDS REVERTING
   ON-CHAIN" -- that is what costs gas.

=> Failed-gas is an artifact of PUBLIC mempool submission. Private bundle
   submission ELIMINATES it. It is not reduced. It is zero.
   PRIVATE SUBMISSION IS THEREFORE MANDATORY, NOT OPTIONAL. See guards.py.
"""

from __future__ import annotations

# ---------------------------------------------------------------- the goal ---
GOAL_MONTHLY_ROI_PCT = 1000.0     # "thousands %" floor
GOAL_DAY_WIN_RATE = 0.80          # measured at DAY level (Virtu unit of account)
GOAL_MAX_DD = 0.04
GOAL_DEAD_DAY_HORIZON = 30        # DD must hold across 30 CONSECUTIVE dead days

# ------------------------------------------------- MEASURED: L2 gas, 2026 ---
# Source: spotedcrypto.com L2 fee survey, April 2026 median per-tx fees.
GAS_BASE_USD = 0.02               # [MEASURED] Base median
GAS_WORLDCHAIN_USD = 0.02         # [MEASURED]
GAS_OP_USD = 0.03                 # [MEASURED] OP Mainnet median
GAS_ARBITRUM_USD = 0.04           # [MEASURED] Arbitrum One median
GAS_ZKSYNC_USD = 0.05             # [MEASURED]
GAS_SCROLL_USD = 0.06             # [MEASURED]
# For contrast, the chain FlashArb actually ran on:
GAS_ETH_MAINNET_USD = 16.50       # [DERIVED] ($12,180+$8,400)/1,247 txs

# ------------------------------------------- MEASURED: infrastructure cost ---
# Free tiers are real and published:
#   Alchemy    30M compute units/month  = $0   [alchemy.com 2026]
#   dRPC       210M CU/month            = $0   [Chainstack RPC survey 2026]
#   Chainstack 3M requests/month        = $0   [chainstack.com 2026]
# Cheapest paid entry actually published:
INFRA_CHAINSTACK_ENTRY_USD_MO = 5.0      # [MEASURED]
INFRA_FREE_TIER_USD_MO = 0.50            # [ASSUMED] nominal, not literally $0
INFRA_FLASHARB_MAINNET_USD_MO = 700.0    # [MEASURED] $2,100 / 3 months

# ------------------------- MEASURED: FlashArb production disclosure (3 mo) ---
# Source: dev.to "The Arbitrage Bot Arms Race: What We Learned Running
# FlashArb in Production". Full cost breakdown disclosed by the operator.
FA_TX_SUBMITTED = 1247            # [MEASURED]
FA_TX_SUCCESS = 892               # [MEASURED]
FA_GROSS_USD = 47_320.0           # [MEASURED]
FA_GAS_SUCCESS_USD = 12_180.0     # [MEASURED]
FA_GAS_FAILED_USD = 8_400.0       # [MEASURED] -> becomes $0 with private bundles
FA_INFRA_USD = 2_100.0            # [MEASURED]
FA_DAYS = 90                      # [MEASURED]

# ------------------------------------------ MEASURED: Solana Vpe operator ---
# Source: Helius "Solana MEV Report", 30-day window Dec 7 - Jan 5.
SOL_TX_30D = 1_550_000            # [MEASURED]
SOL_SUCCESS_RATE = 0.889          # [MEASURED]
SOL_GROSS_USD_30D = 13_430_000.0  # [MEASURED]
SOL_TIPS_USD_30D = 4_630_000.0    # [MEASURED]
SOL_AVG_PROFIT_PER_TX = 8.67      # [MEASURED]

# --------------------------------------------------- THE CENTRAL ASSUMPTION ---
# *** THIS IS THE ONE UNVALIDATED INPUT IN THE ENTIRE MODEL. ***
# FlashArb's win frequency and per-win gross were measured on ETHEREUM
# MAINNET. We project them onto an L2. L2s have lower competition but
# smaller pools, so opportunities are smaller. We apply a 10x PENALTY to
# per-win gross and keep the win frequency unchanged.
#
# It is deliberately pessimistic on SIZE. It is NOT validated on-chain.
# No bot has been run on Base to count actual fills. Treat every ROI number
# downstream of this constant as PROJECTED, not MEASURED.
L2_OPPORTUNITY_PENALTY = 10.0     # [ASSUMED] <-- the load-bearing assumption

# --------------------------------------------------------------- risk rails ---
REQUIRE_PRIVATE_BUNDLES = True    # non-negotiable; see guards.py
KILL_SWITCH_DD = 0.03             # halt at 3%, before the 4% goal breach
MIN_PROFIT_MULTIPLE_OF_GAS = 2.0  # never submit unless profit >= 2x gas
