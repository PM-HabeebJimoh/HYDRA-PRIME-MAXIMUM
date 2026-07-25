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
  GET /api/status            runtime status
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from v01t import __version__, spec
from v01t.dataset import load
from v01t.model import V01TModel
from v01t.report import full_report

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

# The model is deterministic, so compute once at import and serve from memory.
_MODEL = V01TModel()
_RESULT = _MODEL.run()


def result():
    return _RESULT


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
        "started_at": START_TIME.isoformat(),
        "uptime_seconds": (datetime.now(timezone.utc) - START_TIME).total_seconds(),
    }


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    r = result()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "r": r,
            "spec": spec,
            "published": spec.PUBLISHED_ROW,
            "version": __version__,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
