"""Bybit client + executor: every path verified offline with a mock transport."""

import os

import pytest

from v01t import spec
from v01t.bybit import (CATEGORY, MODE_HEDGE, POSITION_IDX_LONG,
                        POSITION_IDX_SHORT, BybitClient, BybitError,
                        sign_payload)
from v01t.bybit_executor import (MODE_DRY_RUN, MODE_LIVE, MODE_PAPER,
                                 BybitExecutor, RiskLimits)


class MockTransport:
    """Records requests and returns canned Bybit V5 responses."""

    def __init__(self, fail_on=None):
        self.requests = []
        self.fail_on = fail_on or {}

    def __call__(self, method, url, headers, body, timeout):
        import json as _json
        path = url.split("?")[0].replace("https://api-testnet.bybit.com", "")
        payload = _json.loads(body) if body else {}
        self.requests.append({"method": method, "path": path,
                              "headers": headers, "body": payload})
        if path in self.fail_on:
            return self.fail_on[path]
        if path == "/v5/market/time":
            return {"retCode": 0, "result": {"timeSecond": "1700000000"}}
        if path == "/v5/market/kline":
            rows = [[str(i), "1", "2", "0.5", str(60000 + i), "10", "1"]
                    for i in range(200)]
            return {"retCode": 0, "result": {"list": list(reversed(rows))}}
        if path == "/v5/market/instruments-info":
            return {"retCode": 0, "result": {"list": [
                {"lotSizeFilter": {"qtyStep": "0.001", "minOrderQty": "0.001"}}]}}
        if path == "/v5/account/wallet-balance":
            return {"retCode": 0, "result": {"list": [
                {"coin": [{"coin": "USDT", "walletBalance": "10000"}]}]}}
        if path == "/v5/position/list":
            return {"retCode": 0, "result": {"list": [
                {"positionIdx": 1, "size": "0"}, {"positionIdx": 2, "size": "0"}]}}
        if path in ("/v5/position/switch-mode", "/v5/position/set-leverage"):
            return {"retCode": 0, "result": {}}
        if path == "/v5/order/create":
            return {"retCode": 0, "result": {"orderId": "mock-order-id"}}
        return {"retCode": 0, "result": {}}


@pytest.fixture
def client():
    return BybitClient(api_key="k", api_secret="s", testnet=True,
                       transport=MockTransport())


# ----------------------------------------------------------------- signing ---

def test_signature_is_deterministic():
    a = sign_payload("secret", "1700000000000", "key", "5000", '{"a":1}')
    b = sign_payload("secret", "1700000000000", "key", "5000", '{"a":1}')
    assert a == b and len(a) == 64


def test_signature_changes_with_payload():
    a = sign_payload("secret", "1", "key", "5000", '{"a":1}')
    b = sign_payload("secret", "1", "key", "5000", '{"a":2}')
    assert a != b


def test_signed_request_sends_auth_headers(client):
    client.wallet_balance()
    h = client.transport.requests[-1]["headers"]
    for key in ("X-BAPI-API-KEY", "X-BAPI-SIGN", "X-BAPI-TIMESTAMP",
                "X-BAPI-RECV-WINDOW"):
        assert key in h


def test_public_request_is_unsigned(client):
    client.server_time()
    assert "X-BAPI-SIGN" not in client.transport.requests[-1]["headers"]


def test_signed_request_needs_credentials():
    c = BybitClient(transport=MockTransport())
    with pytest.raises(BybitError, match="api_key"):
        c.wallet_balance()


def test_nonzero_retcode_raises():
    t = MockTransport(fail_on={"/v5/order/create":
                               {"retCode": 10001, "retMsg": "bad"}})
    c = BybitClient(api_key="k", api_secret="s", transport=t)
    with pytest.raises(BybitError, match="10001"):
        c.place_leg("BTCUSDT", "Buy", 1.0, 61000, 59000, POSITION_IDX_LONG)


def test_testnet_is_the_default_endpoint():
    assert "testnet" in BybitClient().base_url


# ------------------------------------------------------------ market data ---

def test_closes_are_oldest_first(client):
    c = client.closes("BTCUSDT", limit=200)
    assert len(c) == 200
    assert c[0] < c[-1]          # mock increases with index


def test_qty_step(client):
    step, minq = client.qty_step("BTCUSDT")
    assert step == 0.001 and minq == 0.001


# -------------------------------------------------------------- hedge mode ---

def test_ensure_hedge_mode_requests_both_sides(client):
    client.ensure_hedge_mode("BTCUSDT")
    body = client.transport.requests[-1]["body"]
    assert body["mode"] == MODE_HEDGE
    assert body["category"] == CATEGORY


def test_hedge_mode_already_set_is_not_an_error():
    t = MockTransport(fail_on={"/v5/position/switch-mode":
                               {"retCode": 110025, "retMsg": "not modified"}})
    c = BybitClient(api_key="k", api_secret="s", transport=t)
    assert c.ensure_hedge_mode()["retCode"] == 0


def test_leverage_already_set_is_not_an_error():
    t = MockTransport(fail_on={"/v5/position/set-leverage":
                               {"retCode": 110043, "retMsg": "not modified"}})
    c = BybitClient(api_key="k", api_secret="s", transport=t)
    assert c.set_leverage("BTCUSDT", 50)["retCode"] == 0


def test_preflight_reports_ready(client):
    r = client.preflight("BTCUSDT", 50)
    assert r["ready"] is True
    assert all(c["ok"] for c in r["checks"].values())


# ------------------------------------------------------------ double entry ---

def test_long_leg_uses_position_idx_1(client):
    client.place_leg("BTCUSDT", "Buy", 0.5, 61000, 59000, POSITION_IDX_LONG)
    b = client.transport.requests[-1]["body"]
    assert b["side"] == "Buy" and b["positionIdx"] == 1


def test_short_leg_uses_position_idx_2(client):
    client.place_leg("BTCUSDT", "Sell", 0.5, 59000, 61000, POSITION_IDX_SHORT)
    b = client.transport.requests[-1]["body"]
    assert b["side"] == "Sell" and b["positionIdx"] == 2


def test_every_leg_carries_sl_and_tp(client):
    client.place_leg("BTCUSDT", "Buy", 0.5, 61000, 59000, POSITION_IDX_LONG)
    b = client.transport.requests[-1]["body"]
    assert float(b["takeProfit"]) == 61000
    assert float(b["stopLoss"]) == 59000


def test_position_idx_zero_is_rejected(client):
    """positionIdx 0 = one-way mode, which nets the two legs to zero."""
    with pytest.raises(BybitError, match="hedge mode"):
        client.place_leg("BTCUSDT", "Buy", 0.5, 61000, 59000, 0)


def test_bad_side_is_rejected(client):
    with pytest.raises(BybitError, match="Buy or Sell"):
        client.place_leg("BTCUSDT", "long", 0.5, 61000, 59000, 1)


# ------------------------------------------------------------- executor ---

def test_paper_is_the_default_mode():
    assert BybitExecutor().mode == MODE_PAPER


def test_paper_mode_never_touches_the_exchange():
    ex = BybitExecutor()
    assert ex.client is None
    sig = {"price": 60000.0, "bb_pct": 5.0, "hv_ratio": 0.4, "score": 92}
    sq = ex.execute_squeeze(sig)
    assert sq.long_result["simulated"] is True


def test_live_mode_refused_without_confirmation(monkeypatch, client):
    monkeypatch.delenv("V01T_LIVE", raising=False)
    with pytest.raises(PermissionError, match="I_UNDERSTAND"):
        BybitExecutor(client=client, mode=MODE_LIVE)


def test_live_mode_allowed_with_confirmation(monkeypatch, client):
    monkeypatch.setenv("V01T_LIVE", "I_UNDERSTAND")
    assert BybitExecutor(client=client, mode=MODE_LIVE).mode == MODE_LIVE


def test_dry_run_logs_but_sends_nothing(client):
    ex = BybitExecutor(client=client, mode=MODE_DRY_RUN)
    sig = {"price": 60000.0, "bb_pct": 5.0, "hv_ratio": 0.4, "score": 92}
    sq = ex.execute_squeeze(sig)
    assert sq.long_result["dry_run"] is True
    assert not any(r["path"] == "/v5/order/create"
                   for r in client.transport.requests)


def test_live_mode_places_exactly_two_legs(monkeypatch, client):
    monkeypatch.setenv("V01T_LIVE", "I_UNDERSTAND")
    ex = BybitExecutor(client=client, mode=MODE_LIVE)
    ex.execute_squeeze({"price": 60000.0, "bb_pct": 5.0,
                        "hv_ratio": 0.4, "score": 92})
    orders = [r for r in client.transport.requests
              if r["path"] == "/v5/order/create"]
    assert len(orders) == 2
    assert {o["body"]["positionIdx"] for o in orders} == {1, 2}
    assert {o["body"]["side"] for o in orders} == {"Buy", "Sell"}
    assert ex.state.legs_placed == 2


def test_levels_match_the_spec():
    ex = BybitExecutor()
    lv = ex.levels(60000.0)
    assert lv["long_stop"] == pytest.approx(60000 * (1 - spec.STOP_PCT))
    assert lv["long_target"] == pytest.approx(60000 * (1 + spec.TP_PCT))
    assert lv["short_stop"] == pytest.approx(60000 * (1 + spec.STOP_PCT))
    assert lv["short_target"] == pytest.approx(60000 * (1 - spec.TP_PCT))


def test_qty_splits_notional_across_two_legs():
    ex = BybitExecutor(equity=10_000, leverage=50, qty_step=0.0,
                       limits=RiskLimits(max_notional_per_leg=1e12))
    qty = ex.leg_qty(60000.0)
    assert qty * 60000.0 == pytest.approx(10_000 * 50 / 2)


def test_qty_is_floored_to_the_step():
    ex = BybitExecutor(equity=10_000, qty_step=0.001)
    q = ex.leg_qty(60000.0)
    assert abs(q / 0.001 - round(q / 0.001)) < 1e-6


def test_dust_equity_produces_no_order():
    ex = BybitExecutor(equity=0.01, qty_step=0.001, min_qty=0.001)
    assert ex.execute_squeeze({"price": 60000.0, "bb_pct": 5.0,
                               "hv_ratio": 0.4, "score": 92}) is None


# ---------------------------------------------------------------- risk rails ---

def test_kill_switch_blocks_execution():
    ex = BybitExecutor(limits=RiskLimits(kill_switch=True))
    assert ex.execute_squeeze({"price": 60000.0, "bb_pct": 5.0,
                               "hv_ratio": 0.4, "score": 92}) is None
    assert "kill switch" in ex.state.last_rejection


def test_max_concurrent_squeezes_enforced():
    ex = BybitExecutor(limits=RiskLimits(max_concurrent_squeezes=2))
    sig = {"price": 60000.0, "bb_pct": 5.0, "hv_ratio": 0.4, "score": 92}
    assert ex.execute_squeeze(sig) and ex.execute_squeeze(sig)
    assert ex.execute_squeeze(sig) is None
    assert "max concurrent" in ex.state.last_rejection


def test_daily_loss_limit_enforced():
    ex = BybitExecutor(equity=10_000, limits=RiskLimits(max_daily_loss_pct=10.0))
    ex.state.equity = 8_500                       # -15%
    assert ex.execute_squeeze({"price": 60000.0, "bb_pct": 5.0,
                               "hv_ratio": 0.4, "score": 92}) is None
    assert "daily loss" in ex.state.last_rejection


def test_notional_cap_limits_size():
    ex = BybitExecutor(equity=1_000_000, leverage=50, qty_step=0.0,
                       limits=RiskLimits(max_notional_per_leg=50_000))
    assert ex.leg_qty(60000.0) * 60000.0 == pytest.approx(50_000)


# ------------------------------------------------------------------- signal ---

def test_executor_uses_the_shared_elite_gate():
    from v01t.dataset import load_month
    from v01t.indicators import is_elite
    ex = BybitExecutor()
    closes = load_month("jul2026").closes[:200]
    sig = ex.evaluate(closes)
    assert sig["elite"] == is_elite(sig["bb_pct"], sig["hv_ratio"], sig["score"])


def test_cycle_ignores_non_elite_bars():
    """A choppy random walk sits mid-band with HV>0.8, so it must not trade.

    (A perfectly linear ramp would NOT work here: it pins price at the band
    edge with collapsed HV, which is a genuine squeeze by definition.)
    """
    import random
    random.seed(3)
    closes = [100.0]
    for _ in range(59):
        closes.append(closes[-1] * (1 + random.uniform(-0.004, 0.004)))
    r = ex_cycle = BybitExecutor()
    out = ex_cycle.cycle(closes)
    assert out["elite"] is False
    assert ex_cycle.state.squeezes_executed == 0


def test_cycle_executes_on_a_genuine_squeeze():
    """A tight directional ramp pins the band with low HV = elite -> trades."""
    ex = BybitExecutor()
    closes = [100.0 + i * 0.01 for i in range(60)]
    out = ex.cycle(closes)
    assert out["elite"] is True
    assert ex.state.squeezes_executed == 1
    assert ex.state.legs_placed == 2


def test_cycle_survives_errors():
    ex = BybitExecutor()
    r = ex.cycle([1.0, 2.0])                            # too short
    assert "skipped" in r or "error" in r
    assert ex.state.cycles == 1


def test_snapshot_serialises():
    import json
    assert json.dumps(BybitExecutor().state.snapshot())


# ------------------------------------------------- preflight must fail safe ---

def test_preflight_fails_without_credentials():
    """No keys must never report ready — regression for a double-call bug in
    run_bybit.py that printed one report and returned the exit code of another."""
    c = BybitClient(api_key="", api_secret="", transport=MockTransport())
    r = c.preflight("BTCUSDT", 50)
    assert r["ready"] is False
    assert "credentials" in r["blocking"]


def test_preflight_fails_when_transport_is_down():
    def dead(*a, **k):
        raise OSError("network unreachable")
    c = BybitClient(api_key="k", api_secret="s", transport=dead)
    r = c.preflight("BTCUSDT", 50)
    assert r["ready"] is False


def test_run_bybit_preflight_exit_code_matches_the_report():
    import run_bybit
    assert run_bybit.main(["--preflight"]) == 1     # no keys in the environment


def test_executor_preflight_flags_hedge_mode_fatally():
    t = MockTransport(fail_on={"/v5/position/switch-mode":
                               {"retCode": 10001, "retMsg": "cannot switch"}})
    c = BybitClient(api_key="k", api_secret="s", transport=t)
    ex = BybitExecutor(client=c, mode=MODE_DRY_RUN)
    r = ex.preflight()
    assert r["ready"] is False
    assert "HEDGE MODE REQUIRED" in r["fatal"]
