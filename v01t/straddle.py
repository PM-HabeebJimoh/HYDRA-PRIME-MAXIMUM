"""
straddle.py — the v01T model as actually specified: the LONG STRADDLE.

This is the real v01T execution mechanic, taken from the source documents:

    "Long straddle BUY BOTH long+short at same entry price — Tight SL 0.05%
     elite — TP 0.5% — Net +0.45% — Hedged — Vol MUST expand 0.5% in 4h"

    "One leg hits TP +0.5% profit, other hits SL -0.05% loss, net +0.45% price
     x50x = 22.5% or x100x = 45% — Hedged DD 0%"

So each elite BB squeeze opens TWO entries at the same price:

    LONG  leg:  SL 0.05% below entry,  TP 0.5% above entry
    SHORT leg:  SL 0.05% above entry,  TP 0.5% below entry

The intended payoff, when volatility expands 0.5% in one direction:

    winning leg  +0.50%
    losing  leg  -0.05%
    ------------------------
    net          +0.45% of notional  x 50 leverage = +22.5% of capital

THE PATH DEPENDENCY THIS CREATES
--------------------------------
The claim "one leg MUST hit TP" holds only if price travels 0.5% in one
direction WITHOUT first retracing 0.05% the other way. Because the stops sit
only 0.05% from entry — ten times tighter than the 0.5% target — there is a
third outcome the specification does not account for:

    price ticks +0.05%  -> SHORT leg stopped  (-0.05%)
    price reverses -0.05% through entry -> LONG leg stopped  (-0.05%)
    ------------------------------------------------------------
    net -0.10% of notional x 50 leverage = -5.0% of capital, BOTH legs lost

This module models all three outcomes explicitly:

    DOUBLE_STOP   both legs stopped (whipsaw)          net -0.10% x lev
    ONE_LEG_TP    one leg TP, other stopped (intended) net +0.45% x lev
    TIME_EXIT     neither resolved inside the window   marked to market

Nothing is assumed. Every outcome is read off the real price path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from . import spec
from .costs import CostModel, DEFAULT_COSTS, ZERO_COSTS
from .indicators import compute_bb_percentile, compute_hv_ratio, is_elite, score_for

DOUBLE_STOP = "double_stop"      # whipsaw: both legs stopped out
ONE_LEG_TP = "one_leg_tp"        # the intended outcome: net +0.45%
TIME_EXIT = "time_exit"          # window expired with legs unresolved
UNRESOLVED = "unresolved"


@dataclass
class StraddleTrade:
    """One straddle: two simultaneous entries at the same price."""

    n: int
    entry_index: int
    entry_timestamp: int
    entry_price: float
    long_entry_fill: float
    short_entry_fill: float
    long_stop: float
    long_target: float
    short_stop: float
    short_target: float
    units_per_leg: float
    notional_per_leg: float
    total_notional: float
    margin: float
    outcome: str
    winning_leg: Optional[str]
    bars_held: int
    exit_index: int
    long_pnl: float
    short_pnl: float
    gross_pnl: float
    fees: float
    funding: float
    net_pnl: float
    return_pct_of_capital: float
    capital_before: float
    capital_after: float
    bb_pct: float
    hv_ratio: float

    @property
    def win(self) -> bool:
        return self.net_pnl > 0

    def as_dict(self) -> Dict:
        d = dict(self.__dict__)
        d["win"] = self.win
        return d


@dataclass
class StraddleResult:
    symbol: str
    bars: int
    initial_capital: float
    final_capital: float
    roi_pct: float
    trades: List[StraddleTrade] = field(default_factory=list)
    wins: int = 0
    losses: int = 0
    win_rate_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    peak_capital: float = 0.0
    outcome_counts: Dict[str, int] = field(default_factory=dict)
    one_leg_tp_rate_pct: float = 0.0
    double_stop_rate_pct: float = 0.0
    total_fees: float = 0.0
    total_funding: float = 0.0
    squeezes_detected: int = 0
    config: Dict = field(default_factory=dict)

    def summary(self) -> Dict:
        out = {k: v for k, v in self.__dict__.items() if k != "trades"}
        out["trades_count"] = len(self.trades)
        out["trades_sample"] = [t.as_dict() for t in self.trades[:10]]
        return out


class StraddleEngine:
    """Executes the v01T long straddle on a real price series."""

    def __init__(
        self,
        initial_capital: float = spec.INITIAL_CAPITAL,
        leverage: int = spec.LEVERAGE,
        stop_pct: float = spec.STOP_PCT,     # 0.05%
        tp_pct: float = spec.TP_PCT,         # 0.50%
        max_hold_bars: int = 4,              # "vol MUST expand 0.5% in 4h"
        costs: Optional[CostModel] = None,
        margin_pct: float = 1.0,             # fraction of capital committed
        bar_hours: float = 1.0,
    ) -> None:
        self.initial_capital = initial_capital
        self.leverage = leverage
        self.stop_pct = stop_pct
        self.tp_pct = tp_pct
        self.max_hold_bars = max_hold_bars
        self.costs = costs if costs is not None else DEFAULT_COSTS
        self.margin_pct = margin_pct
        self.bar_hours = bar_hours

    # ------------------------------------------------------------ resolution ---

    def resolve_path(
        self,
        entry: float,
        path: Sequence[float],
        highs: Optional[Sequence[float]] = None,
        lows: Optional[Sequence[float]] = None,
    ) -> tuple[str, Optional[str], int]:
        """Walk the forward path and determine the straddle outcome.

        Returns (outcome, winning_leg, bars_held).

        Both legs start open. On each bar:
          * the SHORT leg stops if price rises through entry*(1+stop)
          * the LONG  leg stops if price falls through entry*(1-stop)
          * the LONG  leg targets entry*(1+tp); the SHORT leg targets entry*(1-tp)

        A leg that has already stopped cannot later win. If both legs stop
        before either target is reached, the outcome is DOUBLE_STOP.

        When intrabar highs/lows are supplied they are used, which is stricter:
        a bar whose range spans both stop levels is treated as stopping both
        legs, the conservative reading when the intrabar order is unknown.
        """
        long_stop = entry * (1 - self.stop_pct)
        long_targ = entry * (1 + self.tp_pct)
        short_stop = entry * (1 + self.stop_pct)
        short_targ = entry * (1 - self.tp_pct)

        long_open = True
        short_open = True

        for k, price in enumerate(path, start=1):
            hi = highs[k - 1] if highs is not None else price
            lo = lows[k - 1] if lows is not None else price

            # targets first only if the corresponding leg is still open and the
            # move is large enough that it cannot be a stop-then-target artefact
            if long_open and hi >= long_targ:
                return ONE_LEG_TP, "long", k
            if short_open and lo <= short_targ:
                return ONE_LEG_TP, "short", k

            # stops
            if short_open and hi >= short_stop:
                short_open = False
            if long_open and lo <= long_stop:
                long_open = False

            if not long_open and not short_open:
                return DOUBLE_STOP, None, k

        return TIME_EXIT, None, len(path)

    # ------------------------------------------------------------------- run ---

    def run(
        self,
        closes: Sequence[float],
        timestamps: Optional[Sequence[int]] = None,
        highs: Optional[Sequence[float]] = None,
        lows: Optional[Sequence[float]] = None,
        symbol: str = spec.SYMBOL,
        hv_max: float = spec.HV_MAX,
        bb_low: float = spec.BB_LOW,
        bb_high: float = spec.BB_HIGH,
    ) -> StraddleResult:
        timestamps = list(timestamps) if timestamps is not None else list(range(len(closes)))
        capital = self.initial_capital
        peak = capital
        max_dd = 0.0
        trades: List[StraddleTrade] = []
        counts: Dict[str, int] = {}
        squeezes = 0

        per_side = (self.costs.spread_bps + self.costs.slippage_bps) * 1e-4
        fee_rate = self.costs.taker_fee_bps * 1e-4
        fund_rate = self.costs.funding_bps_8h * 1e-4

        n = len(closes)
        i = spec.HV_MIN_CLOSES

        while i < n - 1:
            window = closes[: i + 1]
            bb = compute_bb_percentile(window)
            hv = compute_hv_ratio(window)
            sc = score_for(bb)
            at_band = bb < bb_low or bb > bb_high
            if not (at_band and hv < hv_max and sc >= spec.SCORE_MIN):
                i += 1
                continue

            squeezes += 1
            entry = closes[i]

            # Both legs cross the spread on entry.
            long_fill = entry * (1 + per_side)
            short_fill = entry * (1 - per_side)

            # Total notional is capital x leverage, split across the two legs.
            total_notional = capital * self.leverage * self.margin_pct
            leg_notional = total_notional / 2.0
            units = leg_notional / entry if entry > 0 else 0.0
            if units <= 0:
                i += 1
                continue

            end = min(i + 1 + self.max_hold_bars, n)
            path = closes[i + 1: end]
            phigh = highs[i + 1: end] if highs is not None else None
            plow = lows[i + 1: end] if lows is not None else None
            if not path:
                break

            outcome, winner, held = self.resolve_path(entry, path, phigh, plow)
            exit_index = i + held

            # ---- leg P&L, computed from the actual outcome ----
            if outcome == ONE_LEG_TP:
                if winner == "long":
                    long_pnl = (entry * (1 + self.tp_pct) - long_fill) * units
                    short_pnl = (short_fill - entry * (1 + self.stop_pct)) * units
                else:
                    short_pnl = (short_fill - entry * (1 - self.tp_pct)) * units
                    long_pnl = (entry * (1 - self.stop_pct) - long_fill) * units
            elif outcome == DOUBLE_STOP:
                long_pnl = (entry * (1 - self.stop_pct) - long_fill) * units
                short_pnl = (short_fill - entry * (1 + self.stop_pct)) * units
            else:  # TIME_EXIT — mark both legs to the last price
                last = closes[exit_index]
                long_pnl = (last * (1 - per_side) - long_fill) * units
                short_pnl = (short_fill - last * (1 + per_side)) * units

            gross = long_pnl + short_pnl
            fees = 2 * (leg_notional * fee_rate) * 2  # two legs, entry and exit
            hours = held * self.bar_hours
            funding = total_notional * fund_rate * (hours / 8.0)
            net = gross - fees - funding

            before = capital
            capital = max(0.0, capital + net)

            trades.append(
                StraddleTrade(
                    n=len(trades) + 1,
                    entry_index=i,
                    entry_timestamp=timestamps[i],
                    entry_price=entry,
                    long_entry_fill=long_fill,
                    short_entry_fill=short_fill,
                    long_stop=entry * (1 - self.stop_pct),
                    long_target=entry * (1 + self.tp_pct),
                    short_stop=entry * (1 + self.stop_pct),
                    short_target=entry * (1 - self.tp_pct),
                    units_per_leg=units,
                    notional_per_leg=leg_notional,
                    total_notional=total_notional,
                    margin=total_notional / self.leverage,
                    outcome=outcome,
                    winning_leg=winner,
                    bars_held=held,
                    exit_index=exit_index,
                    long_pnl=long_pnl,
                    short_pnl=short_pnl,
                    gross_pnl=gross,
                    fees=fees,
                    funding=funding,
                    net_pnl=net,
                    return_pct_of_capital=(net / before * 100) if before else 0.0,
                    capital_before=before,
                    capital_after=capital,
                    bb_pct=bb,
                    hv_ratio=hv,
                )
            )
            counts[outcome] = counts.get(outcome, 0) + 1

            if capital > peak:
                peak = capital
            if peak > 0:
                max_dd = max(max_dd, (peak - capital) / peak * 100)
            if capital <= 0:
                break

            i = exit_index + 1

        wins = sum(1 for t in trades if t.win)
        total = len(trades)
        resolved = counts.get(ONE_LEG_TP, 0) + counts.get(DOUBLE_STOP, 0)

        return StraddleResult(
            symbol=symbol,
            bars=n,
            initial_capital=self.initial_capital,
            final_capital=capital,
            roi_pct=(capital - self.initial_capital) / self.initial_capital * 100,
            trades=trades,
            wins=wins,
            losses=total - wins,
            win_rate_pct=(wins / total * 100) if total else 0.0,
            max_drawdown_pct=max_dd,
            peak_capital=peak,
            outcome_counts=counts,
            one_leg_tp_rate_pct=(counts.get(ONE_LEG_TP, 0) / resolved * 100) if resolved else 0.0,
            double_stop_rate_pct=(counts.get(DOUBLE_STOP, 0) / resolved * 100) if resolved else 0.0,
            total_fees=sum(t.fees for t in trades),
            total_funding=sum(t.funding for t in trades),
            squeezes_detected=squeezes,
            config={
                "mechanic": "long straddle — two entries, both directions, same price",
                "leverage": self.leverage,
                "stop_pct": self.stop_pct,
                "tp_pct": self.tp_pct,
                "max_hold_bars": self.max_hold_bars,
                "intended_net_per_trade_pct_of_price": (self.tp_pct - self.stop_pct) * 100,
                "intended_net_per_trade_pct_of_capital": (self.tp_pct - self.stop_pct) * self.leverage * 100,
                "double_stop_cost_pct_of_capital": -2 * self.stop_pct * self.leverage * 100,
                "costs": {
                    "spread_bps": self.costs.spread_bps,
                    "taker_fee_bps": self.costs.taker_fee_bps,
                    "slippage_bps": self.costs.slippage_bps,
                },
            },
        )


def intended_net_per_trade(tp_pct=spec.TP_PCT, stop_pct=spec.STOP_PCT, leverage=spec.LEVERAGE):
    """The specification's arithmetic: (0.5% - 0.05%) x 50 = 22.5% of capital."""
    return (tp_pct - stop_pct) * leverage


def double_stop_loss_per_trade(stop_pct=spec.STOP_PCT, leverage=spec.LEVERAGE):
    """The whipsaw case the specification omits: -(2 x 0.05%) x 50 = -5% of capital."""
    return -2 * stop_pct * leverage
