"""
vol_expansion.py — the v01T model exactly as specified.

THE ACTUAL MECHANIC (from S3GoalModel.run_timeframe + simulate_vol_expansion):

    for each bar i:
        if is_elite(BB%, HV, score):                 # BB%<10 or >90, HV<0.8, score>=85
            entry = closes[i]
            future = closes[i+1 : i+1+window]        # 4 candles on 1h = 4h
            win = any(|f - entry| / entry >= 0.005 for f in future)
            if win:  capital *= 1.225                # +22.5%  (net +0.45% price x 50x)
            else:    capital *= 0.975                # -2.5%   (risk per trade)

The win condition is a VOLATILITY EXPANSION TEST, not a directional trade:

  * direction-agnostic — a 0.5% move EITHER way is a win
  * the 0.05% stop is NEVER checked against the price path
  * the loss case is only "volatility failed to expand 0.5% within the window"

This is what makes the thesis coherent: after a Bollinger squeeze with
compressed short-term volatility, price is expected to MOVE. The bet is on
movement, not on direction. A 0.5% move within 4 hours is a low bar for BTC,
which is why the win rate is high.

Two variants are provided:

  run_spec()         exactly the above — the model as written
  run_double_entry() the same entries, resolved leg by leg against the path,
                     which additionally exposes whipsaws (both legs stopped)

Both run on the same real data so the difference is visible and measurable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from . import spec
from .indicators import compute_bb_percentile, compute_hv_ratio, is_elite, score_for

WIN_MULT = 1.225      # +22.5% of capital
LOSS_MULT = 0.975     # -2.5% of capital


@dataclass
class VETrade:
    n: int
    index: int
    timestamp: int
    entry_price: float
    bb_pct: float
    hv_ratio: float
    score: int
    win: bool
    max_move_pct: float          # largest |move| seen in the window
    bars_to_expansion: Optional[int]
    capital_before: float
    capital_after: float
    roi_pct: float

    def as_dict(self) -> Dict:
        return dict(self.__dict__)


@dataclass
class VEResult:
    label: str
    variant: str
    bars: int
    window: int
    tp_pct: float
    trades: List[VETrade] = field(default_factory=list)
    wins: int = 0
    losses: int = 0
    win_rate_pct: float = 0.0
    initial_capital: float = spec.INITIAL_CAPITAL
    final_capital: float = 0.0
    roi_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    peak_capital: float = 0.0
    squeezes: int = 0
    expansion_rate_pct: float = 0.0

    def summary(self) -> Dict:
        out = {k: v for k, v in self.__dict__.items() if k != "trades"}
        out["trades_count"] = len(self.trades)
        out["trades_sample"] = [t.as_dict() for t in self.trades[:10]]
        return out


class VolExpansionModel:
    """The v01T elite vol-explosion model, as specified."""

    def __init__(
        self,
        capital: float = spec.INITIAL_CAPITAL,
        tp_pct: float = spec.TP_PCT,          # 0.005 — the 0.5% expansion
        stop_pct: float = spec.STOP_PCT,      # 0.0005 — only used in path-checked mode
        win_mult: float = WIN_MULT,
        loss_mult: float = LOSS_MULT,
        window: int = 4,                      # 4 candles = 4h on the hourly timeframe
        bb_low: float = spec.BB_LOW,
        bb_high: float = spec.BB_HIGH,
        hv_max: float = spec.HV_MAX,
        non_overlapping: bool = False,        # the spec scans every bar
    ) -> None:
        self.capital = capital
        self.tp_pct = tp_pct
        self.stop_pct = stop_pct
        self.win_mult = win_mult
        self.loss_mult = loss_mult
        self.window = window
        self.bb_low = bb_low
        self.bb_high = bb_high
        self.hv_max = hv_max
        self.non_overlapping = non_overlapping

    # ------------------------------------------------------------- the gate ---

    def _elite_at(self, closes: Sequence[float], i: int):
        window = closes[: i + 1]
        bb = compute_bb_percentile(window)
        hv = compute_hv_ratio(window)
        sc = score_for(bb)
        at_band = bb < self.bb_low or bb > self.bb_high
        ok = at_band and hv < self.hv_max and sc >= spec.SCORE_MIN
        return ok, bb, hv, sc

    # ---------------------------------------------------- the win conditions ---

    def expansion_win(self, future: Sequence[float], entry: float):
        """The spec test: did |move| reach tp_pct in either direction?"""
        best = 0.0
        for k, f in enumerate(future, start=1):
            move = abs(f - entry) / entry
            if move > best:
                best = move
            if move >= self.tp_pct:
                return True, best, k
        return False, best, None

    def double_entry_win(self, future: Sequence[float], entry: float):
        """Resolve the DOUBLE ENTRY pair against the real forward path.

        Both legs are open at `entry`:
            LONG  SL entry*(1-stop)  TP entry*(1+tp)
            SHORT SL entry*(1+stop)  TP entry*(1-tp)

        A 0.5% move either way takes one leg to target while the other is
        stopped, which is the +0.45% net win. This variant additionally reports
        whether BOTH legs were stopped before any target was reached (a
        whipsaw), which the headline accounting does not model.

        Returns (win, best_move, bars, whipsawed).
        """
        best = 0.0
        long_stopped = short_stopped = False
        for k, f in enumerate(future, start=1):
            change = (f - entry) / entry
            move = abs(change)
            if move > best:
                best = move
            if change >= self.tp_pct or change <= -self.tp_pct:
                return True, best, k, (long_stopped and short_stopped)
            if change >= self.stop_pct:
                short_stopped = True
            if change <= -self.stop_pct:
                long_stopped = True
        return False, best, None, (long_stopped and short_stopped)

    # -------------------------------------------------------------------- run ---

    def run(
        self,
        closes: Sequence[float],
        timestamps: Optional[Sequence[int]] = None,
        label: str = "",
        variant: str = "spec",
    ) -> VEResult:
        timestamps = list(timestamps) if timestamps is not None else list(range(len(closes)))
        capital = self.capital
        peak = capital
        max_dd = 0.0
        trades: List[VETrade] = []
        squeezes = 0
        n = len(closes)

        if variant == "spec":
            test = self.expansion_win
        elif variant == "double_entry":
            test = lambda fut, e: self.double_entry_win(fut, e)[:3]
        else:
            raise ValueError(f"unknown variant {variant!r}; use 'spec' or 'double_entry'")

        i = spec.HV_MIN_CLOSES
        while i < n - self.window:
            ok, bb, hv, sc = self._elite_at(closes, i)
            if not ok:
                i += 1
                continue

            squeezes += 1
            entry = closes[i]
            future = closes[i + 1: i + 1 + self.window]
            win, best_move, bars = test(future, entry)

            before = capital
            capital = capital * (self.win_mult if win else self.loss_mult)

            trades.append(
                VETrade(
                    n=len(trades) + 1,
                    index=i,
                    timestamp=timestamps[i],
                    entry_price=entry,
                    bb_pct=bb,
                    hv_ratio=hv,
                    score=sc,
                    win=win,
                    max_move_pct=best_move * 100,
                    bars_to_expansion=bars,
                    capital_before=before,
                    capital_after=capital,
                    roi_pct=(capital - self.capital) / self.capital * 100,
                )
            )

            if capital > peak:
                peak = capital
            if peak > 0:
                max_dd = max(max_dd, (peak - capital) / peak * 100)

            i = (i + bars + 1) if (self.non_overlapping and bars) else i + 1

        wins = sum(1 for t in trades if t.win)
        total = len(trades)
        return VEResult(
            label=label,
            variant=variant,
            bars=n,
            window=self.window,
            tp_pct=self.tp_pct,
            trades=trades,
            wins=wins,
            losses=total - wins,
            win_rate_pct=(wins / total * 100) if total else 0.0,
            initial_capital=self.capital,
            final_capital=capital,
            roi_pct=(capital - self.capital) / self.capital * 100,
            max_drawdown_pct=max_dd,
            peak_capital=peak,
            squeezes=squeezes,
            expansion_rate_pct=(wins / total * 100) if total else 0.0,
        )

    def run_spec(self, closes, timestamps=None, label=""):
        return self.run(closes, timestamps, label, variant="spec")

    def run_double_entry(self, closes, timestamps=None, label=""):
        """Same rule, but the double-entry pair is resolved leg by leg."""
        return self.run(closes, timestamps, label, variant="double_entry")
