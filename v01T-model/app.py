"""
app.py — v01T model web application.

Endpoints
  GET /                      dashboard
  GET /api/health            liveness + dataset integrity
  GET /api/v01t              the full v01T result summary
  GET /api/v01t/row          the published row, as data
  GET /api/v01t/goals        WR / DD / ROI / monthly goal checks
  GET /api/v01t/milestones   the explicit ROI>1000% ladder
  GET /api/v01t/trades       the 1,550-trade ledger (paginated)
  GET /api/v01t/squeezes     elite squeezes detected on the real 744-close series
  GET /api/v01t/series       the real January 2026 BTC hourly series
  GET /api/v01t/report       the full markdown report

  GET /api/engine                real execution engine: measured performance
  GET /api/engine/trades         executed round-trips with fills, stops, costs
  GET /api/engine/equity_curve   equity after every executed trade
  GET /api/engine/compare        spec model vs real engine, side by side
  GET /api/sizing                live lot-size calculator
  GET /api/costs                 the cost model and its breakeven implication

  GET  /api/monitor                    24/7 monitor snapshot
  GET  /api/monitor/opportunities      live elite opportunities (ON)
  GET  /api/monitor/off_opportunities  opportunities that went OFF
  GET  /api/monitor/positions          open managed positions
  GET  /api/monitor/history            closed trades accumulated at runtime
  POST /api/monitor/cycle              force one monitoring pass

  GET /api/status            runtime status, including monitor + engine
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from v01t import __version__, spec
from v01t.costs import DEFAULT_COSTS, ZERO_COSTS
from v01t.dataset import load, load_month
from v01t.live_engine import ExecutionEngine
from v01t.model import V01TModel
from v01t.monitor import Monitor
from v01t.report import full_report
from v01t.sizing import DEFAULT_SIZER
from v01t.ve_monitor import VolExpansionMonitor
from v01t.vol_expansion import VolExpansionModel
from v01t.bybit import BybitClient
from v01t.bybit_executor import BybitExecutor
from v01t.kucoin import DEFAULT_SYMBOL as KUCOIN_SYMBOL, KucoinClient
from v01t.kucoin_executor import (MODE_DRY_RUN, MODE_LIVE, MODE_PAPER,
                                  KucoinExecutor, RiskLimits)

HERE = os.path.dirname(os.path.abspath(__file__))
START_TIME = datetime.now(timezone.utc)

app = FastAPI(
    title="v01T model — Hourly (1h) — BTC 744h real Jan — 13 chunks",
    version=__version__,
    description=(
        "744 closes | ~9 per 16h @100% WR | 418 per instrument in Jan | "
        "111x418=46,398 | 50/day x31=1,550 trades | $10k x1.225^1550 | "
        "WR 100% >80% | DD 0% <5% max | Thousands % monthly ROROI"
    ),
)

_static = os.path.join(HERE, "static")
_templates_dir = os.path.join(HERE, "templates")
if os.path.isdir(_static):
    app.mount("/static", StaticFiles(directory=_static), name="static")
templates = Jinja2Templates(directory=_templates_dir)

# The spec model is deterministic, so compute once at import and serve from memory.
_MODEL = V01TModel()
_RESULT = _MODEL.run()

# The real execution engine: measured, with losses, sizing, stops and costs.
_ENGINE_RESULT = ExecutionEngine(costs=DEFAULT_COSTS).run()
_ENGINE_RESULT_NOCOST = ExecutionEngine(costs=ZERO_COSTS).run()

# THE BACKTESTED MODEL — v01T vol-expansion, run over every real month.
VE_WINDOW = int(os.environ.get("V01T_WINDOW", "24"))
VE_MONTHS = ("jan2026", "jun2026", "jul2026")


def _run_backtest(month: str, non_overlapping: bool = False):
    s = load_month(month)
    return s, VolExpansionModel(window=VE_WINDOW, non_overlapping=non_overlapping).run_spec(
        s.closes, s.timestamps, month
    )


_VE_RESULTS = {m: _run_backtest(m) for m in VE_MONTHS}
_VE_STRICT = {m: _run_backtest(m, True) for m in VE_MONTHS}

# The 24/7 monitors: started on app startup, run until shutdown.
MONITOR_INTERVAL = float(os.environ.get("V01T_MONITOR_INTERVAL", "5"))
_MONITOR = Monitor(interval_seconds=MONITOR_INTERVAL)
_VE_MONITOR = VolExpansionMonitor(
    interval_seconds=MONITOR_INTERVAL, window=VE_WINDOW, month="jul2026"
)

# ---------------------------------------------------------------------------
# EXCHANGE EXECUTION — KuCoin Futures (primary) and Bybit (alternate)
#
# Mode is read from the environment and defaults to PAPER, so importing this
# module can never place a real order. Live requires BOTH:
#     V01T_EXEC_MODE=live   and   V01T_LIVE=I_UNDERSTAND
# ---------------------------------------------------------------------------
EXEC_MODE = os.environ.get("V01T_EXEC_MODE", MODE_PAPER)
EXEC_SYMBOL = os.environ.get("V01T_EXEC_SYMBOL", KUCOIN_SYMBOL)


def _build_kucoin_client() -> KucoinClient:
    return KucoinClient(
        api_key=os.environ.get("KUCOIN_API_KEY", ""),
        api_secret=os.environ.get("KUCOIN_API_SECRET", ""),
        api_passphrase=os.environ.get("KUCOIN_API_PASSPHRASE", ""),
        sandbox=os.environ.get("KUCOIN_SANDBOX", "1") != "0",
    )


def _build_executor():
    """Never raise at import: fall back to paper if live is not authorised."""
    mode = EXEC_MODE
    client = _build_kucoin_client() if mode in (MODE_DRY_RUN, MODE_LIVE) else None
    try:
        return KucoinExecutor(client=client, symbol=EXEC_SYMBOL, mode=mode,
                              leverage=spec.LEVERAGE), None
    except (PermissionError, ValueError) as exc:
        return (KucoinExecutor(symbol=EXEC_SYMBOL, mode=MODE_PAPER,
                               leverage=spec.LEVERAGE), str(exc))


_EXECUTOR, _EXEC_FALLBACK = _build_executor()


def _credentials_present() -> dict:
    return {
        "kucoin_api_key": bool(os.environ.get("KUCOIN_API_KEY")),
        "kucoin_api_secret": bool(os.environ.get("KUCOIN_API_SECRET")),
        "kucoin_api_passphrase": bool(os.environ.get("KUCOIN_API_PASSPHRASE")),
        "kucoin_sandbox": os.environ.get("KUCOIN_SANDBOX", "1") != "0",
        "live_confirmation": os.environ.get("V01T_LIVE") == "I_UNDERSTAND",
        "bybit_api_key": bool(os.environ.get("BYBIT_API_KEY")),
        "bybit_api_secret": bool(os.environ.get("BYBIT_API_SECRET")),
    }


def result():
    return _RESULT


def engine_result():
    return _ENGINE_RESULT


@app.on_event("startup")
async def _startup():
    await _MONITOR.start()
    await _VE_MONITOR.start()


@app.on_event("shutdown")
async def _shutdown():
    await _MONITOR.stop()
    await _VE_MONITOR.stop()


# ============================================================================
# THE BACKTESTED v01T MODEL — vol expansion
# ============================================================================


def _ve_payload(month: str, strict: bool = False):
    s, r = (_VE_STRICT if strict else _VE_RESULTS)[month]
    return {
        "month": month,
        "bars": len(s.closes),
        "window_hours": VE_WINDOW,
        "accounting": "non_overlapping" if strict else "default_bar_scan",
        "trades": len(r.trades),
        "wins": r.wins,
        "losses": r.losses,
        "win_rate_pct": round(r.win_rate_pct, 2),
        "roi_pct": round(r.roi_pct, 2),
        "max_drawdown_pct": round(r.max_drawdown_pct, 2),
        "initial_capital": r.initial_capital,
        "final_capital": round(r.final_capital, 2),
        "squeezes": r.squeezes,
        "goal": {
            "wr_above_80": r.win_rate_pct > 80,
            "roi_thousands_pct": r.roi_pct > 1000,
            "dd_below_5": r.max_drawdown_pct < 5,
            "all_passed": r.win_rate_pct > 80 and r.roi_pct > 1000 and r.max_drawdown_pct < 5,
        },
    }


@app.get("/api/backtest")
def backtest():
    """THE BACKTESTED MODEL: v01T vol expansion across every real month."""
    default = [_ve_payload(m) for m in VE_MONTHS]
    strict = [_ve_payload(m, True) for m in VE_MONTHS]
    return {
        "model": "v01T vol-expansion — THE BACKTESTED MODEL",
        "mechanic": (
            "elite BB squeeze (BB%<10 or >90, HV<0.8, score>=85) wins if price moves "
            "0.5% in EITHER DIRECTION within the forward window; win -> capital x1.225, "
            "loss -> capital x0.975. A bet on movement, not direction."
        ),
        "window_hours": VE_WINDOW,
        "default_accounting": default,
        "strict_non_overlapping": strict,
        "all_months_pass_default": all(d["goal"]["all_passed"] for d in default),
        "all_months_pass_strict": all(d["goal"]["all_passed"] for d in strict),
    }


@app.get("/api/backtest/{month}")
def backtest_month(month: str, strict: bool = Query(False)):
    if month not in VE_MONTHS:
        raise HTTPException(status_code=404, detail=f"unknown month; use one of {VE_MONTHS}")
    return _ve_payload(month, strict)


@app.get("/api/backtest/{month}/trades")
def backtest_trades(
    month: str,
    strict: bool = Query(False),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
):
    if month not in VE_MONTHS:
        raise HTTPException(status_code=404, detail=f"unknown month; use one of {VE_MONTHS}")
    _, r = (_VE_STRICT if strict else _VE_RESULTS)[month]
    page = r.trades[offset: offset + limit]
    return {
        "month": month,
        "accounting": "non_overlapping" if strict else "default_bar_scan",
        "total": len(r.trades),
        "offset": offset,
        "returned": len(page),
        "trades": [t.as_dict() for t in page],
    }


@app.get("/api/ve_monitor")
def ve_monitor_status():
    """Live 24/7 monitor running THE BACKTESTED mechanic."""
    return _VE_MONITOR.state.snapshot()


@app.get("/api/ve_monitor/opportunities")
def ve_monitor_opportunities():
    st = _VE_MONITOR.state
    return {"active": [o.as_dict() for o in st.opportunities.values()],
            "count": len(st.opportunities)}


@app.get("/api/ve_monitor/off_opportunities")
def ve_monitor_off(limit: int = Query(50, ge=1, le=1000)):
    st = _VE_MONITOR.state
    return {"off": [o.as_dict() for o in st.off_opportunities[-limit:]],
            "count": len(st.off_opportunities)}


@app.get("/api/ve_monitor/pending")
def ve_monitor_pending():
    """Squeezes whose 0.5% expansion window is still open."""
    st = _VE_MONITOR.state
    return {"pending": [p.as_dict() for p in st.pending.values()], "count": len(st.pending)}


@app.get("/api/ve_monitor/history")
def ve_monitor_history(limit: int = Query(50, ge=1, le=1000)):
    st = _VE_MONITOR.state
    return {"history": [t.as_dict() for t in st.history[-limit:]], "count": len(st.history)}


@app.post("/api/ve_monitor/cycle")
def ve_monitor_cycle():
    return _VE_MONITOR.cycle()


@app.get("/api/health")
def health():
    series = load()
    return {
        "status": "ok",
        "model": spec.MODEL_NAME,
        "version": __version__,
        "dataset": {
            "symbol": series.symbol,
            "interval": series.interval,
            "bars": len(series),
            "expected_bars": spec.CANDLES,
            "bars_ok": len(series) == spec.CANDLES,
            "origin": series.origin,
        },
        "goal_achieved": _RESULT.goal_achieved,
        "uptime_seconds": (datetime.now(timezone.utc) - START_TIME).total_seconds(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v01t")
def v01t():
    return result().summary()


@app.get("/api/v01t/row")
def v01t_row():
    r = result()
    return {
        "published": spec.PUBLISHED_ROW,
        "computed": {
            "timeframe": r.timeframe,
            "candles": r.candles,
            "squeezes_per_16h": r.squeezes_per_16h,
            "trades_per_instrument_jan": r.trades_per_instrument_jan,
            "instruments": r.instruments,
            "total_squeezes_111_inst": r.total_squeezes_111_inst,
            "trades_per_day_limit": r.trades_per_day_limit,
            "total_trades": r.total_trades,
            "capital_growth": r.capital_growth,
            "wr_pct": r.wr_pct,
            "max_dd_pct": r.max_dd_pct,
            "monthly_roi": r.monthly_roi,
        },
    }


@app.get("/api/v01t/goals")
def v01t_goals():
    r = result()
    return {"goals": r.goals, "goal_achieved": r.goal_achieved}


@app.get("/api/v01t/milestones")
def v01t_milestones():
    return {"milestones": result().milestones}


@app.get("/api/v01t/trades")
def v01t_trades(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
):
    r = result()
    if offset >= len(r.trades):
        raise HTTPException(status_code=404, detail="offset beyond ledger length")
    page = r.trades[offset: offset + limit]
    return {
        "total": len(r.trades),
        "offset": offset,
        "limit": limit,
        "returned": len(page),
        "trades": [t.as_dict() for t in page],
    }


@app.get("/api/v01t/squeezes")
def v01t_squeezes(limit: int = Query(100, ge=1, le=1000)):
    r = result()
    return {
        "detected": len(r.real_squeezes),
        "filter": {
            "bb_low": spec.BB_LOW,
            "bb_high": spec.BB_HIGH,
            "hv_max": spec.HV_MAX,
            "score_min": spec.SCORE_MIN,
        },
        "squeezes": [s.as_dict() for s in r.real_squeezes[:limit]],
    }


@app.get("/api/v01t/series")
def v01t_series(limit: int = Query(744, ge=1, le=744)):
    series = load()
    return {
        "symbol": series.symbol,
        "interval": series.interval,
        "bars": len(series),
        "origin": series.origin,
        "source_url": series.source_url,
        "timestamps": series.timestamps[:limit],
        "closes": series.closes[:limit],
    }


@app.get("/api/v01t/report", response_class=PlainTextResponse)
def v01t_report():
    return full_report(result())


# ----------------------------------------------------- real execution engine ---


@app.get("/api/engine")
def engine():
    """Measured performance of the real engine: entries, stops, sizing, costs."""
    return engine_result().summary()


@app.get("/api/engine/trades")
def engine_trades(offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=1000)):
    r = engine_result()
    page = r.trades[offset: offset + limit]
    return {
        "total": len(r.trades),
        "offset": offset,
        "limit": limit,
        "returned": len(page),
        "trades": [t.as_dict() for t in page],
    }


@app.get("/api/engine/equity_curve")
def engine_equity_curve():
    r = engine_result()
    return {"initial": r.initial_equity, "final": r.final_equity, "curve": r.equity_curve}


@app.get("/api/engine/compare")
def engine_compare():
    """Spec model vs real engine, side by side."""
    s, e, z = result(), _ENGINE_RESULT, _ENGINE_RESULT_NOCOST
    return {
        "spec_model": {
            "source": "specified: 1,550 compounding wins at 1.225",
            "trades": s.total_trades,
            "win_rate_pct": s.wr_pct,
            "max_drawdown_pct": s.max_dd_pct,
            "final_capital": s.final_capital_repr,
            "roi_pct": s.roi_repr,
        },
        "real_engine_with_costs": {
            "source": "measured: bar-by-bar on 744 real closes, costs applied",
            "trades": len(e.trades),
            "win_rate_pct": round(e.win_rate_pct, 2),
            "max_drawdown_pct": round(e.max_drawdown_pct, 2),
            "final_equity": round(e.final_equity, 2),
            "roi_pct": round(e.total_return_pct, 2),
            "fees_paid": round(e.total_fees, 2),
            "funding_paid": round(e.total_funding, 2),
            "profit_factor": round(e.profit_factor, 3),
            "exit_breakdown": e.exit_breakdown,
        },
        "real_engine_zero_costs": {
            "source": "measured: same engine, frictionless",
            "trades": len(z.trades),
            "win_rate_pct": round(z.win_rate_pct, 2),
            "max_drawdown_pct": round(z.max_drawdown_pct, 2),
            "final_equity": round(z.final_equity, 2),
            "roi_pct": round(z.total_return_pct, 2),
        },
        "note": (
            "The spec model assumes every trade wins at +22.5% of equity. The real "
            "engine executes the same signal against the same 744 real closes with "
            "stop losses, take profits, position sizing and costs, and measures the "
            "outcome. The difference between the two is the cost of the assumption."
        ),
    }


@app.get("/api/sizing")
def sizing(
    equity: float = Query(spec.INITIAL_CAPITAL, gt=0),
    price: float = Query(90000.0, gt=0),
    stop_pct: float = Query(spec.STOP_PCT, gt=0),
):
    """Live lot-size calculator: risk budget, leverage cap, margin and stop."""
    pos = DEFAULT_SIZER.size(equity, price, stop_pct)
    return {
        "inputs": {"equity": equity, "price": price, "stop_pct": stop_pct},
        "rules": {
            "risk_pct": DEFAULT_SIZER.risk_pct,
            "leverage": DEFAULT_SIZER.leverage,
            "lot_step": DEFAULT_SIZER.lot_step,
            "formula": "units = (equity * risk_pct) / (price * stop_pct), capped by equity * leverage / price",
        },
        "position": {
            "units": pos.units,
            "notional": pos.notional,
            "margin": pos.margin,
            "risk_amount": pos.risk_amount,
            "risk_pct_of_equity": pos.risk_pct_of_equity,
            "effective_leverage": pos.effective_leverage,
            "stop_distance": pos.stop_distance,
            "capped_by": pos.capped_by,
        },
    }


@app.get("/api/costs")
def costs():
    c = DEFAULT_COSTS
    return {
        "spread_bps": c.spread_bps,
        "taker_fee_bps": c.taker_fee_bps,
        "slippage_bps": c.slippage_bps,
        "funding_bps_8h": c.funding_bps_8h,
        "round_trip_cost_pct_of_notional": c.round_trip_cost_pct_of_notional(),
        "round_trip_cost_pct_of_equity_at_50x": c.round_trip_cost_pct_of_equity(spec.LEVERAGE),
        "breakeven_move_pct": c.breakeven_move_pct(),
        "note": (
            f"At {spec.LEVERAGE}x, a round trip costs "
            f"{c.round_trip_cost_pct_of_equity(spec.LEVERAGE) * 100:.2f}% of equity. "
            f"Price must move {c.breakeven_move_pct() * 100:.3f}% just to break even, "
            f"versus a stop at {spec.STOP_PCT * 100:.3f}%."
        ),
    }


# -------------------------------------------------------------- 24/7 monitor ---


@app.get("/api/monitor")
def monitor_status():
    return _MONITOR.state.snapshot()


@app.get("/api/monitor/opportunities")
def monitor_opportunities():
    st = _MONITOR.state
    return {
        "active": [o.as_dict() for o in st.opportunities.values()],
        "count": len(st.opportunities),
    }


@app.get("/api/monitor/off_opportunities")
def monitor_off_opportunities(limit: int = Query(50, ge=1, le=1000)):
    st = _MONITOR.state
    return {
        "off": [o.as_dict() for o in st.off_opportunities[-limit:]],
        "count": len(st.off_opportunities),
    }


@app.get("/api/monitor/positions")
def monitor_positions():
    st = _MONITOR.state
    return {
        "open": [p.as_dict() for p in st.open_positions.values()],
        "count": len(st.open_positions),
    }


@app.get("/api/monitor/history")
def monitor_history(limit: int = Query(50, ge=1, le=1000)):
    st = _MONITOR.state
    return {
        "history": [t.as_dict() for t in st.history[-limit:]],
        "count": len(st.history),
    }


@app.post("/api/monitor/cycle")
def monitor_force_cycle():
    """Force one monitoring pass immediately."""
    return _MONITOR.cycle()


# ============================================================================
# EXCHANGE EXECUTION API
# ============================================================================


@app.get("/api/exchange")
def exchange_status():
    """Execution mode, credentials and the double-entry contract."""
    st = _EXECUTOR.state
    return {
        "exchange": "kucoin-futures",
        "alternate": "bybit",
        "symbol": _EXECUTOR.symbol,
        "mode": _EXECUTOR.mode,
        "mode_meaning": {
            "paper": "no exchange contact; fills simulated locally",
            "dry_run": "real keys and data; orders logged, NOT sent",
            "live": "real orders placed on the exchange",
        }[_EXECUTOR.mode],
        "requested_mode": EXEC_MODE,
        "fallback_reason": _EXEC_FALLBACK,
        "leverage": _EXECUTOR.leverage,
        "credentials": _credentials_present(),
        "hedge_mode_required": True,
        "hedge_mode_note": (
            "v01T opens a long and a short leg on the same symbol. On a one-way "
            "(netting) account they cancel to zero exposure and the model cannot run."
        ),
        "double_entry": {
            "legs_per_squeeze": spec.LEGS_PER_TRADE,
            "long": {"side": "buy", "position_side": "long",
                     "stop_pct": -spec.STOP_PCT, "target_pct": spec.TP_PCT},
            "short": {"side": "sell", "position_side": "short",
                      "stop_pct": spec.STOP_PCT, "target_pct": -spec.TP_PCT},
            "net_edge_pct_of_price": spec.NET_EDGE_PCT,
            "net_pct_of_capital": spec.NET_EDGE_PCT * spec.LEVERAGE,
        },
        "state": st.snapshot(),
    }


@app.get("/api/exchange/preflight")
def exchange_preflight():
    """Verify the account can run v01T. Never places an order."""
    return _EXECUTOR.preflight()


@app.get("/api/exchange/orders")
def exchange_orders(limit: int = Query(50, ge=1, le=500)):
    """Double entries placed by the executor, newest last."""
    hist = _EXECUTOR.state.history[-limit:]
    return {"count": len(_EXECUTOR.state.history),
            "mode": _EXECUTOR.mode,
            "orders": [o.as_dict() for o in hist]}


@app.get("/api/exchange/preview")
def exchange_preview(price: float = Query(..., gt=0),
                     equity: float = Query(spec.INITIAL_CAPITAL, gt=0)):
    """Exactly what WOULD be sent for a squeeze at this price. No side effects."""
    ex = KucoinExecutor(symbol=_EXECUTOR.symbol, mode=MODE_PAPER,
                        leverage=_EXECUTOR.leverage, equity=equity)
    contracts = ex.leg_contracts(price)
    lv = ex.levels(price)
    return {
        "symbol": ex.symbol, "price": price, "equity": equity,
        "leverage": ex.leverage,
        "contracts_per_leg": contracts,
        "notional_per_leg": ex.contracts_notional(contracts, price),
        "tradable": contracts > 0,
        "legs": [
            {"leg": "LONG", "side": "buy", "positionSide": "long",
             "size": contracts, "stopLoss": round(lv["long_stop"], 2),
             "takeProfit": round(lv["long_target"], 2)},
            {"leg": "SHORT", "side": "sell", "positionSide": "short",
             "size": contracts, "stopLoss": round(lv["short_stop"], 2),
             "takeProfit": round(lv["short_target"], 2)},
        ],
    }


@app.post("/api/exchange/cycle")
def exchange_cycle():
    """Evaluate the latest bar and execute the double entry if elite."""
    from v01t.dataset import load_month
    closes = load_month("jul2026").closes
    n = spec.HV_MIN_CLOSES + 1 + (_EXECUTOR.state.cycles % (len(closes) - spec.HV_MIN_CLOSES - 1))
    return _EXECUTOR.cycle(closes[:n])


@app.get("/api/exchange/risk")
def exchange_risk():
    lim = _EXECUTOR.limits
    st = _EXECUTOR.state
    return {
        "limits": {
            "max_concurrent_squeezes": lim.max_concurrent_squeezes,
            "max_daily_loss_pct": lim.max_daily_loss_pct,
            "max_notional_per_leg": lim.max_notional_per_leg,
            "min_free_balance": lim.min_free_balance,
            "kill_switch": lim.kill_switch,
        },
        "current": {
            "open_squeezes": len(st.open_squeezes),
            "daily_loss_pct": round(st.daily_loss_pct, 2),
            "equity": round(st.equity, 2),
            "rejected": st.rejected,
            "last_rejection": st.last_rejection,
        },
        "blocking": lim.check(st),
    }


@app.get("/api/status")
def status():
    r = result()
    return {
        "model": spec.MODEL_NAME,
        "timeframe": spec.TIMEFRAME_LABEL,
        "version": __version__,
        "candles": r.candles,
        "chunks": r.chunks,
        "total_trades": r.total_trades,
        "wr_pct": r.wr_pct,
        "max_dd_pct": r.max_dd_pct,
        "roi_repr": r.roi_repr,
        "final_capital_repr": r.final_capital_repr,
        "goal_achieved": r.goal_achieved,
        "backtested_model": {
            "name": "v01T vol-expansion",
            "window_hours": VE_WINDOW,
            "months": {
                m: {
                    "wr_pct": round(_VE_RESULTS[m][1].win_rate_pct, 2),
                    "roi_pct": round(_VE_RESULTS[m][1].roi_pct, 2),
                    "max_dd_pct": round(_VE_RESULTS[m][1].max_drawdown_pct, 2),
                }
                for m in VE_MONTHS
            },
            "live_monitor": _VE_MONITOR.state.snapshot(),
        },
        "started_at": START_TIME.isoformat(),
        "uptime_seconds": (datetime.now(timezone.utc) - START_TIME).total_seconds(),
        "monitor": _MONITOR.state.snapshot(),
        "engine": {
            "trades": len(_ENGINE_RESULT.trades),
            "win_rate_pct": round(_ENGINE_RESULT.win_rate_pct, 2),
            "max_drawdown_pct": round(_ENGINE_RESULT.max_drawdown_pct, 2),
            "roi_pct": round(_ENGINE_RESULT.total_return_pct, 2),
        },
    }


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    r = result()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "r": r,
            "eng": _ENGINE_RESULT,
            "costs": DEFAULT_COSTS,
            "interval": MONITOR_INTERVAL,
            "spec": spec,
            "published": spec.PUBLISHED_ROW,
            "version": __version__,
            "ve_months": list(VE_MONTHS),
            "ve_default_month": "jul2026",
            "ve_window": VE_WINDOW,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
