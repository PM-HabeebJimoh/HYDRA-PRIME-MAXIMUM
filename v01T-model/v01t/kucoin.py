"""
kucoin.py — KuCoin Futures API client for v01T automatic execution.

Zero dependencies: standard library only. The HTTP layer is injectable, so
signing, hedge mode, order construction and the risk paths are all unit-tested
offline without touching the network.

WHY KUCOIN
----------
v01T needs three things at once: perpetual futures with leverage, a working
trading API, and HEDGE MODE (dual-side positions). KuCoin provides all three,
and uniquely exposes the position-mode switch over the API rather than the UI
only. (MEXC, by contrast, has had its futures API disabled since July 2022.)

WHY HEDGE MODE IS MANDATORY
---------------------------
v01T uses DOUBLE ENTRY: each elite squeeze opens BOTH a long and a short leg at
the same price. In one-way mode those two orders net to zero exposure and the
model cannot function. KuCoin calls it "Hedge Mode"; positions are then tagged
with a side:

    side "buy"  + marginMode/positionSide long   -> long leg
    side "sell" + positionSide short             -> short leg

`ensure_hedge_mode()` sets it, and `preflight()` refuses to trade without it.

AUTH — differs from most exchanges
----------------------------------
KuCoin signs `timestamp + method + endpoint + body` with HMAC-SHA256 and then
**base64-encodes** the digest (Bybit uses a plain hex digest). It additionally
requires the API passphrase, itself signed the same way, plus a key-version
header. Getting any of these wrong returns 401.

Reference: https://www.kucoin.com/docs/rest/futures-trading/
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

FUTURES_MAINNET = "https://api-futures.kucoin.com"
FUTURES_SANDBOX = "https://api-sandbox-futures.kucoin.com"

KEY_VERSION = "2"
DEFAULT_SYMBOL = "XBTUSDTM"          # KuCoin's BTC/USDT perpetual

SIDE_BUY = "buy"
SIDE_SELL = "sell"
POSITION_LONG = "long"
POSITION_SHORT = "short"


class KucoinError(RuntimeError):
    """KuCoin returned a non-200000 code, or the transport failed."""


def _now_ms() -> str:
    return str(int(time.time() * 1000))


def sign_message(secret: str, message: str) -> str:
    """HMAC-SHA256 then base64 — KuCoin's scheme, not a hex digest."""
    return base64.b64encode(
        hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()
    ).decode()


def sign_passphrase(secret: str, passphrase: str) -> str:
    """The passphrase is itself signed for API key version 2+."""
    return sign_message(secret, passphrase)


def _urllib_transport(method: str, url: str, headers: Dict[str, str],
                      body: Optional[str], timeout: float) -> Dict[str, Any]:
    data = body.encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


@dataclass
class KucoinClient:
    """Minimal KuCoin Futures client covering everything v01T needs."""

    api_key: str = ""
    api_secret: str = ""
    api_passphrase: str = ""
    sandbox: bool = True
    timeout: float = 15.0
    transport: Callable[..., Dict[str, Any]] = _urllib_transport
    calls: list = field(default_factory=list)

    @property
    def base_url(self) -> str:
        return FUTURES_SANDBOX if self.sandbox else FUTURES_MAINNET

    # --------------------------------------------------------------- plumbing ---

    def _request(self, method: str, path: str,
                 params: Optional[Dict[str, Any]] = None,
                 signed: bool = False) -> Dict[str, Any]:
        params = params or {}
        endpoint = path
        body = ""

        if method == "GET":
            query = urllib.parse.urlencode(params)
            if query:
                endpoint = f"{path}?{query}"
        else:
            body = json.dumps(params, separators=(",", ":"))

        url = self.base_url + endpoint
        headers = {"Content-Type": "application/json"}

        if signed:
            if not (self.api_key and self.api_secret and self.api_passphrase):
                raise KucoinError(
                    "signed request requires api_key, api_secret and api_passphrase"
                )
            ts = _now_ms()
            # KuCoin signs: timestamp + METHOD + endpoint(with query) + body
            message = f"{ts}{method.upper()}{endpoint}{body}"
            headers.update({
                "KC-API-KEY": self.api_key,
                "KC-API-SIGN": sign_message(self.api_secret, message),
                "KC-API-TIMESTAMP": ts,
                "KC-API-PASSPHRASE": sign_passphrase(self.api_secret,
                                                     self.api_passphrase),
                "KC-API-KEY-VERSION": KEY_VERSION,
            })

        self.calls.append({"method": method, "path": path, "params": params,
                           "signed": signed})

        try:
            resp = self.transport(method, url, headers, body or None, self.timeout)
        except KucoinError:
            raise
        except Exception as exc:
            raise KucoinError(f"{type(exc).__name__}: {exc}") from exc

        if not isinstance(resp, dict):
            raise KucoinError(f"unexpected response type {type(resp).__name__}")
        code = str(resp.get("code", ""))
        if code != "200000":
            raise KucoinError(f"code={code} msg={resp.get('msg')!r} path={path}")
        return resp

    # ----------------------------------------------------------- market data ---

    def server_time(self) -> Dict[str, Any]:
        return self._request("GET", "/api/v1/timestamp")

    def klines(self, symbol: str = DEFAULT_SYMBOL, granularity: int = 60,
               limit: int = 200) -> list:
        """Candles. granularity is in MINUTES: 60 = 1h. Oldest first."""
        end = int(time.time() * 1000)
        start = end - granularity * 60 * 1000 * limit
        r = self._request("GET", "/api/v1/kline/query",
                          {"symbol": symbol, "granularity": granularity,
                           "from": start, "to": end})
        return r.get("data") or []

    def closes(self, symbol: str = DEFAULT_SYMBOL, granularity: int = 60,
               limit: int = 200) -> list:
        """Closing prices, oldest first — the input the v01T model expects.

        KuCoin kline rows are [time, open, high, low, close, volume].
        """
        return [float(row[4]) for row in self.klines(symbol, granularity, limit)]

    def contract(self, symbol: str = DEFAULT_SYMBOL) -> Dict[str, Any]:
        r = self._request("GET", f"/api/v1/contracts/{symbol}")
        data = r.get("data")
        if not data:
            raise KucoinError(f"unknown symbol {symbol}")
        return data

    def lot_size(self, symbol: str = DEFAULT_SYMBOL) -> tuple[float, float]:
        """(multiplier, lotSize) — futures trade in integer CONTRACTS."""
        c = self.contract(symbol)
        return float(c.get("multiplier", 0.001)), float(c.get("lotSize", 1))

    def mark_price(self, symbol: str = DEFAULT_SYMBOL) -> float:
        r = self._request("GET", f"/api/v1/mark-price/{symbol}/current")
        return float(r["data"]["value"])

    # -------------------------------------------------------------- account ---

    def balance(self, currency: str = "USDT") -> float:
        r = self._request("GET", "/api/v1/account-overview",
                          {"currency": currency}, signed=True)
        return float(r["data"].get("availableBalance") or 0.0)

    def position_mode(self) -> bool:
        """True when hedge (dual-side) mode is active."""
        r = self._request("GET", "/api/v2/position/getMarginMode"
                          if False else "/api/v1/position/getPositionMode",
                          signed=True)
        data = r.get("data") or {}
        return bool(data.get("positionMode") in (1, "1", True, "hedge"))

    def ensure_hedge_mode(self) -> Dict[str, Any]:
        """Switch the account to hedge mode. Idempotent where possible."""
        try:
            return self._request("POST", "/api/v1/position/changePositionMode",
                                 {"positionMode": 1}, signed=True)
        except KucoinError as exc:
            msg = str(exc).lower()
            if "not modified" in msg or "same" in msg or "300018" in msg:
                return {"code": "200000", "msg": "already hedge mode"}
            raise

    def set_leverage(self, symbol: str = DEFAULT_SYMBOL,
                     leverage: int = 50) -> Dict[str, Any]:
        try:
            return self._request("POST", "/api/v2/position/changeCrossUserLeverage",
                                 {"symbol": symbol, "leverage": str(leverage)},
                                 signed=True)
        except KucoinError as exc:
            if "not modified" in str(exc).lower():
                return {"code": "200000", "msg": "leverage already set"}
            raise

    def positions(self, symbol: str = DEFAULT_SYMBOL) -> list:
        r = self._request("GET", "/api/v1/positions", {"symbol": symbol},
                          signed=True)
        data = r.get("data")
        return data if isinstance(data, list) else [data] if data else []

    # ---------------------------------------------------------------- orders ---

    def place_leg(self, symbol: str, side: str, size: int, leverage: int,
                  take_profit: float, stop_loss: float,
                  position_side: str, client_oid: str = "") -> Dict[str, Any]:
        """One leg of the double entry, with SL and TP attached server-side.

        side "buy"  + position_side "long"  -> long leg
        side "sell" + position_side "short" -> short leg

        `size` is in CONTRACTS (integer), not coins — a KuCoin futures quirk.
        """
        if side not in (SIDE_BUY, SIDE_SELL):
            raise KucoinError(f"side must be {SIDE_BUY!r} or {SIDE_SELL!r}, got {side!r}")
        if position_side not in (POSITION_LONG, POSITION_SHORT):
            raise KucoinError("position_side must be 'long' or 'short'; hedge mode "
                              "is required for v01T double entry")
        if not isinstance(size, int) or size <= 0:
            raise KucoinError("size must be a positive integer number of contracts")

        params = {
            "clientOid": client_oid or f"v01t{_now_ms()}",
            "symbol": symbol,
            "side": side,
            "type": "market",
            "size": size,
            "leverage": str(leverage),
            "positionSide": position_side,
            # server-side bracket: whichever triggers first closes the leg
            "triggerStopUpPrice": f"{take_profit:.2f}" if side == SIDE_BUY
                                  else f"{stop_loss:.2f}",
            "triggerStopDownPrice": f"{stop_loss:.2f}" if side == SIDE_BUY
                                    else f"{take_profit:.2f}",
            "stopPriceType": "MP",          # mark price
            "marginMode": "CROSS",
        }
        return self._request("POST", "/api/v1/orders", params, signed=True)

    def close_leg(self, symbol: str, position_side: str,
                  size: int, leverage: int) -> Dict[str, Any]:
        """Emergency flat: reduce-only market order against one leg."""
        side = SIDE_SELL if position_side == POSITION_LONG else SIDE_BUY
        return self._request("POST", "/api/v1/orders", {
            "clientOid": f"v01tflat{_now_ms()}",
            "symbol": symbol, "side": side, "type": "market",
            "size": size, "leverage": str(leverage),
            "positionSide": position_side, "reduceOnly": True,
            "marginMode": "CROSS",
        }, signed=True)

    # -------------------------------------------------------------- preflight ---

    def preflight(self, symbol: str = DEFAULT_SYMBOL,
                  leverage: int = 50) -> Dict[str, Any]:
        """Verify the account can actually run v01T before any order is sent."""
        report: Dict[str, Any] = {"exchange": "kucoin-futures", "symbol": symbol,
                                  "sandbox": self.sandbox, "checks": {},
                                  "ready": False}

        def check(name, fn):
            try:
                report["checks"][name] = {"ok": True, "value": fn()}
            except Exception as exc:
                report["checks"][name] = {"ok": False, "error": str(exc)}

        check("connectivity", lambda: str(self.server_time().get("code")) == "200000")
        check("market_data", lambda: len(self.closes(symbol, limit=50)))
        check("contract", lambda: self.lot_size(symbol))
        check("credentials", lambda: self.balance())
        check("hedge_mode",
              lambda: str(self.ensure_hedge_mode().get("code")) == "200000")
        check("leverage",
              lambda: str(self.set_leverage(symbol, leverage).get("code")) == "200000")

        report["ready"] = all(c["ok"] for c in report["checks"].values())
        if not report["ready"]:
            report["blocking"] = [k for k, v in report["checks"].items()
                                  if not v["ok"]]
        return report
