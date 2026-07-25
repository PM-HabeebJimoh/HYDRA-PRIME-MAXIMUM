"""The live app must serve THE BACKTESTED model (vol expansion), not a variant."""

import pytest
from fastapi.testclient import TestClient

from app import app
from v01t.dataset import load_month
from v01t.vol_expansion import VolExpansionModel

client = TestClient(app)
MONTHS = ["jan2026", "jun2026", "jul2026"]


# ------------------------------------------------------------- wiring ---

def test_backtest_endpoint_exists():
    assert client.get("/api/backtest").status_code == 200


def test_app_serves_the_vol_expansion_mechanic():
    body = client.get("/api/backtest").json()
    assert "vol-expansion" in body["model"]
    assert "EITHER DIRECTION" in body["mechanic"]
    assert body["window_hours"] == 24


@pytest.mark.parametrize("month", MONTHS)
def test_backtest_month_endpoint(month):
    assert client.get(f"/api/backtest/{month}").status_code == 200


def test_unknown_month_is_404():
    assert client.get("/api/backtest/nope").status_code == 404


# ------------------------------------------------ served == recomputed ---

@pytest.mark.parametrize("month", MONTHS)
def test_served_numbers_match_a_fresh_backtest(month):
    """The API must not drift from what the model actually computes."""
    s = load_month(month)
    r = VolExpansionModel(window=24).run_spec(s.closes, s.timestamps)
    body = client.get(f"/api/backtest/{month}").json()
    assert body["trades"] == len(r.trades)
    assert body["win_rate_pct"] == pytest.approx(round(r.win_rate_pct, 2))
    assert body["roi_pct"] == pytest.approx(round(r.roi_pct, 2))
    assert body["max_drawdown_pct"] == pytest.approx(round(r.max_drawdown_pct, 2))


# --------------------------------------------------------------- goal ---

@pytest.mark.parametrize("month", MONTHS)
def test_every_month_passes_the_goal_by_default(month):
    g = client.get(f"/api/backtest/{month}").json()["goal"]
    assert g["wr_above_80"] and g["roi_thousands_pct"] and g["dd_below_5"]
    assert g["all_passed"]


@pytest.mark.parametrize("month", MONTHS)
def test_every_month_passes_the_goal_strict(month):
    g = client.get(f"/api/backtest/{month}?strict=true").json()["goal"]
    assert g["all_passed"], f"{month} failed under non-overlapping accounting"


def test_summary_flags_all_months_pass():
    body = client.get("/api/backtest").json()
    assert body["all_months_pass_default"] is True
    assert body["all_months_pass_strict"] is True


def test_trades_endpoint_returns_the_ledger():
    body = client.get("/api/backtest/jul2026/trades?limit=5").json()
    assert body["total"] == 29
    for t in body["trades"]:
        assert "win" in t and "max_move_pct" in t


# ------------------------------------------------------- live monitor ---

def test_ve_monitor_runs_the_backtested_mechanic():
    with TestClient(app) as c:
        snap = c.get("/api/ve_monitor").json()
        assert snap["running"] is True
        assert "EITHER direction" in snap["rule"]


@pytest.mark.parametrize("path", [
    "/api/ve_monitor",
    "/api/ve_monitor/opportunities",
    "/api/ve_monitor/off_opportunities",
    "/api/ve_monitor/pending",
    "/api/ve_monitor/history",
])
def test_ve_monitor_endpoints(path):
    assert client.get(path).status_code == 200


def test_ve_monitor_accumulates_and_uses_spec_multipliers():
    for _ in range(200):
        client.post("/api/ve_monitor/cycle")
    snap = client.get("/api/ve_monitor").json()
    assert snap["cycles"] >= 200
    hist = client.get("/api/ve_monitor/history?limit=1000").json()["history"]
    assert hist, "monitor should have resolved expansion windows"
    for t in hist:
        assert t["multiplier"] in (1.225, 0.975)
        assert t["outcome"] in ("expansion_0.5pct", "no_expansion")
        assert t["win"] is (t["multiplier"] == 1.225)


def test_ve_monitor_is_direction_agnostic():
    """No long/short anywhere: it is a bet on movement."""
    for _ in range(120):
        client.post("/api/ve_monitor/cycle")
    hist = client.get("/api/ve_monitor/history?limit=1000").json()["history"]
    for t in hist:
        assert "side" not in t and "direction" not in t


def test_status_exposes_the_backtested_model():
    b = client.get("/api/status").json()["backtested_model"]
    assert b["name"] == "v01T vol-expansion"
    for m in MONTHS:
        assert b["months"][m]["wr_pct"] > 80
