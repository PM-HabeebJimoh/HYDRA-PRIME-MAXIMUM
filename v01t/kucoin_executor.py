"""
kucoin_executor.py — automatic v01T execution on KuCoin Futures.

Each elite squeeze places the DOUBLE ENTRY: a long leg and a short leg at the
same price, each with its own stop and target attached server-side.

    LONG  leg: side buy,  positionSide long,  SL -0.05%, TP +0.50%
    SHORT leg: side sell, positionSide short, SL +0.05%, TP -0.50%
    net: +0.45% of price x 50 leverage = +22.5% of capital

SIZING DIFFERS FROM MOST EXCHANGES
----------------------------------
KuCoin futures trade in integer CONTRACTS, not coin amounts. For XBTUSDTM one
contract is `multiplier` BTC (0.001 by default), so:

    contracts = floor( notional / price / multiplier )

Sub-contract precision is impossible, so small accounts may round to zero — the
executor refuses rather than silently sending a malformed order.

Three modes, safest first:

    paper    no exchange contact at all; fills simulated locally   (DEFAULT)
    dry_run  real keys, real market data, orders logged NOT sent
    live     orders actually placed  (requires V01T_LIVE=I_UNDERSTAND)
"""

from __future__ import annotations

import math
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import spec
from .indicators import compute_bb_percentile, compute_hv_ratio, is_elite, score_for
from .kucoin import (DEFAULT_SYMBOL, POSITION_LONG, POSITION_SHORT, SIDE_BUY,
                     SIDE_SELL, KucoinClient, KucoinError)

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
    contracts_per_leg: int
    notional_per_leg: float
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
        return max(0.0, (self.starting_equity - self.equity)
                   / self.starting_equity * 100)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "exchange": "kucoin-futures",
            "mode": self.mode,
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


class KucoinExecutor:
    """Automatic v01T execution against KuCoin Futures."""

    def __init__(
        self,
        client: Optional[KucoinClient] = None,
        symbol: str = DEFAULT_SYMBOL,
        mode: str = MODE_PAPER,
        leverage: int = spec.LEVERAGE,
        equity: float = spec.INITIAL_CAPITAL,
        margin_pct: float = 1.0,
        limits: Optional[RiskLimits] = None,
        multiplier: float = 0.001,      # BTC per contract on XBTUSDTM
    ) -> None:
        if mode not in (MODE_PAPER, MODE_DRY_RUN, MODE_LIVE):
            raise ValueError(f"unknown mode {mode!r}")
        if mode == MODE_LIVE and os.environ.get("V01T_LIVE") != LIVE_CONFIRMATION:
            raise PermissionError(
                "live mode refused: set V01T_LIVE=I_UNDERSTAND to place real orders"
            )
        if mode in (MODE_DRY_RUN, MODE_LIVE) and client is None:
            raise ValueError(f"{mode} mode requires a KucoinClient")

        self.client = client
        self.symbol = symbol
        self.mode = mode
        self.leverage = leverage
        self.margin_pct = margin_pct
        self.limits = limits or RiskLimits()
        self.multiplier = multiplier
        self.state = ExecutorState(mode=mode, equity=equity,
                                   starting_equity=equity)

    # ------------------------------------------------------------------ sizing ---

    def leg_contracts(self, price: float) -> int:
        """Contracts per leg. KuCoin futures are integer-sized."""
        if price <= 0 or self.multiplier <= 0:
            return 0
        total_notional = self.state.equity * self.leverage * self.margin_pct
        leg_notional = min(total_notional / 2.0, self.limits.max_notional_per_leg)
        return int(math.floor(leg_notional / price / self.multiplier))

    def contracts_notional(self, contracts: int, price: float) -> float:
        return contracts * self.multiplier * price

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
        contracts = self.leg_contracts(entry)
        if contracts <= 0:
            self.state.rejected += 1
            self.state.last_rejection = (
                "size rounds to zero contracts — equity too small for one "
                f"contract of {self.multiplier} at {entry:,.2f}"
            )
            return None

        lv = self.levels(entry)
        sq = SqueezeOrder(
            id=uuid.uuid4().hex[:12], symbol=self.symbol, entry_price=entry,
            contracts_per_leg=contracts,
            notional_per_leg=self.contracts_notional(contracts, entry),
            bb_pct=signal["bb_pct"], hv_ratio=signal["hv_ratio"],
            score=signal["score"], mode=self.mode, opened_at=_now(), **lv,
        )

        long_req = {"symbol": self.symbol, "side": SIDE_BUY, "size": contracts,
                    "leverage": self.leverage, "take_profit": lv["long_target"],
                    "stop_loss": lv["long_stop"], "position_side": POSITION_LONG,
                    "client_oid": f"v01t{sq.id}L"}
        short_req = {"symbol": self.symbol, "side": SIDE_SELL, "size": contracts,
                     "leverage": self.leverage, "take_profit": lv["short_target"],
                     "stop_loss": lv["short_stop"], "position_side": POSITION_SHORT,
                     "client_oid": f"v01t{sq.id}S"}

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
            except KucoinError as exc:
                # One leg may already be live — flatten so we are never one-sided.
                self.state.errors += 1
                self.state.last_error = str(exc)
                self._emergency_flatten(contracts)
                return None

        self.state.squeezes_executed += 1
        self.state.legs_placed += 2
        self.state.open_squeezes[sq.id] = sq
        self.state.history.append(sq)
        return sq

    def _emergency_flatten(self, contracts: int) -> None:
        """Never hold a single naked leg: close both sides, ignore failures."""
        if self.mode != MODE_LIVE or self.client is None:
            return
        for side in (POSITION_LONG, POSITION_SHORT):
            try:
                self.client.close_leg(self.symbol, side, contracts, self.leverage)
            except KucoinError:
                pass

    # -------------------------------------------------------------------- cycle ---

    def cycle(self, closes=None) -> Dict[str, Any]:
        self.state.cycles += 1
        try:
            if closes is None:
                if self.client is None:
                    raise KucoinError("no client and no closes supplied")
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
            return {"exchange": "kucoin-futures", "mode": MODE_PAPER, "ready": True,
                    "note": "paper mode: no exchange contact, nothing to verify"}
        report = self.client.preflight(self.symbol, self.leverage)
        report["mode"] = self.mode
        if not report["checks"].get("hedge_mode", {}).get("ok"):
            report["fatal"] = (
                "HEDGE MODE REQUIRED — v01T opens a long and a short leg on the "
                "same symbol. In one-way mode they net to zero exposure and the "
                "model cannot run."
            )
        return report
