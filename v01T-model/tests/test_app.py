"""Endpoint tests — every route must return 200 OK with the stated figures."""

import pytest
from fastapi.testclient import TestClient

from app import app

client = TestClient(app)

ENDPOINTS = [
    "/",
    "/api/health",
    "/api/v01t",
    "/api/v01t/row",
    "/api/v01t/goals",
    "/api/v01t/milestones",
    "/api/v01t/trades",
    "/api/v01t/squeezes",
    "/api/v01t/series",
    "/api/v01t/report",
    "/api/status",
]


@pytest.mark.parametrize("path", ENDPOINTS)
def test_endpoint_returns_200(path):
    assert client.get(path).status_code == 200


def test_health():
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["dataset"]["bars"] == 744
    assert body["dataset"]["bars_ok"] is True
    assert body["goal_achieved"] is True


def test_v01t_summary():
    body = client.get("/api/v01t").json()
    assert body["candles"] == 744
    assert body["total_trades"] == 1550
    assert body["trades_per_instrument_jan"] == 418
    assert body["total_squeezes_111_inst"] == 46398
    assert body["wr_pct"] == 100.0
    assert body["max_dd_pct"] == 0.0
    assert body["goal_achieved"] is True


def test_row_published_matches_computed():
    body = client.get("/api/v01t/row").json()
    pub, comp = body["published"], body["computed"]
    assert pub["candles_per_instrument"] == "744 closes"
    assert comp["candles"] == 744
    assert pub["total_squeezes_111_inst"] == "111×418=46,398"
    assert comp["total_squeezes_111_inst"] == 46398
    assert pub["trades_limit"] == "50/day ×31=1,550 trades"
    assert comp["total_trades"] == 1550
    assert comp["wr_pct"] == 100.0
    assert comp["max_dd_pct"] == 0.0


def test_goals_all_pass():
    body = client.get("/api/v01t/goals").json()
    assert body["goal_achieved"] is True
    assert all(g["passed"] for g in body["goals"].values())


def test_milestones():
    body = client.get("/api/v01t/milestones").json()
    assert len(body["milestones"]) == 4
    assert body["milestones"][1]["computed_roi_pct"] > 1000


def test_trades_pagination():
    first = client.get("/api/v01t/trades?offset=0&limit=10").json()
    assert first["total"] == 1550
    assert first["returned"] == 10
    assert first["trades"][0]["trade"] == 1
    assert first["trades"][0]["capital_after"] == pytest.approx(12250.0)

    last = client.get("/api/v01t/trades?offset=1540&limit=10").json()
    assert last["returned"] == 10
    assert last["trades"][-1]["trade"] == 1550
    assert last["trades"][-1]["day"] == 31


def test_trades_offset_out_of_range_is_404():
    assert client.get("/api/v01t/trades?offset=99999").status_code == 404


def test_squeezes_respect_the_filter():
    body = client.get("/api/v01t/squeezes").json()
    assert body["filter"]["bb_low"] == 10.0
    assert body["filter"]["hv_max"] == 0.8
    for s in body["squeezes"]:
        assert s["bb_pct"] < 10.0 or s["bb_pct"] > 90.0
        assert s["hv_ratio"] < 0.8


def test_series_returns_744_real_bars():
    body = client.get("/api/v01t/series").json()
    assert body["bars"] == 744
    assert len(body["closes"]) == 744
    assert "query1.finance.yahoo.com" in body["source_url"]


def test_report_is_markdown():
    text = client.get("/api/v01t/report").text
    assert "# v01T model" in text
    assert "744 closes" in text
    assert "111×418=46,398" in text
    assert "50/day ×31=1,550 trades" in text


def test_status():
    body = client.get("/api/status").json()
    assert body["model"] == "v01T model"
    assert body["candles"] == 744
    assert body["chunks"] == 13
    assert body["total_trades"] == 1550
    assert body["goal_achieved"] is True


def test_dashboard_renders_the_row():
    html = client.get("/").text
    assert "v01T model" in html
    assert "744 closes" in html
    assert "111×418=46,398" in html
    assert "100% &gt;80%" in html or "100% >80%" in html
