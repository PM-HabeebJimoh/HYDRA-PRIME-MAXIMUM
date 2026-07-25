"""
Binance public API — free, no key, orderbook + trades for OBI/VPIN
ONLY REAL LIVE DATA PULLING AT RUNTIME — no synthetic fallback
"""
import aiohttp
import asyncio
import logging
from typing import Dict, List
logger = logging.getLogger(__name__)

class BinanceDataSource:
    BASE = "https://api.binance.com"

    async def _get(self, session: aiohttp.ClientSession, path: str, params: dict = None):
        try:
            async with session.get(f"{self.BASE}{path}", params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.debug(f"Binance {path} status {resp.status}")
                    return None
        except Exception as e:
            logger.debug(f"Binance _get {path}: {e}")
            return None

    async def get_ticker_24hr(self, symbol: str = None) -> dict:
        async with aiohttp.ClientSession() as sess:
            params = {}
            if symbol:
                params["symbol"] = symbol
            data = await self._get(sess, "/api/v3/ticker/24hr", params)
            if data is None:
                return {"live": False, "symbol": symbol, "error": "fetch failed", "real_data_only": True}
            # mark live
            if isinstance(data, dict):
                data["live"] = True
                data["real_data_only"] = True
                data["source"] = "Binance Ticker 24hr real-time"
            elif isinstance(data, list):
                return {"live": True, "data": data, "real_data_only": True, "source": "Binance Ticker real-time"}
            return data

    async def get_orderbook(self, symbol: str, limit: int = 20) -> dict:
        async with aiohttp.ClientSession() as sess:
            data = await self._get(sess, "/api/v3/depth", {"symbol": symbol, "limit": limit})
            if not data or not data.get("bids"):
                return {"live": False, "symbol": symbol, "error": "orderbook fetch failed", "real_data_only": True}
            data["live"] = True
            data["real_data_only"] = True
            return data

    async def get_trades(self, symbol: str, limit: int = 100) -> List[dict]:
        async with aiohttp.ClientSession() as sess:
            data = await self._get(sess, "/api/v3/trades", {"symbol": symbol, "limit": limit})
            if not data:
                return []
            return data if isinstance(data, list) else []

    async def compute_obi(self, symbol: str) -> dict:
        """Order Book Imbalance: (bid_vol - ask_vol)/(bid_vol+ask_vol) — ONLY REAL"""
        ob = await self.get_orderbook(symbol, limit=20)
        if not ob.get("live"):
            return {"symbol": symbol, "live": False, "obi": 0.0, "real_data_only": True}
        bids = ob.get("bids", [])
        asks = ob.get("asks", [])
        if not bids or not asks:
            return {"symbol": symbol, "live": False, "obi": 0.0, "real_data_only": True}
        try:
            bid_vol = sum(float(b[1]) for b in bids)
            ask_vol = sum(float(a[1]) for a in asks)
            total = bid_vol + ask_vol
            obi = (bid_vol - ask_vol) / total if total > 0 else 0.0
            signal = 1 if obi > 0.2 else -1 if obi < -0.2 else 0
            return {"symbol": symbol, "live": True, "obi": round(obi, 4), "bid_vol": round(bid_vol, 2), "ask_vol": round(ask_vol, 2), "signal": signal, "strength": round(abs(obi)*100,1), "real_data_only": True, "source": "Binance Depth 20 OBI real-time"}
        except Exception as e:
            return {"symbol": symbol, "live": False, "obi": 0.0, "error": str(e), "real_data_only": True}

    async def test_live_async(self) -> dict:
        try:
            ob = await self.get_orderbook("BTCUSDT", 5)
            return {"source": "binance", "live": ob.get("live", False), "real_data_only": True}
        except Exception as e:
            return {"source": "binance", "live": False, "error": str(e), "real_data_only": True}
