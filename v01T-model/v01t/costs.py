"""
costs.py — the trading cost model.

At 50x leverage the notional is 50x equity, so every cost expressed in basis
points of *notional* becomes 50x that in percent of *equity*. A 4bp taker fee is
0.04% of notional = 2.0% of equity per side. This module makes those costs
explicit instead of folding them into a single assumed net edge.
"""

from __future__ import annotations

from dataclasses import dataclass

BPS = 1e-4


@dataclass(frozen=True)
class CostModel:
    """Round-trip trading costs, all quoted in basis points of notional."""

    spread_bps: float = 1.0        # half-spread paid on each side
    taker_fee_bps: float = 4.0     # exchange taker fee per side
    slippage_bps: float = 0.5      # adverse fill slippage per side
    funding_bps_8h: float = 1.0    # perpetual funding, charged per 8h held

    # ------------------------------------------------------------- entry/exit ---

    def entry_price(self, mid: float, direction: int) -> float:
        """Fill price after crossing the spread and slipping."""
        adverse = (self.spread_bps + self.slippage_bps) * BPS
        return mid * (1 + adverse) if direction > 0 else mid * (1 - adverse)

    def exit_price(self, mid: float, direction: int) -> float:
        """Exit fills are adverse in the opposite direction."""
        adverse = (self.spread_bps + self.slippage_bps) * BPS
        return mid * (1 - adverse) if direction > 0 else mid * (1 + adverse)

    # ------------------------------------------------------------------- fees ---

    def fee(self, notional: float) -> float:
        """Exchange fee for one side."""
        return abs(notional) * self.taker_fee_bps * BPS

    def round_trip_fee(self, entry_notional: float, exit_notional: float) -> float:
        return self.fee(entry_notional) + self.fee(exit_notional)

    def funding(self, notional: float, hours_held: float) -> float:
        """Funding accrues continuously against the 8h rate."""
        return abs(notional) * self.funding_bps_8h * BPS * (hours_held / 8.0)

    # -------------------------------------------------------------- diagnostics ---

    def round_trip_cost_pct_of_notional(self) -> float:
        """Total round-trip cost as a fraction of notional, funding excluded."""
        per_side = (self.spread_bps + self.slippage_bps + self.taker_fee_bps) * BPS
        return 2 * per_side

    def round_trip_cost_pct_of_equity(self, leverage: int) -> float:
        """The same cost expressed against equity — this is the number that bites."""
        return self.round_trip_cost_pct_of_notional() * leverage

    def breakeven_move_pct(self) -> float:
        """Minimum favourable price move required just to cover round-trip costs."""
        return self.round_trip_cost_pct_of_notional()


ZERO_COSTS = CostModel(spread_bps=0.0, taker_fee_bps=0.0, slippage_bps=0.0, funding_bps_8h=0.0)
"""Frictionless model — reproduces the original spec's implicit assumption."""

DEFAULT_COSTS = CostModel()
"""Realistic crypto-perp costs."""
