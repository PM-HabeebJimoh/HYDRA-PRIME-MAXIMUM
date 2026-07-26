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


def test_dashboard_renders_the_published_row():
    """The published row is rendered server-side in the Model Spec view."""
    html = client.get("/").text
    assert "744 closes" in html
    assert "111×418=46,398" in html
    assert "50/day ×31=1,550 trades" in html


def test_dashboard_is_an_enterprise_shell():
    """Multi-view application shell, not a single scrolling page."""
    html = client.get("/").text
    for view in ("overview", "backtest", "trades", "signals",
                 "monitor", "risk", "model", "api"):
        assert 'id="view-%s"' % view in html, view
        assert 'data-view="%s"' % view in html, view


def test_dashboard_declares_double_entry():
    html = client.get("/").text.upper()
    assert "DOUBLE ENTRY" in html
    assert "HEDGE MODE" in html


def test_dashboard_is_accessible():
    """Baseline a11y: landmarks, skip link, labelled controls, live region."""
    html = client.get("/").text
    assert 'lang="en"' in html
    assert 'class="skip-link"' in html
    assert "<main" in html and "<nav" in html and "<header" in html
    assert 'aria-label' in html
    assert 'aria-live="polite"' in html
    assert 'role="tabpanel"' in html
    assert 'scope="col"' in html          # data tables are scoped


def test_dashboard_ships_the_design_system():
    css = client.get("/static/css/app.css").text
    assert client.get("/static/css/app.css").status_code == 200
    assert "--surface" in css and "--text-1" in css      # design tokens
    assert "prefers-reduced-motion" in css               # motion safety
    assert '[data-theme="light"]' in css                 # theme support
    assert "@media (max-width: 1024px)" in css           # responsive
    assert "tabular-nums" in css                         # aligned numerics


def test_dashboard_ships_the_controller():
    js = client.get("/static/js/app.js").text
    assert client.get("/static/js/app.js").status_code == 200
    assert "palette" in js.lower()                       # command palette
    assert "setInterval" in js                           # live polling


# ------------------------------------------- engine / sizing / costs routes ---

NEW_ENDPOINTS = [
    "/api/engine",
    "/api/engine/trades",
    "/api/engine/equity_curve",
    "/api/engine/compare",
    "/api/sizing",
    "/api/costs",
    "/api/monitor",
    "/api/monitor/opportunities",
    "/api/monitor/off_opportunities",
    "/api/monitor/positions",
    "/api/monitor/history",
]


@pytest.mark.parametrize("path", NEW_ENDPOINTS)
def test_new_endpoint_returns_200(path):
    assert client.get(path).status_code == 200


def test_engine_reports_measured_losses():
    body = client.get("/api/engine").json()
    assert body["losses"] > 0
    assert body["win_rate_pct"] < 100.0
    assert body["max_drawdown_pct"] > 0.0
    assert body["total_fees"] > 0


def test_engine_compare_shows_both_sides():
    body = client.get("/api/engine/compare").json()
    assert body["spec_model"]["win_rate_pct"] == 100.0
    assert body["spec_model"]["max_drawdown_pct"] == 0.0
    assert body["real_engine_with_costs"]["win_rate_pct"] < 100.0
    assert body["real_engine_with_costs"]["max_drawdown_pct"] > 0.0
    assert "note" in body


def test_engine_trades_have_stops_targets_and_costs():
    body = client.get("/api/engine/trades?limit=5").json()
    assert body["total"] > 0
    for t in body["trades"]:
        assert t["stop_price"] > 0
        assert t["target_price"] > 0
        assert t["units"] > 0
        assert t["exit_reason"] in {"stop_loss", "take_profit", "time_exit", "end_of_data"}


def test_sizing_endpoint_computes_a_lot_size():
    body = client.get("/api/sizing?equity=10000&price=90000").json()
    pos = body["position"]
    assert pos["units"] > 0
    assert pos["notional"] > 0
    assert pos["margin"] == pytest.approx(pos["notional"] / 50, rel=1e-5)
    assert body["rules"]["risk_pct"] == 0.025
    assert body["rules"]["leverage"] == 50


def test_costs_endpoint_exposes_breakeven():
    body = client.get("/api/costs").json()
    assert body["round_trip_cost_pct_of_equity_at_50x"] > 0
    assert body["breakeven_move_pct"] > 0


# ------------------------------------------------------------- monitor routes ---

def test_monitor_starts_with_the_app_lifespan():
    """Startup events fire inside the TestClient context manager."""
    with TestClient(app) as c:
        assert c.get("/api/monitor").json()["running"] is True


def test_monitor_stops_cleanly_on_shutdown():
    with TestClient(app) as c:
        assert c.get("/api/monitor").json()["running"] is True
    assert client.get("/api/monitor").json()["running"] is False


def test_forced_cycle_advances_the_monitor():
    before = client.get("/api/monitor").json()["cycles"]
    client.post("/api/monitor/cycle")
    after = client.get("/api/monitor").json()["cycles"]
    assert after > before


def test_monitor_accumulates_activity_at_runtime():
    for _ in range(120):
        client.post("/api/monitor/cycle")
    snap = client.get("/api/monitor").json()
    assert snap["cycles"] >= 120
    assert snap["closed_trades"] > 0 or snap["open_positions"] > 0
    hist = client.get("/api/monitor/history").json()
    assert hist["count"] >= 0


def test_status_includes_monitor_and_engine():
    body = client.get("/api/status").json()
    assert "monitor" in body and "engine" in body
    assert body["engine"]["win_rate_pct"] < 100.0


# ------------------------------------------------ deployment readiness ---

def test_replit_config_present_and_binds_all_interfaces():
    cfg = open(".replit").read()
    assert "uvicorn app:app" in cfg
    assert "0.0.0.0" in cfg            # must not bind localhost on a PaaS
    assert "PORT" in cfg               # honours the injected port


def test_procfile_present():
    assert "uvicorn app:app" in open("Procfile").read()


def test_entrypoint_honours_the_port_env_var():
    src = open("app.py").read()
    assert 'os.environ.get("PORT"' in src
    assert 'host="0.0.0.0"' in src


def test_runtime_dependencies_are_declared():
    reqs = open("requirements.txt").read().lower()
    for pkg in ("fastapi", "uvicorn", "jinja2"):
        assert pkg in reqs, pkg


def test_no_network_needed_at_boot():
    """Vendored data means the app starts in a sandboxed/offline container."""
    from v01t.dataset import load_month
    for m in ("jan2026", "jun2026", "jul2026"):
        assert load_month(m).origin == "vendored"


def test_monitor_starts_and_stops_with_the_app_lifespan():
    with TestClient(app) as c:
        assert c.get("/api/ve_monitor").json()["running"] is True
    assert client.get("/api/ve_monitor").json()["running"] is False


# ------------------------------------------- exchange execution surface ---

EXCHANGE_ENDPOINTS = [
    "/api/exchange", "/api/exchange/preflight", "/api/exchange/orders",
    "/api/exchange/preview?price=90000", "/api/exchange/risk",
]


@pytest.mark.parametrize("path", EXCHANGE_ENDPOINTS)
def test_exchange_endpoint_returns_200(path):
    assert client.get(path).status_code == 200


def test_exchange_defaults_to_paper_mode():
    """Importing the app must never be able to place a real order."""
    body = client.get("/api/exchange").json()
    assert body["mode"] == "paper"
    assert body["exchange"] == "kucoin-futures"


def test_exchange_declares_hedge_mode_requirement():
    body = client.get("/api/exchange").json()
    assert body["hedge_mode_required"] is True
    assert "zero exposure" in body["hedge_mode_note"]


def test_exchange_declares_double_entry():
    de = client.get("/api/exchange").json()["double_entry"]
    assert de["legs_per_squeeze"] == 2
    assert de["long"]["position_side"] == "long"
    assert de["short"]["position_side"] == "short"
    assert de["net_pct_of_capital"] == pytest.approx(0.225)


def test_exchange_reports_credential_presence_not_values():
    creds = client.get("/api/exchange").json()["credentials"]
    for v in creds.values():
        assert isinstance(v, bool)          # never leak a key


def test_preview_returns_both_legs_with_brackets():
    d = client.get("/api/exchange/preview?price=90000&equity=10000").json()
    assert len(d["legs"]) == 2
    assert {l["positionSide"] for l in d["legs"]} == {"long", "short"}
    assert {l["side"] for l in d["legs"]} == {"buy", "sell"}
    for leg in d["legs"]:
        assert leg["stopLoss"] > 0 and leg["takeProfit"] > 0
        assert isinstance(leg["size"], int)


def test_preview_flags_untradable_size():
    d = client.get("/api/exchange/preview?price=90000&equity=1").json()
    assert d["tradable"] is False
    assert d["contracts_per_leg"] == 0


def test_preview_has_no_side_effects():
    before = client.get("/api/exchange/orders").json()["count"]
    client.get("/api/exchange/preview?price=90000")
    assert client.get("/api/exchange/orders").json()["count"] == before


def test_exchange_risk_exposes_all_rails():
    lim = client.get("/api/exchange/risk").json()["limits"]
    for k in ("max_concurrent_squeezes", "max_daily_loss_pct",
              "max_notional_per_leg", "min_free_balance", "kill_switch"):
        assert k in lim


def test_exchange_cycle_executes_the_double_entry():
    r = client.post("/api/exchange/cycle")
    assert r.status_code == 200
    assert "cycle" in r.json()


def test_dashboard_exposes_the_auto_trading_view():
    html = client.get("/").text
    assert 'id="view-execution"' in html
    assert 'data-view="execution"' in html
    assert "Auto Trading" in html
    assert "positionSide" in html          # the leg contract is shown


# ------------------------------------------------ KuCoin is the sole venue ---

def test_no_bybit_anywhere_in_the_project():
    """Regression guard: Bybit was removed; it must not reappear."""
    import pathlib
    root = pathlib.Path(__file__).resolve().parent.parent
    hits = []
    for f in root.rglob("*"):
        if not f.is_file():
            continue
        if any(part in {".git", "__pycache__", ".pytest_cache"} for part in f.parts):
            continue
        if f.suffix not in {".py", ".js", ".css", ".html", ".md", ".txt", ".yml", ".json"}:
            continue
        if f.name == "test_app.py":          # this guard names it deliberately
            continue
        try:
            if "bybit" in f.read_text(errors="ignore").lower():
                hits.append(str(f.relative_to(root)))
        except Exception:
            pass
    assert hits == [], "Bybit references remain: %s" % hits


def test_kucoin_is_the_only_exchange_exposed():
    body = client.get("/api/exchange").json()
    assert body["exchange"] == "kucoin-futures"
    assert "alternate" not in body
    for key in body["credentials"]:
        assert "bybit" not in key.lower()


def test_kucoin_modules_are_intact():
    from v01t import kucoin, kucoin_executor
    assert kucoin.DEFAULT_SYMBOL == "XBTUSDTM"
    assert kucoin_executor.MODE_PAPER == "paper"
