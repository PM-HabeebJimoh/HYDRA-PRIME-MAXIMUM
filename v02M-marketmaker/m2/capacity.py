"""
capacity.py — the REAL binding constraint on v02M.

Sharpe is achievable (see goal.py: 32-66 annualized required, Virtu runs ~50).
Capacity is not negotiable.

A strategy compounding at 8.32%/day needs its traded notional to compound at
the same rate. Traded notional is bounded by a fraction of each venue's real
volume, because above roughly 0.1% participation your own orders move the price
and destroy the 1-2bp capture you were harvesting.

This module computes, from REAL measured volumes:
  - the daily volume required to sustain the target return
  - the day on which the strategy exceeds its participation cap
  - the terminal equity achievable before capacity binds

This is the module that prevents v02M from repeating v01T's central sin of
reporting a number that cannot physically occur.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import spec

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
DATA = os.path.join(_ROOT, "data", "daily_5inst_jul2026.json")


def load_volumes(path: str = DATA) -> Dict[str, float]:
    """Median real daily USD volume per instrument, from the vendored dataset."""
    with open(path) as fh:
        payload = json.load(fh)
    out: Dict[str, float] = {}
    for sym, d in payload["instruments"].items():
        vols = d.get("volume")
        if not vols:
            continue
        s = sorted(vols)
        n = len(s)
        out[sym] = float(s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2)
    return out


@dataclass
class CapacityDay:
    day: int
    equity: float
    required_notional: float
    available_notional: float
    participation: float
    capped: bool


@dataclass
class CapacityReport:
    initial_equity: float
    daily_return: float
    turnover_per_day: float
    total_venue_volume: float
    max_participation: float
    days: List[CapacityDay] = field(default_factory=list)
    first_capped_day: Optional[int] = None
    terminal_equity_uncapped: float = 0.0
    terminal_equity_capped: float = 0.0

    def as_dict(self) -> Dict:
        return {
            "initial_equity": self.initial_equity,
            "daily_return_pct": round(self.daily_return * 100, 4),
            "turnover_per_day": self.turnover_per_day,
            "total_venue_volume_usd": self.total_venue_volume,
            "max_participation": self.max_participation,
            "first_capped_day": self.first_capped_day,
            "terminal_equity_uncapped": round(self.terminal_equity_uncapped, 2),
            "terminal_equity_capped": round(self.terminal_equity_capped, 2),
            "days": [
                {
                    "day": d.day,
                    "equity": round(d.equity, 2),
                    "required_notional": round(d.required_notional, 2),
                    "participation_pct": round(d.participation * 100, 5),
                    "capped": d.capped,
                }
                for d in self.days
            ],
        }


def required_notional(equity: float, daily_return: float, capture_bps: float) -> float:
    """Notional that must be turned over to earn `daily_return` at `capture_bps`.

    profit = notional * capture      ->   notional = equity * daily_return / capture
    """
    capture = capture_bps * 1e-4
    if capture <= 0:
        raise ValueError("capture_bps must be positive")
    return equity * daily_return / capture


def project(initial_equity: float,
            daily_return: float,
            capture_bps: float,
            total_venue_volume: float,
            days: int = 60,
            max_participation: float = spec.MAX_VOLUME_PARTICIPATION) -> CapacityReport:
    """Compound equity and check participation each day. Cap growth when bound."""
    rep = CapacityReport(
        initial_equity=initial_equity,
        daily_return=daily_return,
        turnover_per_day=0.0,
        total_venue_volume=total_venue_volume,
        max_participation=max_participation,
    )
    available = total_venue_volume * max_participation

    eq_uncapped = initial_equity
    eq_capped = initial_equity
    for d in range(days + 1):
        need = required_notional(eq_capped, daily_return, capture_bps)
        part = need / total_venue_volume if total_venue_volume > 0 else float("inf")
        capped = need > available
        rep.days.append(CapacityDay(d, eq_capped, need, available, part, capped))
        if rep.first_capped_day is None and capped:
            rep.first_capped_day = d

        # uncapped path grows freely
        eq_uncapped *= (1 + daily_return)
        # capped path can only earn on the notional it can actually trade
        realised_notional = min(need, available)
        realised_return = realised_notional * capture_bps * 1e-4 / eq_capped
        eq_capped *= (1 + realised_return)

    rep.terminal_equity_uncapped = eq_uncapped
    rep.terminal_equity_capped = eq_capped
    rep.turnover_per_day = required_notional(initial_equity, daily_return, capture_bps)
    return rep


def max_equity_at_capacity(capture_bps: float,
                           daily_return: float,
                           total_venue_volume: float,
                           max_participation: float = spec.MAX_VOLUME_PARTICIPATION) -> float:
    """Largest equity that can still be traded within the participation cap."""
    available = total_venue_volume * max_participation
    capture = capture_bps * 1e-4
    return available * capture / daily_return
