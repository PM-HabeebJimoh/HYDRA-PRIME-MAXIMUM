"""
engine.py — the REAL v01T backtest engine.

Unlike `model.py` (which reproduces the published v01T row as specified — a fixed
1,550-trade compounding series with no loss branch), this engine actually trades
the price series bar by bar:

  * scans each bar for an elite squeeze (BB% extreme + HV compression)
  * opens a position at that bar's close, direction inferred from the band side
  * sizes the position from RISK_PCT and the stop distance, capped by leverage
  * walks forward bar by bar and exits on stop loss, take profit, or timeout
  * applies fees and slippage on entry and exit
  * records wins AND losses, tracks equity peak and true max drawdown

Every rule below is taken from the v01T spec constants, so the same parameters
that describe the published row are the ones actually executed here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import spec
from .dataset import Series
from .indicators import compute_bb_percentile, compute_hv_ratio, is_elite, score_for

# ------------------------------------------------------------------- costs ---

DEFAULT_FEE_PCT = 0.0004      # 4 bps taker fee, charged on entry and on exit
DEFAULT_SLIPPAGE_PCT = 0.0002  # 2 bps adverse slippage per fill
DEFAULT_MAX_HOLD_BARS = 4      # 4h forward window on the hourly timeframe


@dataclass
class BacktestTrade:
    """One real round-trip trade."""

    n: int
    direction: str            # "long" or "short"
    entry_index: int
    entry_timestamp: int
    entry_price: float
    exit_index: int
    exit_timestamp: int
    exit_price: float
    bars_held: int
    bb_pct: float
    hv_ratio: float
    score: int
    notional: float
    qty: float
    gross_pnl: float
    fees: float
    net_pnl: float
    return_pct: float         # net P&L as a % of equity before the trade
    equity_before: float
    equity_after: float
    outcome: str              # "take_profit" | "stop_loss" | "timeout"
    win: bool

    def as_dict(self) -> Dict:
        return dict(self.__dict__)


@dataclass
class BacktestResult:
    """Aggregate statistics for a real backtest run."""

    label: str
    symbol: str
    interval: str
    bars: int
    period_start_utc: str
    period_end_utc: str
    initial_capital: float
    final_capital: float
    roi_pct: float
    squeezes_detected: int
    trades: int
    wins: int
    losses: int
    win_rate_pct: float
    max_drawdown_pct: float
    peak_equity: float
    total_fees: float
    gross_pnl: float
    net_pnl: float
    avg_win: float
    avg_loss: float
    profit_factor: Optional[float]
    expectancy: float
    largest_win: float
    largest_loss: float
    max_consecutive_losses: int
    outcomes: Dict[str, int]
    buy_and_hold_pct: float
    goals: Dict[str, Dict]
    goal_achieved: bool
    parameters: Dict
    trade_list: List[BacktestTrade] = field(default_factory=list)

    def summary(self) -> Dict:
        out = {k: v for k, v in self.__dict__.items() if k != "trade_list"}
        out["trades_sample"] = [t.as_dict() for t in self.trade_list[:20]]
        return out


class V01TBacktestEngine:
    """Real bar-by-bar backtester for the v01T elite vol-explosion strategy."""

    def __init__(
        self,
        capital: float = spec.INITIAL_CAPITAL,
        leverage: int = spec.LEVERAGE,
        risk_pct: float = spec.RISK_PCT,
        stop_pct: float = spec.STOP_PCT,
        tp_pct: float = spec.TP_PCT,
        fee_pct: float = DEFAULT_FEE_PCT,
        slippage_pct: float = DEFAULT_SLIPPAGE_PCT,
        max_hold_bars: int = DEFAULT_MAX_HOLD_BARS,
        max_trades_per_day: int = spec.TRADES_PER_DAY_LIMIT,
    ) -> None:
        self.initial_capital = capital
        self.leverage = leverage
        self.risk_pct = risk_pct
        self.stop_pct = stop_pct
        self.tp_pct = tp_pct
        self.fee_pct = fee_pct
        self.slippage_pct = slippage_pct
        self.max_hold_bars = max_hold_bars
        self.max_trades_per_day = max_trades_per_day

    # ------------------------------------------------------------- sizing ---

    def position_size(self, equity: float, entry_price: float) -> tuple[float, float]:
        """Return (quantity, notional).

        Risk-based sizing: risk `risk_pct` of equity over the stop distance,
        then cap the notional at `leverage` x equity.
        """
        risk_capital = equity * self.risk_pct
        stop_distance = entry_price * self.stop_pct
        if stop_distance <= 0:
            return 0.0, 0.0
        qty = risk_capital / stop_distance
        notional = qty * entry_price
        max_notional = equity * self.leverage
        if notional > max_notional:
            notional = max_notional
            qty = notional / entry_price
        return qty, notional

    # -------------------------------------------------------------- exits ---

    def _resolve_exit(
        self, closes: List[float], entry_index: int, entry_price: float, direction: str
    ) -> tuple[int, float, str]:
        """Walk forward and return (exit_index, exit_price, outcome)."""
        if direction == "long":
            tp_price = entry_price * (1 + self.tp_pct)
            sl_price = entry_price * (1 - self.stop_pct)
        else:
            tp_price = entry_price * (1 - self.tp_pct)
            sl_price = entry_price * (1 + self.stop_pct)

        last = min(entry_index + self.max_hold_bars, len(closes) - 1)
        for j in range(entry_index + 1, last + 1):
            price = closes[j]
            if direction == "long":
                # Stop is far tighter than the target, so on an ambiguous bar the
                # conservative assumption is that the stop trades first.
                if price <= sl_price:
                    return j, sl_price, "stop_loss"
                if price >= tp_price:
                    return j, tp_price, "take_profit"
            else:
                if price >= sl_price:
                    return j, sl_price, "stop_loss"
                if price <= tp_price:
                    return j, tp_price, "take_profit"
        return last, closes[last], "timeout"

    # ----------------------------------------------------------------- run ---

    def run(self, series: Series, label: str = "") -> BacktestResult:
        closes = list(series.closes)
        timestamps = list(series.timestamps)
        n = len(closes)

        equity = self.initial_capital
        peak = equity
        max_dd = 0.0
        trades: List[BacktestTrade] = []
        squeezes = 0
        total_fees = 0.0
        gross_total = 0.0
        trades_by_day: Dict[int, int] = {}

        i = spec.HV_MIN_CLOSES
        while i < n - 1:
            window = closes[: i + 1]
            bb = compute_bb_percentile(window)
            hv = compute_hv_ratio(window)
            sc = score_for(bb)

            if not is_elite(bb, hv, sc):
                i += 1
                continue

            squeezes += 1

            day = timestamps[i] // 86400
            if trades_by_day.get(day, 0) >= self.max_trades_per_day:
                i += 1
                continue

            # A squeeze at the lower band is expected to expand upward, and one
            # at the upper band downward (mean reversion out of compression).
            direction = "long" if bb < spec.BB_LOW else "short"

            raw_entry = closes[i]
            # Slippage always works against the fill.
            entry_price = (
                raw_entry * (1 + self.slippage_pct)
                if direction == "long"
                else raw_entry * (1 - self.slippage_pct)
            )

            qty, notional = self.position_size(equity, entry_price)
            if qty <= 0 or notional <= 0:
                i += 1
                continue

            exit_index, raw_exit, outcome = self._resolve_exit(
                closes, i, entry_price, direction
            )
            exit_price = (
                raw_exit * (1 - self.slippage_pct)
                if direction == "long"
                else raw_exit * (1 + self.slippage_pct)
            )

            if direction == "long":
                gross = (exit_price - entry_price) * qty
            else:
                gross = (entry_price - exit_price) * qty

            fees = (notional + qty * exit_price) * self.fee_pct
            net = gross - fees

            equity_before = equity
            equity = max(0.0, equity + net)
            total_fees += fees
            gross_total += gross

            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100 if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

            trades_by_day[day] = trades_by_day.get(day, 0) + 1
            trades.append(
                BacktestTrade(
                    n=len(trades) + 1,
                    direction=direction,
                    entry_index=i,
                    entry_timestamp=timestamps[i],
                    entry_price=entry_price,
                    exit_index=exit_index,
                    exit_timestamp=timestamps[exit_index],
                    exit_price=exit_price,
                    bars_held=exit_index - i,
                    bb_pct=bb,
                    hv_ratio=hv,
                    score=sc,
                    notional=notional,
                    qty=qty,
                    gross_pnl=gross,
                    fees=fees,
                    net_pnl=net,
                    return_pct=(net / equity_before * 100) if equity_before > 0 else 0.0,
                    equity_before=equity_before,
                    equity_after=equity,
                    outcome=outcome,
                    win=net > 0,
                )
            )

            if equity <= 0:
                break

            # No pyramiding: resume scanning after the position closes.
            i = exit_index + 1

        return self._summarise(series, label, equity, peak, max_dd, trades,
                               squeezes, total_fees, gross_total, closes)

    # ---------------------------------------------------------- statistics ---

    def _summarise(self, series, label, equity, peak, max_dd, trades,
                   squeezes, total_fees, gross_total, closes) -> BacktestResult:
        from datetime import datetime, timezone

        wins = [t for t in trades if t.win]
        losses = [t for t in trades if not t.win]
        win_pnls = [t.net_pnl for t in wins]
        loss_pnls = [t.net_pnl for t in losses]

        gross_win = sum(win_pnls)
        gross_loss = abs(sum(loss_pnls))
        profit_factor = (gross_win / gross_loss) if gross_loss > 0 else None

        streak = best_streak = 0
        for t in trades:
            if not t.win:
                streak += 1
                best_streak = max(best_streak, streak)
            else:
                streak = 0

        outcomes: Dict[str, int] = {}
        for t in trades:
            outcomes[t.outcome] = outcomes.get(t.outcome, 0) + 1

        wr = (len(wins) / len(trades) * 100) if trades else 0.0
        roi = (equity - self.initial_capital) / self.initial_capital * 100
        net_total = equity - self.initial_capital
        bh = (closes[-1] - closes[0]) / closes[0] * 100

        goals = {
            "win_rate": {
                "value_pct": round(wr, 2),
                "target": f">{spec.TARGET_WR_PCT:.0f}%",
                "passed": wr > spec.TARGET_WR_PCT,
            },
            "max_drawdown": {
                "value_pct": round(max_dd, 2),
                "target": f"<{spec.TARGET_MAX_DD_PCT:.0f}%",
                "passed": max_dd < spec.TARGET_MAX_DD_PCT,
            },
            "roi": {
                "value_pct": round(roi, 2),
                "target": f">{spec.TARGET_ROI_PCT:.0f}%",
                "passed": roi > spec.TARGET_ROI_PCT,
            },
        }

        return BacktestResult(
            label=label or "v01T real backtest",
            symbol=series.symbol,
            interval=series.interval,
            bars=len(closes),
            period_start_utc=datetime.fromtimestamp(
                series.timestamps[0], timezone.utc).isoformat(),
            period_end_utc=datetime.fromtimestamp(
                series.timestamps[-1], timezone.utc).isoformat(),
            initial_capital=self.initial_capital,
            final_capital=round(equity, 2),
            roi_pct=round(roi, 2),
            squeezes_detected=squeezes,
            trades=len(trades),
            wins=len(wins),
            losses=len(losses),
            win_rate_pct=round(wr, 2),
            max_drawdown_pct=round(max_dd, 2),
            peak_equity=round(peak, 2),
            total_fees=round(total_fees, 2),
            gross_pnl=round(gross_total, 2),
            net_pnl=round(net_total, 2),
            avg_win=round(sum(win_pnls) / len(win_pnls), 2) if win_pnls else 0.0,
            avg_loss=round(sum(loss_pnls) / len(loss_pnls), 2) if loss_pnls else 0.0,
            profit_factor=round(profit_factor, 3) if profit_factor else None,
            expectancy=round(net_total / len(trades), 2) if trades else 0.0,
            largest_win=round(max(win_pnls), 2) if win_pnls else 0.0,
            largest_loss=round(min(loss_pnls), 2) if loss_pnls else 0.0,
            max_consecutive_losses=best_streak,
            outcomes=outcomes,
            buy_and_hold_pct=round(bh, 2),
            goals=goals,
            goal_achieved=all(g["passed"] for g in goals.values()),
            parameters={
                "initial_capital": self.initial_capital,
                "leverage": self.leverage,
                "risk_pct": self.risk_pct,
                "stop_pct": self.stop_pct,
                "tp_pct": self.tp_pct,
                "fee_pct": self.fee_pct,
                "slippage_pct": self.slippage_pct,
                "max_hold_bars": self.max_hold_bars,
                "max_trades_per_day": self.max_trades_per_day,
                "bb_low": spec.BB_LOW,
                "bb_high": spec.BB_HIGH,
                "hv_max": spec.HV_MAX,
                "score_min": spec.SCORE_MIN,
            },
            trade_list=trades,
        )
