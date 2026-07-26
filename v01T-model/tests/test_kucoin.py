"""KuCoin Futures client + executor: every path verified offline."""

import base64
import hashlib
import hmac

import pytest

from v01t import spec
from v01t.kucoin import (DEFAULT_SYMBOL, POSITION_LONG, POSITION_SHORT,
                         SIDE_BUY, SIDE_SELL, KucoinClient, KucoinError,
                         sign_message, sign_passphrase)
from v01t.kucoin_executor import (MODE_DRY_RUN, MODE_LIVE, MODE_PAPER,
                                  KucoinExecutor, RiskLimits)


class MockTransport:
    """Records requests and returns canned KuCoin Futures responses."""

    def __init__(self, fail_on=None):
        self.requests = []
        self.fail_on = fail_on or {}

    def __call__(self, method, url, headers, body, timeout):
        import json as _json
        path = url.split("?")[0]
        for base in ("https://api-sandbox-futures.kucoin.com",
                     "https://api-futures.kucoin.com"):
            path = path.replace(base, "")
        payload = _json.loads(body) if body else {}
        self.requests.append({"method": method, "path": path,
                              "headers": headers, "body": payload})
        if path in self.fail_on:
            return self.fail_on[path]
        if path == "/api/v1/timestamp":
            return {"code": "200000", "data": 1700000000000}
        if path == "/api/v1/kline/query":
            return {"code": "200000",
                    "data": [[i, 1, 2, 0.5, 60000 + i, 10] for i in range(200)]}
        if path.startswith("/api/v1/contracts/"):
            return {"code": "200000",
                    "data": {"multiplier": "0.001", "lotSize": "1"}}
        if path.startswith("/api/v1/mark-price/"):
            return {"code": "200000", "data": {"value": "60000"}}
        if path == "/api/v1/account-overview":
            return {"code": "200000", "data": {"availableBalance": "10000"}}
        if path == "/api/v1/position/getPositionMode":
            return {"code": "200000", "data": {"positionMode": 1}}
        if path in ("/api/v1/position/changePositionMode",
                    "/api/v2/position/changeCrossUserLeverage"):
            return {"code": "200000", "data": True}
        if path == "/api/v1/positions":
            return {"code": "200000", "data": []}
        if path == "/api/v1/orders":
            return {"code": "200000", "data": {"orderId": "mock-kucoin-order"}}
        return {"code": "200000", "data": {}}


@pytest.fixture
def client():
    return KucoinClient(api_key="k", api_secret="s", api_passphrase="p",
                        sandbox=True, transport=MockTransport())


# ----------------------------------------------------------------- signing ---

def test_signature_is_base64_not_hex():
    """KuCoin base64-encodes the HMAC digest, not hex. Easy to get wrong."""
    sig = sign_message("secret", "message")
    assert base64.b64decode(sig)                    # valid base64
    expected = base64.b64encode(
        hmac.new(b"secret", b"message", hashlib.sha256).digest()).decode()
    assert sig == expected
    assert sig != hmac.new(b"secret", b"message", hashlib.sha256).hexdigest()


def test_passphrase_is_itself_signed():
    assert sign_passphrase("secret", "pass") == sign_message("secret", "pass")


def test_signed_request_sends_all_five_headers(client):
    client.balance()
    h = client.transport.requests[-1]["headers"]
    for key in ("KC-API-KEY", "KC-API-SIGN", "KC-API-TIMESTAMP",
                "KC-API-PASSPHRASE", "KC-API-KEY-VERSION"):
        assert key in h, key
    assert h["KC-API-KEY-VERSION"] == "2"


def test_public_request_is_unsigned(client):
    client.server_time()
    assert "KC-API-SIGN" not in client.transport.requests[-1]["headers"]


def test_signed_request_requires_passphrase():
    c = KucoinClient(api_key="k", api_secret="s", transport=MockTransport())
    with pytest.raises(KucoinError, match="passphrase"):
        c.balance()


def test_nonzero_code_raises():
    t = MockTransport(fail_on={"/api/v1/orders":
                               {"code": "400100", "msg": "bad request"}})
    c = KucoinClient(api_key="k", api_secret="s", api_passphrase="p", transport=t)
    with pytest.raises(KucoinError, match="400100"):
        c.place_leg(DEFAULT_SYMBOL, SIDE_BUY, 1, 50, 61000, 59000, POSITION_LONG)


def test_sandbox_is_the_default_endpoint():
    assert "sandbox" in KucoinClient().base_url


# ------------------------------------------------------------ market data ---

def test_closes_are_oldest_first(client):
    c = client.closes(DEFAULT_SYMBOL, limit=200)
    assert len(c) == 200 and c[0] < c[-1]


def test_lot_size(client):
    mult, lot = client.lot_size(DEFAULT_SYMBOL)
    assert mult == 0.001 and lot == 1


# -------------------------------------------------------------- hedge mode ---

def test_ensure_hedge_mode_requests_dual_side(client):
    client.ensure_hedge_mode()
    assert client.transport.requests[-1]["body"]["positionMode"] == 1


def test_hedge_mode_already_set_is_not_an_error():
    t = MockTransport(fail_on={"/api/v1/position/changePositionMode":
                               {"code": "300018", "msg": "not modified"}})
    c = KucoinClient(api_key="k", api_secret="s", api_passphrase="p", transport=t)
    assert str(c.ensure_hedge_mode()["code"]) == "200000"


def test_preflight_reports_ready(client):
    r = client.preflight(DEFAULT_SYMBOL, 50)
    assert r["ready"] is True
    assert r["exchange"] == "kucoin-futures"


def test_preflight_fails_without_credentials():
    c = KucoinClient(transport=MockTransport())
    r = c.preflight(DEFAULT_SYMBOL, 50)
    assert r["ready"] is False and "credentials" in r["blocking"]


def test_preflight_fails_when_transport_is_down():
    def dead(*a, **k):
        raise OSError("network unreachable")
    c = KucoinClient(api_key="k", api_secret="s", api_passphrase="p",
                     transport=dead)
    assert c.preflight()["ready"] is False


# ------------------------------------------------------------ double entry ---

def test_long_leg_uses_position_side_long(client):
    client.place_leg(DEFAULT_SYMBOL, SIDE_BUY, 5, 50, 61000, 59000, POSITION_LONG)
    b = client.transport.requests[-1]["body"]
    assert b["side"] == "buy" and b["positionSide"] == "long"


def test_short_leg_uses_position_side_short(client):
    client.place_leg(DEFAULT_SYMBOL, SIDE_SELL, 5, 50, 59000, 61000, POSITION_SHORT)
    b = client.transport.requests[-1]["body"]
    assert b["side"] == "sell" and b["positionSide"] == "short"


def test_every_leg_carries_a_server_side_bracket(client):
    client.place_leg(DEFAULT_SYMBOL, SIDE_BUY, 5, 50, 61000, 59000, POSITION_LONG)
    b = client.transport.requests[-1]["body"]
    assert float(b["triggerStopUpPrice"]) == 61000
    assert float(b["triggerStopDownPrice"]) == 59000


def test_bad_position_side_is_rejected(client):
    with pytest.raises(KucoinError, match="hedge mode"):
        client.place_leg(DEFAULT_SYMBOL, SIDE_BUY, 5, 50, 61000, 59000, "both")


def test_fractional_size_is_rejected(client):
    """KuCoin futures trade in integer contracts."""
    with pytest.raises(KucoinError, match="integer"):
        client.place_leg(DEFAULT_SYMBOL, SIDE_BUY, 1.5, 50, 61000, 59000,
                         POSITION_LONG)


# ---------------------------------------------------------------- executor ---

def test_paper_is_the_default_mode():
    assert KucoinExecutor().mode == MODE_PAPER


def test_paper_mode_never_touches_the_exchange():
    ex = KucoinExecutor()
    assert ex.client is None
    sq = ex.execute_squeeze({"price": 60000.0, "bb_pct": 5.0,
                             "hv_ratio": 0.4, "score": 92})
    assert sq.long_result["simulated"] is True


def test_live_mode_refused_without_confirmation(monkeypatch, client):
    monkeypatch.delenv("V01T_LIVE", raising=False)
    with pytest.raises(PermissionError, match="I_UNDERSTAND"):
        KucoinExecutor(client=client, mode=MODE_LIVE)


def test_dry_run_logs_but_sends_nothing(client):
    ex = KucoinExecutor(client=client, mode=MODE_DRY_RUN)
    sq = ex.execute_squeeze({"price": 60000.0, "bb_pct": 5.0,
                             "hv_ratio": 0.4, "score": 92})
    assert sq.long_result["dry_run"] is True
    assert not any(r["path"] == "/api/v1/orders"
                   for r in client.transport.requests)


def test_live_mode_places_exactly_two_legs(monkeypatch, client):
    monkeypatch.setenv("V01T_LIVE", "I_UNDERSTAND")
    ex = KucoinExecutor(client=client, mode=MODE_LIVE)
    ex.execute_squeeze({"price": 60000.0, "bb_pct": 5.0,
                        "hv_ratio": 0.4, "score": 92})
    orders = [r for r in client.transport.requests
              if r["path"] == "/api/v1/orders"]
    assert len(orders) == 2
    assert {o["body"]["positionSide"] for o in orders} == {"long", "short"}
    assert {o["body"]["side"] for o in orders} == {"buy", "sell"}
    assert ex.state.legs_placed == 2


def test_levels_match_the_spec():
    lv = KucoinExecutor().levels(60000.0)
    assert lv["long_stop"] == pytest.approx(60000 * (1 - spec.STOP_PCT))
    assert lv["long_target"] == pytest.approx(60000 * (1 + spec.TP_PCT))
    assert lv["short_stop"] == pytest.approx(60000 * (1 + spec.STOP_PCT))
    assert lv["short_target"] == pytest.approx(60000 * (1 - spec.TP_PCT))


def test_contracts_are_integers_and_split_the_notional():
    ex = KucoinExecutor(equity=10_000, leverage=50, multiplier=0.001,
                        limits=RiskLimits(max_notional_per_leg=1e12))
    n = ex.leg_contracts(60000.0)
    assert isinstance(n, int)
    # 10000*50/2 = 250k notional /60000 /0.001 = 4166 contracts
    assert n == 4166
    assert ex.contracts_notional(n, 60000.0) == pytest.approx(249_960.0)


def test_size_rounding_to_zero_is_refused():
    """Equity too small for one contract — refuse, do not send a garbage order.

    min_free_balance is lowered here so the sizing guard is what trips, not the
    balance rail (which would otherwise fire first and mask it).
    """
    ex = KucoinExecutor(equity=0.5, leverage=1, multiplier=0.001,
                        limits=RiskLimits(min_free_balance=0.0))
    assert ex.leg_contracts(60000.0) == 0
    assert ex.execute_squeeze({"price": 60000.0, "bb_pct": 5.0,
                               "hv_ratio": 0.4, "score": 92}) is None
    assert "zero contracts" in ex.state.last_rejection


def test_min_balance_rail_fires_before_sizing():
    """A dust account is stopped by the balance rail, not by order maths."""
    ex = KucoinExecutor(equity=0.5, limits=RiskLimits(min_free_balance=10.0))
    assert ex.execute_squeeze({"price": 60000.0, "bb_pct": 5.0,
                               "hv_ratio": 0.4, "score": 92}) is None
    assert "balance below minimum" in ex.state.last_rejection


def test_notional_cap_limits_size():
    ex = KucoinExecutor(equity=1_000_000, leverage=50, multiplier=0.001,
                        limits=RiskLimits(max_notional_per_leg=60_000))
    assert ex.leg_contracts(60000.0) == 1000     # 60k/60000/0.001


# ---------------------------------------------------------------- risk rails ---

def test_kill_switch_blocks_execution():
    ex = KucoinExecutor(limits=RiskLimits(kill_switch=True))
    assert ex.execute_squeeze({"price": 60000.0, "bb_pct": 5.0,
                               "hv_ratio": 0.4, "score": 92}) is None
    assert "kill switch" in ex.state.last_rejection


def test_max_concurrent_squeezes_enforced():
    ex = KucoinExecutor(limits=RiskLimits(max_concurrent_squeezes=2))
    sig = {"price": 60000.0, "bb_pct": 5.0, "hv_ratio": 0.4, "score": 92}
    assert ex.execute_squeeze(sig) and ex.execute_squeeze(sig)
    assert ex.execute_squeeze(sig) is None
    assert "max concurrent" in ex.state.last_rejection


def test_daily_loss_limit_enforced():
    ex = KucoinExecutor(equity=10_000, limits=RiskLimits(max_daily_loss_pct=10.0))
    ex.state.equity = 8_500
    assert ex.execute_squeeze({"price": 60000.0, "bb_pct": 5.0,
                               "hv_ratio": 0.4, "score": 92}) is None
    assert "daily loss" in ex.state.last_rejection


# ------------------------------------------------------------------- signal ---

def test_executor_uses_the_shared_elite_gate():
    from v01t.dataset import load_month
    from v01t.indicators import is_elite
    ex = KucoinExecutor()
    sig = ex.evaluate(load_month("jul2026").closes[:200])
    assert sig["elite"] == is_elite(sig["bb_pct"], sig["hv_ratio"], sig["score"])


def test_cycle_executes_on_a_genuine_squeeze():
    ex = KucoinExecutor()
    out = ex.cycle([100.0 + i * 0.01 for i in range(60)])
    assert out["elite"] is True
    assert ex.state.legs_placed == 2


def test_cycle_survives_errors():
    ex = KucoinExecutor()
    r = ex.cycle([1.0, 2.0])
    assert "skipped" in r or "error" in r


def test_run_kucoin_preflight_exit_code_matches_the_report():
    import run_kucoin
    assert run_kucoin.main(["--preflight"]) == 1     # no keys in the environment


def test_snapshot_serialises():
    import json
    assert json.dumps(KucoinExecutor().state.snapshot())
