"""
monitor.py — the 24/7 live monitoring loop.

Runs continuously in the background, and on every cycle:

  1. refreshes the price series for each watched instrument
  2. evaluates the elite vol-explosion filter on the latest bar
  3. raises an opportunity ON when an instrument becomes elite
  4. keeps a stable ID while it stays elite, updating it when the data moves
  5. raises OFF when an instrument stops meeting the elite requirement
  6. manages open paper positions: checks stop loss, take profit and time exit
     against every new price, and closes them with full cost accounting

State is held in memory and exposed through the web app, so the dashboard shows
live opportunities, live positions and an accumulating trade history.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from . import spec
from .costs import CostModel, DEFAULT_COSTS
from .dataset import Series, load
from .live_engine import EXIT_STOP, EXIT_TARGET, EXIT_TIME, LONG, SHORT
from .indicators import compute_bb_percentile, compute_hv_ratio, is_elite, score_for
from .sizing import Sizer, DEFAULT_SIZER


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Opportunity:
    """An instrument currently meeting (or recently failing) the elite filter."""

    id: str
    instrument: str
    direction: int
    bb_pct: float
    hv_ratio: float
    score: int
    price: float
    detected_at: str
    updated_at: str
    cycles_active: int = 1
    is_off: bool = False
    off_reason: Optional[str] = None
    off_at: Optional[str] = None

    @property
    def side(self) -> str:
        return "LONG" if self.direction == LONG else "SHORT"

    def as_dict(self) -> Dict:
        d = dict(self.__dict__)
        d["side"] = self.side
        return d


@dataclass
class OpenPosition:
    """A live paper position being managed by the monitor."""

    id: str
    instrument: str
    direction: int
    units: float
    entry_fill: float
    notional: float
    margin: float
    stop_price: float
    target_price: float
    opened_at: str
    opened_ts: float
    bars_held: int = 0
    last_price: float = 0.0
    unrealised_pnl: float = 0.0

    @property
    def side(self) -> str:
        return "LONG" if self.direction == LONG else "SHORT"

    def as_dict(self) -> Dict:
        d = dict(self.__dict__)
        d["side"] = self.side
        return d


@dataclass
class ClosedTrade:
    id: str
    instrument: str
    side: str
    units: float
    entry_fill: float
    exit_fill: float
    exit_reason: str
    hours_held: float
    gross_pnl: float
    fees: float
    funding: float
    net_pnl: float
    equity_after: float
    closed_at: str

    def as_dict(self) -> Dict:
        return dict(self.__dict__)


@dataclass
class MonitorState:
    """Everything the dashboard needs to render live activity."""

    running: bool = False
    started_at: Optional[str] = None
    cycles: int = 0
    last_cycle_at: Optional[str] = None
    last_cycle_duration_ms: float = 0.0
    errors: int = 0
    last_error: Optional[str] = None
    equity: float = spec.INITIAL_CAPITAL
    peak_equity: float = spec.INITIAL_CAPITAL
    max_drawdown_pct: float = 0.0
    opportunities: Dict[str, Opportunity] = field(default_factory=dict)
    off_opportunities: List[Opportunity] = field(default_factory=list)
    open_positions: Dict[str, OpenPosition] = field(default_factory=dict)
    history: List[ClosedTrade] = field(default_factory=list)

    def snapshot(self) -> Dict:
        wins = [t for t in self.history if t.net_pnl > 0]
        return {
            "running": self.running,
            "started_at": self.started_at,
            "cycles": self.cycles,
            "last_cycle_at": self.last_cycle_at,
            "last_cycle_duration_ms": round(self.last_cycle_duration_ms, 2),
            "errors": self.errors,
            "last_error": self.last_error,
            "equity": round(self.equity, 2),
            "peak_equity": round(self.peak_equity, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "open_positions": len(self.open_positions),
            "active_opportunities": len(self.opportunities),
            "off_opportunities": len(self.off_opportunities),
            "closed_trades": len(self.history),
            "wins": len(wins),
            "losses": len(self.history) - len(wins),
            "win_rate_pct": round(len(wins) / len(self.history) * 100, 2) if self.history else 0.0,
            "realised_pnl": round(sum(t.net_pnl for t in self.history), 2),
        }


class Monitor:
    """24/7 background monitor: scans, opens, manages and closes positions."""

    def __init__(
        self,
        instruments: Optional[List[str]] = None,
        interval_seconds: float = 30.0,
        sizer: Optional[Sizer] = None,
        costs: Optional[CostModel] = None,
        stop_pct: float = spec.STOP_PCT,
        tp_pct: float = spec.TP_PCT,
        max_hold_bars: int = 4,
        initial_equity: float = spec.INITIAL_CAPITAL,
        series_provider: Optional[Callable[[str], Series]] = None,
        max_history: int = 5000,
    ) -> None:
        self.instruments = instruments or [spec.SYMBOL]
        self.interval_seconds = interval_seconds
        self.sizer = sizer or DEFAULT_SIZER
        self.costs = costs if costs is not None else DEFAULT_COSTS
        self.stop_pct = stop_pct
        self.tp_pct = tp_pct
        self.max_hold_bars = max_hold_bars
        self.max_history = max_history
        self.state = MonitorState(equity=initial_equity, peak_equity=initial_equity)
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()
        self._cursor: Dict[str, int] = {}
        self._series_provider = series_provider or self._default_series

        # A deterministic replay cursor lets the monitor demonstrate live
        # behaviour against the vendored series when no live feed is reachable.
        self._replay: Dict[str, Series] = {}

    # ------------------------------------------------------------ data access ---

    def _default_series(self, instrument: str) -> Series:
        if instrument not in self._replay:
            self._replay[instrument] = load(live=False)
        return self._replay[instrument]

    def _window_for(self, instrument: str) -> tuple[List[float], int, int]:
        """Return the visible close window, its last index and timestamp.

        Each cycle advances the cursor by one bar, so the monitor sees a growing
        series exactly as it would with a live feed.
        """
        series = self._series_provider(instrument)
        start = spec.HV_MIN_CLOSES + 1
        cursor = self._cursor.get(instrument, start)
        if cursor >= len(series.closes):
            cursor = start  # wrap for continuous operation
        self._cursor[instrument] = cursor + 1
        return series.closes[: cursor + 1], cursor, series.timestamps[cursor]

    # ---------------------------------------------------------------- position ---

    def _levels(self, entry_fill: float, direction: int) -> tuple[float, float]:
        if direction == LONG:
            return entry_fill * (1 - self.stop_pct), entry_fill * (1 + self.tp_pct)
        return entry_fill * (1 + self.stop_pct), entry_fill * (1 - self.tp_pct)

    def _open_position(self, instrument: str, direction: int, price: float) -> Optional[OpenPosition]:
        entry_fill = self.costs.entry_price(price, direction)
        pos = self.sizer.size(self.state.equity, entry_fill, self.stop_pct)
        if not pos.is_open:
            return None
        stop_price, target_price = self._levels(entry_fill, direction)
        op = OpenPosition(
            id=uuid.uuid4().hex[:12],
            instrument=instrument,
            direction=direction,
            units=pos.units,
            entry_fill=entry_fill,
            notional=pos.notional,
            margin=pos.margin,
            stop_price=stop_price,
            target_price=target_price,
            opened_at=_now(),
            opened_ts=time.time(),
            last_price=price,
        )
        self.state.open_positions[op.id] = op
        return op

    def _exit_reason(self, op: OpenPosition, price: float) -> Optional[str]:
        if op.direction == LONG:
            if price <= op.stop_price:
                return EXIT_STOP
            if price >= op.target_price:
                return EXIT_TARGET
        else:
            if price >= op.stop_price:
                return EXIT_STOP
            if price <= op.target_price:
                return EXIT_TARGET
        if op.bars_held >= self.max_hold_bars:
            return EXIT_TIME
        return None

    def _close_position(self, op: OpenPosition, price: float, reason: str) -> ClosedTrade:
        exit_fill = self.costs.exit_price(price, op.direction)
        gross = (exit_fill - op.entry_fill) * op.units * op.direction
        fees = self.costs.round_trip_fee(op.units * op.entry_fill, op.units * exit_fill)
        hours = max(op.bars_held, 1) * 1.0
        funding = self.costs.funding(op.units * op.entry_fill, hours)
        net = gross - fees - funding

        self.state.equity = max(0.0, self.state.equity + net)
        if self.state.equity > self.state.peak_equity:
            self.state.peak_equity = self.state.equity
        if self.state.peak_equity > 0:
            dd = (self.state.peak_equity - self.state.equity) / self.state.peak_equity * 100
            self.state.max_drawdown_pct = max(self.state.max_drawdown_pct, dd)

        trade = ClosedTrade(
            id=op.id,
            instrument=op.instrument,
            side=op.side,
            units=op.units,
            entry_fill=op.entry_fill,
            exit_fill=exit_fill,
            exit_reason=reason,
            hours_held=hours,
            gross_pnl=gross,
            fees=fees,
            funding=funding,
            net_pnl=net,
            equity_after=self.state.equity,
            closed_at=_now(),
        )
        self.state.history.append(trade)
        if len(self.state.history) > self.max_history:
            del self.state.history[: len(self.state.history) - self.max_history]
        self.state.open_positions.pop(op.id, None)
        return trade

    # ------------------------------------------------------------------- cycle ---

    def cycle(self) -> Dict:
        """One full monitoring pass. Safe to call directly in tests."""
        started = time.perf_counter()
        opened, closed, turned_off = [], [], []

        for instrument in self.instruments:
            closes, idx, _ts = self._window_for(instrument)
            if len(closes) <= spec.HV_MIN_CLOSES:
                continue
            price = closes[-1]

            # 1. manage existing positions against the new price
            for op in list(self.state.open_positions.values()):
                if op.instrument != instrument:
                    continue
                op.bars_held += 1
                op.last_price = price
                op.unrealised_pnl = (price - op.entry_fill) * op.units * op.direction
                reason = self._exit_reason(op, price)
                if reason:
                    closed.append(self._close_position(op, price, reason).as_dict())

            # 2. evaluate the elite filter on the latest bar
            bb = compute_bb_percentile(closes)
            hv = compute_hv_ratio(closes)
            sc = score_for(bb)
            elite = is_elite(bb, hv, sc)
            existing = self.state.opportunities.get(instrument)

            if elite:
                direction = LONG if bb < spec.BB_LOW else SHORT
                if existing is None:
                    opp = Opportunity(
                        id=uuid.uuid4().hex[:12],
                        instrument=instrument,
                        direction=direction,
                        bb_pct=bb,
                        hv_ratio=hv,
                        score=sc,
                        price=price,
                        detected_at=_now(),
                        updated_at=_now(),
                    )
                    self.state.opportunities[instrument] = opp

                    has_open = any(
                        p.instrument == instrument for p in self.state.open_positions.values()
                    )
                    if not has_open:
                        pos = self._open_position(instrument, direction, price)
                        if pos:
                            opened.append(pos.as_dict())
                else:
                    # same asset still elite: keep the ID, refresh the data
                    existing.bb_pct = bb
                    existing.hv_ratio = hv
                    existing.score = sc
                    existing.price = price
                    existing.direction = direction
                    existing.updated_at = _now()
                    existing.cycles_active += 1
            elif existing is not None:
                # 3. OFF: was elite, no longer meets the requirement
                existing.is_off = True
                existing.off_at = _now()
                existing.off_reason = (
                    f"BB% {existing.bb_pct} -> {bb}, HV {existing.hv_ratio} -> {hv}, "
                    f"score {existing.score} -> {sc}; elite requirement no longer met"
                )
                self.state.off_opportunities.append(existing)
                if len(self.state.off_opportunities) > self.max_history:
                    del self.state.off_opportunities[0]
                turned_off.append(existing.as_dict())
                del self.state.opportunities[instrument]

        self.state.cycles += 1
        self.state.last_cycle_at = _now()
        self.state.last_cycle_duration_ms = (time.perf_counter() - started) * 1000

        return {
            "cycle": self.state.cycles,
            "opened": opened,
            "closed": closed,
            "off": turned_off,
            "equity": round(self.state.equity, 2),
            "open_positions": len(self.state.open_positions),
            "active_opportunities": len(self.state.opportunities),
        }

    # -------------------------------------------------------------------- loop ---

    async def _loop(self) -> None:
        try:
            while not self._stop.is_set():
                try:
                    self.cycle()
                except Exception as exc:  # keep the loop alive 24/7
                    self.state.errors += 1
                    self.state.last_error = f"{type(exc).__name__}: {exc}"
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=self.interval_seconds)
                except asyncio.TimeoutError:
                    pass
        finally:
            self.state.running = False

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop = asyncio.Event()
        # Mark running before scheduling so callers observe the state
        # immediately, without waiting for the loop's first tick.
        self.state.running = True
        self.state.started_at = _now()
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self._task.cancel()
        self.state.running = False


MONITOR = Monitor()
