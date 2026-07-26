"""
bybit_executor.py — automatic v01T execution on Bybit.

Wires the backtested signal to real orders. Each elite squeeze places the
DOUBLE ENTRY: a long leg and a short leg at the same price, each with its own
stop and target attached server-side.

    LONG  leg: side Buy,  positionIdx 1, SL entry*(1-0.0005), TP entry*(1+0.005)
    SHORT leg: side Sell, positionIdx 2, SL entry*(1+0.0005), TP entry*(1-0.005)

Three modes, safest first:

    paper    no exchange contact at all; fills simulated locally   (DEFAULT)
    dry_run  real keys, real market data, orders logged NOT sent
    live     orders actually placed  (requires V01T_LIVE=I_UNDERSTAND)

Risk rails apply in every mode: max concurrent squeezes, max daily loss,
per-order notional cap, and a kill switch.
"""

from __future__ import annotations

import math
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import spec
from .bybit import (BybitClient, BybitError, POSITION_IDX_LONG,
                    POSITION_IDX_SHORT)
from .indicators import compute_bb_percentile, compute_hv_ratio, is_elite, score_for

MODE_PAPER = "paper"
MODE_DRY_RUN = "dry_run"
MODE_LIVE = "live"

LIVE_CONFIRMATION = "I_UNDERSTAND"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RiskLimits:
    """Hard rails. Breaching any of these halts trading."""

    max_concurrent_squeezes: int = 3
    max_daily_loss_pct: float = 20.0
    max_notional_per_leg: float = 100_000.0
    min_free_balance: float = 10.0
    kill_switch: bool = False

    def check(self, state: "ExecutorState") -> Optional[str]:
        if self.kill_switch:
            return "kill switch engaged"
        if len(state.open_squeezes) >= self.max_concurrent_squeezes:
            return (f"max concurrent squeezes reached "
                    f"({len(state.open_squeezes)}/{self.max_concurrent_squeezes})")
        if state.daily_loss_pct >= self.max_daily_loss_pct:
            return (f"daily loss limit hit "
                    f"({state.daily_loss_pct:.2f}% >= {self.max_daily_loss_pct}%)")
        if state.equity < self.min_free_balance:
            return f"balance below minimum ({state.equity:.2f})"
        return None


@dataclass
class SqueezeOrder:
    """One double entry: the two legs placed for a single squeeze."""

    id: str
    symbol: str
    entry_price: float
    qty_per_leg: float
    long_stop: float
    long_target: float
    short_stop: float
    short_target: float
    bb_pct: float
    hv_ratio: float
    score: int
    mode: str
    opened_at: str
    long_result: Dict[str, Any] = field(default_factory=dict)
    short_result: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class ExecutorState:
    mode: str = MODE_PAPER
    running: bool = False
    started_at: Optional[str] = None
    cycles: int = 0
    signals_seen: int = 0
    squeezes_executed: int = 0
    legs_placed: int = 0
    rejected: int = 0
    last_rejection: Optional[str] = None
    errors: int = 0
    last_error: Optional[str] = None
    equity: float = spec.INITIAL_CAPITAL
    starting_equity: float = spec.INITIAL_CAPITAL
    open_squeezes: Dict[str, SqueezeOrder] = field(default_factory=dict)
    history: List[SqueezeOrder] = field(default_factory=list)

    @property
    def daily_loss_pct(self) -> float:
        if self.starting_equity <= 0:
            return 0.0
        drop = self.starting_equity - self.equity
        return max(0.0, drop / self.starting_equity * 100)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "running": self.running,
            "started_at": self.started_at,
            "cycles": self.cycles,
            "signals_seen": self.signals_seen,
            "squeezes_executed": self.squeezes_executed,
            "legs_placed": self.legs_placed,
            "rejected": self.rejected,
            "last_rejection": self.last_rejection,
            "errors": self.errors,
            "last_error": self.last_error,
            "equity": round(self.equity, 2),
            "daily_loss_pct": round(self.daily_loss_pct, 2),
            "open_squeezes": len(self.open_squeezes),
            "completed": len(self.history),
        }


class BybitExecutor:
    """Automatic v01T execution against Bybit."""

    def __init__(
        self,
        client: Optional[BybitClient] = None,
        symbol: str = "BTCUSDT",
        mode: str = MODE_PAPER,
        leverage: int = spec.LEVERAGE,
        equity: float = spec.INITIAL_CAPITAL,
        margin_pct: float = 1.0,
        limits: Optional[RiskLimits] = None,
        qty_step: float = 0.001,
        min_qty: float = 0.001,
    ) -> None:
        if mode not in (MODE_PAPER, MODE_DRY_RUN, MODE_LIVE):
            raise ValueError(f"unknown mode {mode!r}")
        if mode == MODE_LIVE and os.environ.get("V01T_LIVE") != LIVE_CONFIRMATION:
            raise PermissionError(
                "live mode refused: set V01T_LIVE=I_UNDERSTAND to place real orders"
            )
        if mode in (MODE_DRY_RUN, MODE_LIVE) and client is None:
            raise ValueError(f"{mode} mode requires a BybitClient")

        self.client = client
        self.symbol = symbol
        self.mode = mode
        self.leverage = leverage
        self.margin_pct = margin_pct
        self.limits = limits or RiskLimits()
        self.qty_step = qty_step
        self.min_qty = min_qty
        self.state = ExecutorState(mode=mode, equity=equity, starting_equity=equity)

    # ------------------------------------------------------------------ sizing ---

    def leg_qty(self, price: float) -> float:
        """Notional = equity x leverage, split across the two legs."""
        if price <= 0:
            return 0.0
        total_notional = self.state.equity * self.leverage * self.margin_pct
        leg_notional = min(total_notional / 2.0, self.limits.max_notional_per_leg)
        qty = leg_notional / price
        if self.qty_step > 0:
            qty = math.floor(qty / self.qty_step) * self.qty_step
            qty = round(qty, 8)
        return qty if qty >= self.min_qty else 0.0

    def levels(self, entry: float) -> Dict[str, float]:
        return {
            "long_stop": entry * (1 - spec.STOP_PCT),
            "long_target": entry * (1 + spec.TP_PCT),
            "short_stop": entry * (1 + spec.STOP_PCT),
            "short_target": entry * (1 - spec.TP_PCT),
        }

    # ------------------------------------------------------------------ signal ---

    def evaluate(self, closes) -> Dict[str, Any]:
        bb = compute_bb_percentile(closes)
        hv = compute_hv_ratio(closes)
        sc = score_for(bb)
        return {"bb_pct": bb, "hv_ratio": hv, "score": sc,
                "elite": is_elite(bb, hv, sc), "price": closes[-1]}

    # ------------------------------------------------------------- double entry ---

    def execute_squeeze(self, signal: Dict[str, Any]) -> Optional[SqueezeOrder]:
        """Place BOTH legs for one squeeze. Returns None if blocked."""
        blocked = self.limits.check(self.state)
        if blocked:
            self.state.rejected += 1
            self.state.last_rejection = blocked
            return None

        entry = signal["price"]
        qty = self.leg_qty(entry)
        if qty <= 0:
            self.state.rejected += 1
            self.state.last_rejection = "size below minimum order quantity"
            return None

        lv = self.levels(entry)
        sq = SqueezeOrder(
            id=uuid.uuid4().hex[:12], symbol=self.symbol, entry_price=entry,
            qty_per_leg=qty, bb_pct=signal["bb_pct"], hv_ratio=signal["hv_ratio"],
            score=signal["score"], mode=self.mode, opened_at=_now(), **lv,
        )

        long_req = {"symbol": self.symbol, "side": "Buy", "qty": qty,
                    "take_profit": lv["long_target"], "stop_loss": lv["long_stop"],
                    "position_idx": POSITION_IDX_LONG,
                    "order_link_id": f"v01t-{sq.id}-L"}
        short_req = {"symbol": self.symbol, "side": "Sell", "qty": qty,
                     "take_profit": lv["short_target"], "stop_loss": lv["short_stop"],
                     "position_idx": POSITION_IDX_SHORT,
                     "order_link_id": f"v01t-{sq.id}-S"}

        if self.mode == MODE_PAPER:
            sq.long_result = {"simulated": True, **long_req}
            sq.short_result = {"simulated": True, **short_req}
        elif self.mode == MODE_DRY_RUN:
            sq.long_result = {"dry_run": True, "would_send": long_req}
            sq.short_result = {"dry_run": True, "would_send": short_req}
        else:
            try:
                sq.long_result = self.client.place_leg(**long_req)
                sq.short_result = self.client.place_leg(**short_req)
            except BybitError as exc:
                # One leg may already be open — flatten so we are never one-sided.
                self.state.errors += 1
                self.state.last_error = str(exc)
                self._emergency_flatten(qty)
                return None

        self.state.squeezes_executed += 1
        self.state.legs_placed += 2
        self.state.open_squeezes[sq.id] = sq
        self.state.history.append(sq)
        return sq

    def _emergency_flatten(self, qty: float) -> None:
        """Never hold a single naked leg: close both sides, ignore failures."""
        if self.mode != MODE_LIVE or self.client is None:
            return
        for idx in (POSITION_IDX_LONG, POSITION_IDX_SHORT):
            try:
                self.client.close_leg(self.symbol, idx, qty)
            except BybitError:
                pass

    # -------------------------------------------------------------------- cycle ---

    def cycle(self, closes=None) -> Dict[str, Any]:
        """One pass: refresh data, evaluate, execute if elite."""
        self.state.cycles += 1
        try:
            if closes is None:
                if self.client is None:
                    raise BybitError("no client and no closes supplied")
                closes = self.client.closes(self.symbol, limit=200)
            if len(closes) < spec.HV_MIN_CLOSES:
                return {"cycle": self.state.cycles, "skipped": "insufficient history"}

            sig = self.evaluate(closes)
            if not sig["elite"]:
                return {"cycle": self.state.cycles, "elite": False, **sig}

            self.state.signals_seen += 1
            sq = self.execute_squeeze(sig)
            return {"cycle": self.state.cycles, "elite": True, **sig,
                    "executed": sq.as_dict() if sq else None,
                    "blocked": None if sq else self.state.last_rejection}
        except Exception as exc:
            self.state.errors += 1
            self.state.last_error = f"{type(exc).__name__}: {exc}"
            return {"cycle": self.state.cycles, "error": self.state.last_error}

    # ---------------------------------------------------------------- preflight ---

    def preflight(self) -> Dict[str, Any]:
        if self.mode == MODE_PAPER:
            return {"mode": MODE_PAPER, "ready": True,
                    "note": "paper mode: no exchange contact, nothing to verify"}
        report = self.client.preflight(self.symbol, self.leverage)
        report["mode"] = self.mode
        hedge = report["checks"].get("hedge_mode", {})
        if not hedge.get("ok"):
            report["fatal"] = (
                "HEDGE MODE REQUIRED — v01T opens a long and a short leg on the "
                "same symbol. On a one-way account they net to zero exposure and "
                "the model cannot run."
            )
        return report
