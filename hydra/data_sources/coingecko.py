"""
CoinGecko — free crypto prices — ONLY REAL LIVE DATA PULLING, no synthetic fallback
"""
import aiohttp
import logging
logger = logging.getLogger(__name__)

class CoingeckoDataSource:
    BASE = "https://api.coingecko.com/api/v3"

    ID_MAP = {
        "BTCUSD": "bitcoin",
        "ETHUSD": "ethereum",
        "BNBUSD": "binancecoin",
        "SOLUSD": "solana",
        "XRPUSD": "ripple",
        "ADAUSD": "cardano",
        "DOGEUSD": "dogecoin",
        "AVAXUSD": "avalanche-2",
        "DOTUSD": "polkadot",
        "LINKUSD": "chainlink",
    }

    async def get_prices(self, instruments: list = None) -> dict:
        if instruments is None:
            instruments = list(self.ID_MAP.keys())
        ids = [self.ID_MAP.get(inst) for inst in instruments if self.ID_MAP.get(inst)]
        ids_str = ",".join(ids)
        url = f"{self.BASE}/simple/price?ids={ids_str}&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true"
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        logger.debug(f"Coingecko status {resp.status}")
                        return {"live": False, "error": f"status {resp.status}", "real_data_only": True}
                    data = await resp.json()
                    if not data:
                        return {"live": False, "error": "empty", "real_data_only": True}
                    return {"live": True, "data": data, "real_data_only": True, "source": "CoinGecko real-time pulling live"}
        except Exception as e:
            logger.debug(f"Coingecko: {e}")
            return {"live": False, "error": str(e), "real_data_only": True}

    async def test_live_async(self) -> dict:
        try:
            data = await self.get_prices(["BTCUSD", "ETHUSD"])
            live = data.get("live", False) if isinstance(data, dict) else len(data) > 0
            return {"source": "coingecko", "live": live, "real_data_only": True, "no_synthetic": True}
        except Exception as e:
            return {"source": "coingecko", "live": False, "error": str(e), "real_data_only": True}
