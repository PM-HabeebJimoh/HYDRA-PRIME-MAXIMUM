"""
bybit.py — Bybit V5 API client for v01T automatic execution.

Zero dependencies: standard library only (urllib + hmac). The HTTP layer is
injectable, so every code path — signing, hedge mode, order construction — is
unit-tested offline without touching the network.

WHY HEDGE MODE IS MANDATORY
---------------------------
v01T uses DOUBLE ENTRY: each elite squeeze opens BOTH a long and a short leg at
the same price. On a one-way (netting) account those two orders cancel to zero
exposure and the model cannot function. Bybit calls the required setting
"Both Sides" / hedge mode, selected per position with `positionIdx`:

    positionIdx = 1   ->  long leg
    positionIdx = 2   ->  short leg

`ensure_hedge_mode()` sets it and `preflight()` refuses to trade without it.

Reference: https://bybit-exchange.github.io/docs/v5/intro
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

MAINNET = "https://api.bybit.com"
TESTNET = "https://api-testnet.bybit.com"

CATEGORY = "linear"          # USDT perpetuals
POSITION_IDX_LONG = 1
POSITION_IDX_SHORT = 2
MODE_HEDGE = 3               # "Both Sides"
MODE_ONE_WAY = 0             # "Merged Single" — incompatible with v01T

RECV_WINDOW = "5000"


class BybitError(RuntimeError):
    """Bybit returned a non-zero retCode, or the transport failed."""


def _now_ms() -> str:
    return str(int(time.time() * 1000))


def sign_payload(secret: str, timestamp: str, api_key: str,
                 recv_window: str, payload: str) -> str:
    """Bybit V5 signature: HMAC-SHA256 over ts + key + recv_window + payload."""
    to_sign = f"{timestamp}{api_key}{recv_window}{payload}"
    return hmac.new(secret.encode(), to_sign.encode(), hashlib.sha256).hexdigest()


def _urllib_transport(method: str, url: str, headers: Dict[str, str],
                      body: Optional[str], timeout: float) -> Dict[str, Any]:
    data = body.encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


@dataclass
class BybitClient:
    """Minimal Bybit V5 client covering everything v01T needs."""

    api_key: str = ""
    api_secret: str = ""
    testnet: bool = True
    timeout: float = 15.0
    # Injectable HTTP layer: (method, url, headers, body, timeout) -> dict
    transport: Callable[..., Dict[str, Any]] = _urllib_transport
    calls: list = field(default_factory=list)   # audit log of every request

    @property
    def base_url(self) -> str:
        return TESTNET if self.testnet else MAINNET

    # --------------------------------------------------------------- plumbing ---

    def _request(self, method: str, path: str,
                 params: Optional[Dict[str, Any]] = None,
                 signed: bool = False) -> Dict[str, Any]:
        params = params or {}
        url = self.base_url + path
        headers = {"Content-Type": "application/json"}
        body = None

        if method == "GET":
            query = urllib.parse.urlencode(params)
            payload = query
            if query:
                url = f"{url}?{query}"
        else:
            body = json.dumps(params, separators=(",", ":"))
            payload = body

        if signed:
            if not self.api_key or not self.api_secret:
                raise BybitError("signed request requires api_key and api_secret")
            ts = _now_ms()
            headers.update({
                "X-BAPI-API-KEY": self.api_key,
                "X-BAPI-TIMESTAMP": ts,
                "X-BAPI-RECV-WINDOW": RECV_WINDOW,
                "X-BAPI-SIGN": sign_payload(self.api_secret, ts, self.api_key,
                                            RECV_WINDOW, payload),
            })

        self.calls.append({"method": method, "path": path, "params": params,
                           "signed": signed})

        try:
            resp = self.transport(method, url, headers, body, self.timeout)
        except BybitError:
            raise
        except Exception as exc:                       # network, DNS, TLS, JSON
            raise BybitError(f"{type(exc).__name__}: {exc}") from exc

        if not isinstance(resp, dict):
            raise BybitError(f"unexpected response type {type(resp).__name__}")
        if resp.get("retCode", 0) != 0:
            raise BybitError(f"retCode={resp.get('retCode')} "
                             f"retMsg={resp.get('retMsg')!r} path={path}")
        return resp

    # ----------------------------------------------------------- market data ---

    def server_time(self) -> Dict[str, Any]:
        return self._request("GET", "/v5/market/time")

    def klines(self, symbol: str = "BTCUSDT", interval: str = "60",
               limit: int = 200) -> list:
        """Hourly candles. interval '60' = 1h. Newest first, so reversed here."""
        r = self._request("GET", "/v5/market/kline",
                          {"category": CATEGORY, "symbol": symbol,
                           "interval": interval, "limit": limit})
        rows = r["result"]["list"]
        return list(reversed(rows))

    def closes(self, symbol: str = "BTCUSDT", interval: str = "60",
               limit: int = 200) -> list:
        """Closing prices, oldest first — the input the v01T model expects."""
        return [float(row[4]) for row in self.klines(symbol, interval, limit)]

    def instrument(self, symbol: str = "BTCUSDT") -> Dict[str, Any]:
        r = self._request("GET", "/v5/market/instruments-info",
                          {"category": CATEGORY, "symbol": symbol})
        items = r["result"]["list"]
        if not items:
            raise BybitError(f"unknown symbol {symbol}")
        return items[0]

    def qty_step(self, symbol: str = "BTCUSDT") -> tuple[float, float]:
        """(qtyStep, minOrderQty) — order size must respect both."""
        f = self.instrument(symbol)["lotSizeFilter"]
        return float(f["qtyStep"]), float(f["minOrderQty"])

    # -------------------------------------------------------------- account ---

    def position_mode(self, symbol: str = "BTCUSDT") -> int:
        """0 = one-way (INCOMPATIBLE), 3 = hedge. Inferred from positionIdx."""
        r = self._request("GET", "/v5/position/list",
                          {"category": CATEGORY, "symbol": symbol}, signed=True)
        rows = r["result"]["list"]
        if not rows:
            return MODE_ONE_WAY
        return MODE_HEDGE if any(int(p.get("positionIdx", 0)) in (1, 2)
                                 for p in rows) else MODE_ONE_WAY

    def ensure_hedge_mode(self, symbol: str = "BTCUSDT") -> Dict[str, Any]:
        """Switch the symbol to Both Sides. Idempotent: 110025 = already set."""
        try:
            return self._request("POST", "/v5/position/switch-mode",
                                 {"category": CATEGORY, "symbol": symbol,
                                  "mode": MODE_HEDGE}, signed=True)
        except BybitError as exc:
            if "110025" in str(exc):            # not modified
                return {"retCode": 0, "retMsg": "already hedge mode"}
            raise

    def set_leverage(self, symbol: str = "BTCUSDT", leverage: int = 50) -> Dict[str, Any]:
        """Both sides must carry the same leverage. 110043 = already set."""
        try:
            return self._request("POST", "/v5/position/set-leverage",
                                 {"category": CATEGORY, "symbol": symbol,
                                  "buyLeverage": str(leverage),
                                  "sellLeverage": str(leverage)}, signed=True)
        except BybitError as exc:
            if "110043" in str(exc):
                return {"retCode": 0, "retMsg": "leverage already set"}
            raise

    def wallet_balance(self, coin: str = "USDT") -> float:
        r = self._request("GET", "/v5/account/wallet-balance",
                          {"accountType": "UNIFIED", "coin": coin}, signed=True)
        for acct in r["result"]["list"]:
            for c in acct.get("coin", []):
                if c.get("coin") == coin:
                    return float(c.get("walletBalance") or 0.0)
        return 0.0

    def positions(self, symbol: str = "BTCUSDT") -> list:
        r = self._request("GET", "/v5/position/list",
                          {"category": CATEGORY, "symbol": symbol}, signed=True)
        return r["result"]["list"]

    # ---------------------------------------------------------------- orders ---

    def place_leg(self, symbol: str, side: str, qty: float,
                  take_profit: float, stop_loss: float,
                  position_idx: int, order_link_id: str = "") -> Dict[str, Any]:
        """One leg of the double entry, with SL and TP attached server-side.

        side "Buy" + positionIdx 1  -> long leg
        side "Sell" + positionIdx 2 -> short leg
        """
        if side not in ("Buy", "Sell"):
            raise BybitError(f"side must be Buy or Sell, got {side!r}")
        if position_idx not in (POSITION_IDX_LONG, POSITION_IDX_SHORT):
            raise BybitError("positionIdx must be 1 (long) or 2 (short); "
                             "hedge mode is required for v01T double entry")
        if qty <= 0:
            raise BybitError("qty must be positive")

        params = {
            "category": CATEGORY,
            "symbol": symbol,
            "side": side,
            "orderType": "Market",
            "qty": str(qty),
            "positionIdx": position_idx,
            "takeProfit": f"{take_profit:.2f}",
            "stopLoss": f"{stop_loss:.2f}",
            "tpTriggerBy": "LastPrice",
            "slTriggerBy": "LastPrice",
            "timeInForce": "IOC",
            "reduceOnly": False,
        }
        if order_link_id:
            params["orderLinkId"] = order_link_id
        return self._request("POST", "/v5/order/create", params, signed=True)

    def close_leg(self, symbol: str, position_idx: int, qty: float) -> Dict[str, Any]:
        """Emergency flat: reduce-only market order against one leg."""
        side = "Sell" if position_idx == POSITION_IDX_LONG else "Buy"
        return self._request("POST", "/v5/order/create", {
            "category": CATEGORY, "symbol": symbol, "side": side,
            "orderType": "Market", "qty": str(qty),
            "positionIdx": position_idx, "reduceOnly": True,
            "timeInForce": "IOC",
        }, signed=True)

    # -------------------------------------------------------------- preflight ---

    def preflight(self, symbol: str = "BTCUSDT", leverage: int = 50) -> Dict[str, Any]:
        """Verify the account can actually run v01T before any order is sent."""
        report: Dict[str, Any] = {"symbol": symbol, "testnet": self.testnet,
                                  "checks": {}, "ready": False}

        def check(name, fn):
            try:
                report["checks"][name] = {"ok": True, "value": fn()}
            except Exception as exc:
                report["checks"][name] = {"ok": False, "error": str(exc)}

        check("connectivity", lambda: self.server_time()["retCode"] == 0)
        check("market_data", lambda: len(self.closes(symbol, limit=50)))
        check("instrument", lambda: self.qty_step(symbol))
        check("credentials", lambda: self.wallet_balance())
        check("hedge_mode", lambda: self.ensure_hedge_mode(symbol)["retCode"] == 0)
        check("leverage", lambda: self.set_leverage(symbol, leverage)["retCode"] == 0)

        report["ready"] = all(c["ok"] for c in report["checks"].values())
        if not report["ready"]:
            report["blocking"] = [k for k, v in report["checks"].items() if not v["ok"]]
        return report
