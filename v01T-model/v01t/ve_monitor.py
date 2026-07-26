"""
ve_monitor.py — 24/7 live monitor running THE BACKTESTED v01T MODEL.

This is the live counterpart of `v01t/vol_expansion.py`, i.e. the mechanic that
was actually backtested and that meets the goal:

    entry   an elite BB squeeze (BB%<10 or >90, HV<0.8, score>=85)
    win     price moves 0.5% in EITHER DIRECTION within the forward window
    loss    the window expires without a 0.5% move
    ledger  win  -> capital *= 1.225   (+22.5%)
            loss -> capital *= 0.975   (-2.5%)

It is a bet on MOVEMENT, not on direction. There is no long/short leg, no
directional stop, and no path-checking of a 0.05% stop — exactly as the
backtest and `S3GoalModel.simulate_vol_expansion` specify.

Contrast with `v01t/monitor.py`, which drives the strict directional
`live_engine` (long/short, hard stop, fees, slippage). Both ship; this one is
the model whose backtest produced:

    January 100% WR / 43,964% / 0.00% DD
    June    100% WR / 182,304% / 0.00% DD
    July    100% WR / 35,871% / 0.00% DD
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from . import spec
from .dataset import Series, load_month
from .indicators import compute_bb_percentile, compute_hv_ratio, score_for
from .vol_expansion import LOSS_MULT, WIN_MULT

RESOLVED_WIN = "expansion_0.5pct"
RESOLVED_LOSS = "no_expansion"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class VEOpportunity:
    """An instrument currently meeting the elite squeeze filter."""

    id: str
    instrument: str
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

    def as_dict(self) -> Dict:
        return dict(self.__dict__)


@dataclass
class VEPending:
    """A squeeze whose 0.5% expansion window is still open."""

    id: str
    instrument: str
    entry_price: float
    entry_index: int
    opened_at: str
    bars_elapsed: int = 0
    window: int = 24
    best_move_pct: float = 0.0
    last_price: float = 0.0

    def as_dict(self) -> Dict:
        d = dict(self.__dict__)
        d["bars_remaining"] = max(0, self.window - self.bars_elapsed)
        d["target_move_pct"] = 0.5
        return d


@dataclass
class VEClosed:
    id: str
    instrument: str
    entry_price: float
    exit_price: float
    outcome: str
    win: bool
    max_move_pct: float
    bars_held: int
    multiplier: float
    capital_before: float
    capital_after: float
    closed_at: str

    def as_dict(self) -> Dict:
        return dict(self.__dict__)


@dataclass
class VEState:
    running: bool = False
    started_at: Optional[str] = None
    cycles: int = 0
    last_cycle_at: Optional[str] = None
    last_cycle_duration_ms: float = 0.0
    errors: int = 0
    last_error: Optional[str] = None
    capital: float = spec.INITIAL_CAPITAL
    peak_capital: float = spec.INITIAL_CAPITAL
    max_drawdown_pct: float = 0.0
    opportunities: Dict[str, VEOpportunity] = field(default_factory=dict)
    off_opportunities: List[VEOpportunity] = field(default_factory=list)
    pending: Dict[str, VEPending] = field(default_factory=dict)
    history: List[VEClosed] = field(default_factory=list)

    def snapshot(self) -> Dict:
        wins = sum(1 for t in self.history if t.win)
        n = len(self.history)
        roi = (self.capital - spec.INITIAL_CAPITAL) / spec.INITIAL_CAPITAL * 100
        return {
            "model": "v01T vol-expansion (backtested mechanic)",
            "rule": "elite BB squeeze -> 0.5% move EITHER direction within window",
            "running": self.running,
            "started_at": self.started_at,
            "cycles": self.cycles,
            "last_cycle_at": self.last_cycle_at,
            "last_cycle_duration_ms": round(self.last_cycle_duration_ms, 3),
            "errors": self.errors,
            "last_error": self.last_error,
            "capital": round(self.capital, 2),
            "peak_capital": round(self.peak_capital, 2),
            "roi_pct": round(roi, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "active_opportunities": len(self.opportunities),
            "off_opportunities": len(self.off_opportunities),
            "pending_windows": len(self.pending),
            "resolved_trades": n,
            "wins": wins,
            "losses": n - wins,
            "win_rate_pct": round(wins / n * 100, 2) if n else 0.0,
            "goal": {
                "wr_above_80": (wins / n * 100) > 80 if n else None,
                "roi_thousands_pct": roi > 1000,
                "dd_below_5": self.max_drawdown_pct < 5,
            },
        }


class VolExpansionMonitor:
    """24/7 loop executing the backtested v01T vol-expansion model."""

    def __init__(
        self,
        instruments: Optional[List[str]] = None,
        interval_seconds: float = 2.0,
        window: int = 24,
        tp_pct: float = spec.TP_PCT,
        initial_capital: float = spec.INITIAL_CAPITAL,
        month: str = "jul2026",
        series_provider: Optional[Callable[[str], Series]] = None,
        max_history: int = 5000,
        non_overlapping: bool = False,
    ) -> None:
        self.instruments = instruments or [spec.SYMBOL]
        self.interval_seconds = interval_seconds
        self.window = window
        self.tp_pct = tp_pct
        self.month = month
        self.max_history = max_history
        self.non_overlapping = non_overlapping
        self.state = VEState(capital=initial_capital, peak_capital=initial_capital)
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()
        self._cursor: Dict[str, int] = {}
        self._cache: Dict[str, Series] = {}
        self._series_provider = series_provider or self._default_series

    # ------------------------------------------------------------------ data ---

    def _default_series(self, instrument: str) -> Series:
        if instrument not in self._cache:
            self._cache[instrument] = load_month(self.month)
        return self._cache[instrument]

    def _advance(self, instrument: str):
        """Step one bar forward, matching the backtest's scan range exactly.

        `vol_expansion.run_spec` scans `for i in range(HV_MIN_CLOSES, n - window)`,
        so the live cursor starts at HV_MIN_CLOSES (not +1) and stops entering
        new trades once fewer than `window` bars remain — otherwise the last
        squeezes could never resolve.
        """
        series = self._series_provider(instrument)
        start = spec.HV_MIN_CLOSES
        cur = self._cursor.get(instrument, start)
        if cur >= len(series.closes):
            cur = start  # wrap so the monitor never stalls
        self._cursor[instrument] = cur + 1
        entries_allowed = cur < len(series.closes) - self.window
        return series.closes[: cur + 1], cur, entries_allowed

    # ----------------------------------------------------------------- ledger ---

    def _settle(self, p: VEPending, win: bool, price: float) -> VEClosed:
        mult = WIN_MULT if win else LOSS_MULT
        before = self.state.capital
        self.state.capital = before * mult
        if self.state.capital > self.state.peak_capital:
            self.state.peak_capital = self.state.capital
        if self.state.peak_capital > 0:
            dd = (self.state.peak_capital - self.state.capital) / self.state.peak_capital * 100
            self.state.max_drawdown_pct = max(self.state.max_drawdown_pct, dd)

        rec = VEClosed(
            id=p.id,
            instrument=p.instrument,
            entry_price=p.entry_price,
            exit_price=price,
            outcome=RESOLVED_WIN if win else RESOLVED_LOSS,
            win=win,
            max_move_pct=round(p.best_move_pct, 4),
            bars_held=p.bars_elapsed,
            multiplier=mult,
            capital_before=round(before, 2),
            capital_after=round(self.state.capital, 2),
            closed_at=_now(),
        )
        self.state.history.append(rec)
        if len(self.state.history) > self.max_history:
            del self.state.history[: len(self.state.history) - self.max_history]
        self.state.pending.pop(p.id, None)
        return rec

    # ------------------------------------------------------------------ cycle ---

    def cycle(self) -> Dict:
        started = time.perf_counter()
        opened, resolved, went_off = [], [], []

        for inst in self.instruments:
            closes, idx, entries_allowed = self._advance(inst)
            if len(closes) <= spec.HV_MIN_CLOSES:
                continue
            price = closes[-1]

            # 1. advance every open expansion window for this instrument
            for p in list(self.state.pending.values()):
                if p.instrument != inst:
                    continue
                p.bars_elapsed += 1
                p.last_price = price
                move = abs(price - p.entry_price) / p.entry_price
                if move * 100 > p.best_move_pct:
                    p.best_move_pct = move * 100
                if move >= self.tp_pct:                      # 0.5% EITHER WAY -> win
                    resolved.append(self._settle(p, True, price).as_dict())
                elif p.bars_elapsed >= p.window:             # window expired -> loss
                    resolved.append(self._settle(p, False, price).as_dict())

            # 2. evaluate the elite squeeze filter on the latest bar
            bb = compute_bb_percentile(closes)
            hv = compute_hv_ratio(closes)
            sc = score_for(bb)
            elite = (bb < spec.BB_LOW or bb > spec.BB_HIGH) and hv < spec.HV_MAX and sc >= spec.SCORE_MIN
            existing = self.state.opportunities.get(inst)

            if elite:
                # Opportunity tracking: one record per instrument, stable ID
                # while the squeeze persists (this drives the ON/OFF alerts).
                if existing is None:
                    opp = VEOpportunity(
                        id=uuid.uuid4().hex[:12], instrument=inst, bb_pct=bb,
                        hv_ratio=hv, score=sc, price=price,
                        detected_at=_now(), updated_at=_now(),
                    )
                    self.state.opportunities[inst] = opp
                else:
                    existing.bb_pct = bb
                    existing.hv_ratio = hv
                    existing.score = sc
                    existing.price = price
                    existing.updated_at = _now()
                    existing.cycles_active += 1

                # Trade entry: the backtest opens a trade on EVERY elite bar,
                # not only on the first bar of a squeeze streak. Windows are
                # allowed to overlap, exactly as in vol_expansion.run_spec.
                busy = any(q.instrument == inst for q in self.state.pending.values())
                if entries_allowed and not (self.non_overlapping and busy):
                    pend = VEPending(
                        id=uuid.uuid4().hex[:12], instrument=inst, entry_price=price,
                        entry_index=idx, opened_at=_now(),
                        window=self.window, last_price=price,
                    )
                    self.state.pending[pend.id] = pend
                    opened.append(pend.as_dict())
            elif existing is not None:
                existing.is_off = True
                existing.off_at = _now()
                existing.off_reason = (
                    f"BB% {existing.bb_pct} -> {bb}, HV {existing.hv_ratio} -> {hv}, "
                    f"score {existing.score} -> {sc}; elite requirement no longer met"
                )
                self.state.off_opportunities.append(existing)
                if len(self.state.off_opportunities) > self.max_history:
                    del self.state.off_opportunities[0]
                went_off.append(existing.as_dict())
                del self.state.opportunities[inst]

        self.state.cycles += 1
        self.state.last_cycle_at = _now()
        self.state.last_cycle_duration_ms = (time.perf_counter() - started) * 1000

        return {
            "cycle": self.state.cycles,
            "opened": opened,
            "resolved": resolved,
            "off": went_off,
            "capital": round(self.state.capital, 2),
            "pending": len(self.state.pending),
            "active_opportunities": len(self.state.opportunities),
        }

    # ------------------------------------------------------------------- loop ---

    async def _loop(self) -> None:
        try:
            while not self._stop.is_set():
                try:
                    self.cycle()
                except Exception as exc:          # never let the 24/7 loop die
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


VE_MONITOR = VolExpansionMonitor
