"""
sizing.py — position sizing and lot-size calculation.

Answers the question the spec constants imply but never computed:
given equity, a risk budget, a stop distance and a leverage/margin cap, how
large is the position?

Risk-based size:      units = (equity * risk_pct) / (stop_distance_in_price)
Leverage cap:         units <= (equity * leverage) / entry_price
Final size:           the smaller of the two, floored to the lot step.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from . import spec


@dataclass(frozen=True)
class Position:
    """A fully specified position, ready to open."""

    units: float               # position size in base units (e.g. BTC)
    notional: float            # units * entry price, in quote currency
    margin: float              # notional / leverage
    risk_amount: float         # cash at risk if the stop is hit
    risk_pct_of_equity: float
    effective_leverage: float
    stop_distance: float       # absolute price distance to the stop
    capped_by: str             # "risk" | "leverage" | "min_lot"

    @property
    def is_open(self) -> bool:
        return self.units > 0


@dataclass(frozen=True)
class Sizer:
    """Position sizer honouring the risk budget, leverage cap and lot step."""

    risk_pct: float = spec.RISK_PCT           # 2.5% of equity risked per trade
    leverage: int = spec.LEVERAGE             # 50x
    lot_step: float = 1e-6                    # minimum tradable increment
    min_lot: float = 1e-6
    max_margin_pct: float = 1.0               # never commit more than 100% equity

    def stop_distance(self, entry_price: float, stop_pct: float = spec.STOP_PCT) -> float:
        """Absolute price distance from entry to stop."""
        return entry_price * stop_pct

    def floor_to_step(self, units: float) -> float:
        if self.lot_step <= 0:
            return units
        return math.floor(units / self.lot_step) * self.lot_step

    def size(
        self,
        equity: float,
        entry_price: float,
        stop_pct: float = spec.STOP_PCT,
    ) -> Position:
        """Compute the position for this equity, entry and stop."""
        if equity <= 0 or entry_price <= 0:
            return Position(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "min_lot")

        stop_dist = self.stop_distance(entry_price, stop_pct)
        if stop_dist <= 0:
            return Position(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "min_lot")

        # 1. risk-based size: losing `stop_dist` per unit must cost risk_pct of equity
        risk_budget = equity * self.risk_pct
        units_by_risk = risk_budget / stop_dist

        # 2. leverage/margin cap
        max_notional = equity * self.leverage * self.max_margin_pct
        units_by_leverage = max_notional / entry_price

        if units_by_risk <= units_by_leverage:
            units, capped_by = units_by_risk, "risk"
        else:
            units, capped_by = units_by_leverage, "leverage"

        units = self.floor_to_step(units)
        if units < self.min_lot:
            return Position(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, stop_dist, "min_lot")

        notional = units * entry_price
        return Position(
            units=units,
            notional=notional,
            margin=notional / self.leverage,
            risk_amount=units * stop_dist,
            risk_pct_of_equity=(units * stop_dist) / equity,
            effective_leverage=notional / equity,
            stop_distance=stop_dist,
            capped_by=capped_by,
        )


DEFAULT_SIZER = Sizer()
