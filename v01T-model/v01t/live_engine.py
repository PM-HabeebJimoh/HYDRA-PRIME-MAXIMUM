"""
live_engine.py — the real-time v01T execution engine.

Complements engine.py (the January/June bar-walk backtester) by providing the
execution core shared with the 24/7 monitor: sizing, costs and exit management
as reusable components.

Unlike the spec ledger in model.py (which compounds a fixed +22.5% win outcome
1,550 times), this engine walks the price series bar by bar and actually trades:

  entry  an elite squeeze (BB% extreme + HV compression + score) opens a position
         in the direction of the expected band reversion
  size   lot size from the risk budget and stop distance, capped by leverage
  stop   exit if price trades through entry -/+ STOP_PCT
  target exit if price trades through entry +/- TP_PCT
  time   exit after a maximum holding period if neither is hit
  costs  spread, slippage, taker fees per side and funding while held

Losses are possible, so win rate and drawdown are measured outcomes rather
than assumptions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from . import spec
from .costs import CostModel, DEFAULT_COSTS
from .dataset import Series, load
from .indicators import compute_bb_percentile, compute_hv_ratio, is_elite, score_for
from .sizing import Position, Sizer, DEFAULT_SIZER

LONG = 1
SHORT = -1

EXIT_STOP = "stop_loss"
EXIT_TARGET = "take_profit"
EXIT_TIME = "time_exit"
EXIT_EOD = "end_of_data"


@dataclass
class ExecutedTrade:
    """One round-trip trade actually executed by the engine."""

    n: int
    direction: int
    entry_index: int
    entry_timestamp: int
    entry_mid: float
    entry_fill: float
    exit_index: int
    exit_timestamp: int
    exit_mid: float
    exit_fill: float
    exit_reason: str
    bars_held: int
    hours_held: float
    units: float
    notional: float
    margin: float
    stop_price: float
    target_price: float
    bb_pct: float
    hv_ratio: float
    score: int
    gross_pnl: float
    fees: float
    funding: float
    net_pnl: float
    return_pct_of_equity: float
    equity_before: float
    equity_after: float

    @property
    def win(self) -> bool:
        return self.net_pnl > 0

    def as_dict(self) -> Dict:
        d = dict(self.__dict__)
        d["win"] = self.win
        d["side"] = "LONG" if self.direction == LONG else "SHORT"
        return d


@dataclass
class EngineResult:
    """Measured performance of a real execution run."""

    symbol: str
    interval: str
    bars: int
    data_origin: str
    initial_equity: float
    final_equity: float
    total_return_pct: float
    trades: List[ExecutedTrade] = field(default_factory=list)
    wins: int = 0
    losses: int = 0
    win_rate_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    peak_equity: float = 0.0
    gross_pnl: float = 0.0
    total_fees: float = 0.0
    total_funding: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    exit_breakdown: Dict[str, int] = field(default_factory=dict)
    signals_detected: int = 0
    signals_taken: int = 0
    equity_curve: List[float] = field(default_factory=list)
    config: Dict = field(default_factory=dict)

    def summary(self) -> Dict:
        out = {k: v for k, v in self.__dict__.items() if k not in ("trades", "equity_curve")}
        out["trades_count"] = len(self.trades)
        out["trades_sample"] = [t.as_dict() for t in self.trades[:10]]
        return out


class ExecutionEngine:
    """Bar-by-bar executor for the v01T elite vol-explosion signal."""

    def __init__(
        self,
        initial_equity: float = spec.INITIAL_CAPITAL,
        sizer: Optional[Sizer] = None,
        costs: Optional[CostModel] = None,
        stop_pct: float = spec.STOP_PCT,
        tp_pct: float = spec.TP_PCT,
        max_hold_bars: int = 4,
        bar_hours: float = 1.0,
        allow_concurrent: bool = False,
    ) -> None:
        self.initial_equity = initial_equity
        self.sizer = sizer or DEFAULT_SIZER
        self.costs = costs if costs is not None else DEFAULT_COSTS
        self.stop_pct = stop_pct
        self.tp_pct = tp_pct
        self.max_hold_bars = max_hold_bars
        self.bar_hours = bar_hours
        self.allow_concurrent = allow_concurrent

    # ------------------------------------------------------------- direction ---

    @staticmethod
    def direction_for(bb_pct: float) -> int:
        """Band-reversion: squeezed at the low band -> long, at the high band -> short."""
        return LONG if bb_pct < spec.BB_LOW else SHORT

    # ------------------------------------------------------------------ exits ---

    def _levels(self, entry_fill: float, direction: int) -> tuple[float, float]:
        if direction == LONG:
            return entry_fill * (1 - self.stop_pct), entry_fill * (1 + self.tp_pct)
        return entry_fill * (1 + self.stop_pct), entry_fill * (1 - self.tp_pct)

    def _check_exit(
        self, price: float, direction: int, stop_price: float, target_price: float
    ) -> Optional[str]:
        """Stop is checked before target: the conservative assumption when a
        single bar's close could have touched both."""
        if direction == LONG:
            if price <= stop_price:
                return EXIT_STOP
            if price >= target_price:
                return EXIT_TARGET
        else:
            if price >= stop_price:
                return EXIT_STOP
            if price <= target_price:
                return EXIT_TARGET
        return None

    # -------------------------------------------------------------------- run ---

    def run(self, series: Optional[Series] = None, live: bool = False) -> EngineResult:
        if series is None:
            series = load(live=live)

        closes = series.closes
        timestamps = series.timestamps

        equity = self.initial_equity
        peak = equity
        max_dd = 0.0
        trades: List[ExecutedTrade] = []
        equity_curve: List[float] = [equity]
        exit_breakdown: Dict[str, int] = {}
        signals_detected = 0
        signals_taken = 0

        i = spec.HV_MIN_CLOSES
        n = len(closes)

        while i < n - 1:
            window = closes[: i + 1]
            bb = compute_bb_percentile(window)
            hv = compute_hv_ratio(window)
            sc = score_for(bb)

            if not is_elite(bb, hv, sc):
                i += 1
                continue

            signals_detected += 1

            direction = self.direction_for(bb)
            entry_mid = closes[i]
            entry_fill = self.costs.entry_price(entry_mid, direction)
            pos: Position = self.sizer.size(equity, entry_fill, self.stop_pct)

            if not pos.is_open:
                i += 1
                continue

            signals_taken += 1
            stop_price, target_price = self._levels(entry_fill, direction)

            # walk forward bar by bar looking for stop / target / time exit
            exit_reason = EXIT_EOD
            exit_index = min(i + self.max_hold_bars, n - 1)
            for j in range(i + 1, min(i + 1 + self.max_hold_bars, n)):
                reason = self._check_exit(closes[j], direction, stop_price, target_price)
                if reason:
                    exit_reason, exit_index = reason, j
                    break
                if j == i + self.max_hold_bars:
                    exit_reason, exit_index = EXIT_TIME, j

            exit_mid = closes[exit_index]
            exit_fill = self.costs.exit_price(exit_mid, direction)

            bars_held = exit_index - i
            hours_held = bars_held * self.bar_hours

            gross = (exit_fill - entry_fill) * pos.units * direction
            entry_notional = pos.units * entry_fill
            exit_notional = pos.units * exit_fill
            fees = self.costs.round_trip_fee(entry_notional, exit_notional)
            funding = self.costs.funding(entry_notional, hours_held)
            net = gross - fees - funding

            equity_before = equity
            equity = max(0.0, equity + net)

            trades.append(
                ExecutedTrade(
                    n=len(trades) + 1,
                    direction=direction,
                    entry_index=i,
                    entry_timestamp=timestamps[i],
                    entry_mid=entry_mid,
                    entry_fill=entry_fill,
                    exit_index=exit_index,
                    exit_timestamp=timestamps[exit_index],
                    exit_mid=exit_mid,
                    exit_fill=exit_fill,
                    exit_reason=exit_reason,
                    bars_held=bars_held,
                    hours_held=hours_held,
                    units=pos.units,
                    notional=pos.notional,
                    margin=pos.margin,
                    stop_price=stop_price,
                    target_price=target_price,
                    bb_pct=bb,
                    hv_ratio=hv,
                    score=sc,
                    gross_pnl=gross,
                    fees=fees,
                    funding=funding,
                    net_pnl=net,
                    return_pct_of_equity=(net / equity_before * 100) if equity_before else 0.0,
                    equity_before=equity_before,
                    equity_after=equity,
                )
            )

            exit_breakdown[exit_reason] = exit_breakdown.get(exit_reason, 0) + 1
            equity_curve.append(equity)

            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100 if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

            if equity <= 0:
                break

            # non-overlapping by default: resume after the exit bar
            i = exit_index + 1 if not self.allow_concurrent else i + 1

        wins = [t for t in trades if t.win]
        losses = [t for t in trades if not t.win]
        gross_win = sum(t.net_pnl for t in wins)
        gross_loss = abs(sum(t.net_pnl for t in losses))

        return EngineResult(
            symbol=series.symbol,
            interval=series.interval,
            bars=n,
            data_origin=series.origin,
            initial_equity=self.initial_equity,
            final_equity=equity,
            total_return_pct=(equity - self.initial_equity) / self.initial_equity * 100,
            trades=trades,
            wins=len(wins),
            losses=len(losses),
            win_rate_pct=(len(wins) / len(trades) * 100) if trades else 0.0,
            max_drawdown_pct=max_dd,
            peak_equity=peak,
            gross_pnl=sum(t.gross_pnl for t in trades),
            total_fees=sum(t.fees for t in trades),
            total_funding=sum(t.funding for t in trades),
            avg_win=(gross_win / len(wins)) if wins else 0.0,
            avg_loss=(-gross_loss / len(losses)) if losses else 0.0,
            profit_factor=(gross_win / gross_loss) if gross_loss > 0 else float("inf") if gross_win > 0 else 0.0,
            expectancy=(sum(t.net_pnl for t in trades) / len(trades)) if trades else 0.0,
            exit_breakdown=exit_breakdown,
            signals_detected=signals_detected,
            signals_taken=signals_taken,
            equity_curve=equity_curve,
            config={
                "initial_equity": self.initial_equity,
                "risk_pct": self.sizer.risk_pct,
                "leverage": self.sizer.leverage,
                "stop_pct": self.stop_pct,
                "tp_pct": self.tp_pct,
                "max_hold_bars": self.max_hold_bars,
                "costs": {
                    "spread_bps": self.costs.spread_bps,
                    "taker_fee_bps": self.costs.taker_fee_bps,
                    "slippage_bps": self.costs.slippage_bps,
                    "funding_bps_8h": self.costs.funding_bps_8h,
                    "round_trip_cost_pct_of_equity": self.costs.round_trip_cost_pct_of_equity(
                        self.sizer.leverage
                    ),
                },
            },
        )


def run_engine(live: bool = False, **kwargs) -> EngineResult:
    return ExecutionEngine(**kwargs).run(live=live)
