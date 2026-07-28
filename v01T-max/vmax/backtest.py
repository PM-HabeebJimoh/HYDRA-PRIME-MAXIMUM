"""
backtest.py — the honest v01T resolver plus the parameter sweep that repaired it.

THE CRITICAL DIFFERENCE FROM v01T
---------------------------------
v01T's `expansion_win` asked only: did |move| reach 0.5% within the window?
It never checked whether a leg had already been stopped. That is why it
reported 100% win rates.

`resolve_double_entry` below enforces the rule that makes the double entry
real: A STOPPED LEG IS DEAD AND CANNOT LATER WIN.

    LONG  leg: stop entry*(1-S), target entry*(1+T)
    SHORT leg: stop entry*(1+S), target entry*(1-T)

    win   a STILL-OPEN leg reaches its target -> +T on the winner, -S on the
          other (price must have crossed the other leg's stop to get there)
    loss  both legs stopped before any target -> -2S
    time  window expires -> surviving legs marked to the final close
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from . import spec

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_DATA = os.path.join(os.path.dirname(_ROOT), "v01T-model", "data")

MONTHS = ("jan2026", "jun2026", "jul2026")


# ------------------------------------------------------------------- data ---

def load_closes(month: str) -> List[float]:
    """Real vendored BTC hourly closes (Yahoo Finance Chart API v8)."""
    path = os.path.join(_DATA, f"btc_usd_1h_{month}.json")
    with open(path) as fh:
        return list(json.load(fh)["closes"])


# ------------------------------------------------------------- indicators ---
# Reimplemented rather than imported so v01T-max is self-contained and the
# arithmetic is auditable in one place. Matches v01t/indicators.py exactly,
# including v01T's population-vs-sample stdev quirk.

def bb_percentile(closes: Sequence[float]) -> float:
    if len(closes) < spec.BB_WINDOW:
        return 50.0
    w = list(closes[-spec.BB_WINDOW:])
    sma = sum(w) / spec.BB_WINDOW
    var = sum((x - sma) ** 2 for x in w) / len(w)      # population stdev
    sd = var ** 0.5
    if sd == 0:
        return 50.0
    lo, hi = sma - 2 * sd, sma + 2 * sd
    if hi == lo:
        return 50.0
    return round((closes[-1] - lo) / (hi - lo) * 100, 2)


def hv_ratio(closes: Sequence[float]) -> float:
    if len(closes) < spec.HV_MIN_CLOSES:
        return 1.0
    rets = [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes))]
    if len(rets) < spec.HV_LONG_WINDOW:
        return 1.0

    def sd(xs):                                         # sample stdev (n-1)
        n = len(xs)
        if n < 2:
            return 0.0
        m = sum(xs) / n
        return (sum((x - m) ** 2 for x in xs) / (n - 1)) ** 0.5

    s = sd(rets[-spec.HV_SHORT_WINDOW:])
    l = sd(rets[-spec.HV_LONG_WINDOW:])
    return 1.0 if l == 0 else round(s / l, 3)


def is_elite(bb: float, hv: float) -> bool:
    """The v01T gate, unchanged."""
    return (bb < spec.BB_LOW or bb > spec.BB_HIGH) and hv < spec.HV_MAX


def find_signals(closes: Sequence[float],
                 window: int = spec.RESOLUTION_WINDOW) -> List[Tuple[int, float]]:
    out = []
    for i in range(spec.HV_MIN_CLOSES, len(closes) - window):
        w = closes[: i + 1]
        if is_elite(bb_percentile(w), hv_ratio(w)):
            out.append((i, closes[i]))
    return out


# -------------------------------------------------------------- resolution ---

def resolve_double_entry(closes: Sequence[float], idx: int, entry: float,
                         stop: float, target: float,
                         window: int = spec.RESOLUTION_WINDOW) -> float:
    """Net price move of the pair. A stopped leg is DEAD and cannot win."""
    if entry <= 0:
        raise ValueError("entry must be positive")
    long_open = short_open = True
    for f in closes[idx + 1: idx + 1 + window]:
        ch = (f - entry) / entry
        if long_open and ch >= target:
            return target - stop
        if short_open and ch <= -target:
            return target - stop
        if long_open and ch <= -stop:
            long_open = False
        if short_open and ch >= stop:
            short_open = False
        if not long_open and not short_open:
            return -2 * stop
    last = closes[min(idx + window, len(closes) - 1)]
    ch = (last - entry) / entry
    return (ch if long_open else -stop) + (-ch if short_open else -stop)


# ------------------------------------------------------------------ report ---

@dataclass
class Result:
    stop: float
    target: float
    trades: int
    wins: int
    gross_total: float

    @property
    def win_rate_pct(self) -> float:
        return self.wins / self.trades * 100 if self.trades else 0.0

    @property
    def gross_per_trade(self) -> float:
        return self.gross_total / self.trades if self.trades else 0.0

    def net_per_trade(self, cost: float = spec.MAKER_COST_PCT) -> float:
        return self.gross_per_trade - cost

    def as_dict(self) -> Dict:
        return {
            "stop": self.stop, "target": self.target, "trades": self.trades,
            "wins": self.wins, "win_rate_pct": round(self.win_rate_pct, 4),
            "gross_per_trade": round(self.gross_per_trade, 8),
            "net_per_trade_maker": round(self.net_per_trade(), 8),
            "net_per_trade_taker": round(
                self.net_per_trade(spec.TAKER_COST_PCT), 8),
        }


def run(stop: float, target: float,
        months: Sequence[str] = MONTHS) -> Result:
    """Backtest one bracket across the real months."""
    if stop <= 0 or target <= 0:
        raise ValueError("stop and target must be positive")
    if stop >= target:
        raise ValueError("stop must be smaller than target")
    n = w = 0
    tot = 0.0
    for m in months:
        c = load_closes(m)
        for idx, price in find_signals(c):
            r = resolve_double_entry(c, idx, price, stop, target)
            tot += r
            n += 1
            if r > 0:
                w += 1
    return Result(stop, target, n, w, tot)


def outcomes(stop: float, target: float,
             months: Sequence[str] = MONTHS) -> List[float]:
    """Every individual real trade outcome. Input to the bootstrap."""
    out = []
    for m in months:
        c = load_closes(m)
        for idx, price in find_signals(c):
            out.append(resolve_double_entry(c, idx, price, stop, target))
    return out


def per_month(stop: float, target: float) -> Dict[str, Result]:
    """Stability check: each month scored independently."""
    return {m: run(stop, target, months=(m,)) for m in MONTHS}


def sweep(stops: Sequence[float] = (0.0005, 0.001, 0.002, 0.003, 0.005,
                                    0.0075, 0.01),
          targets: Sequence[float] = (0.005, 0.0075, 0.01, 0.015)
          ) -> List[Result]:
    """The sweep that located the repair."""
    res = []
    for s in stops:
        for t in targets:
            if s < t:
                res.append(run(s, t))
    return res
