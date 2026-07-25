"""
GDELT — Global news event database — ONLY REAL LIVE DATA PULLING
No synthetic fallback
"""
import aiohttp
import logging
logger = logging.getLogger(__name__)
from datetime import datetime

class GdeltDataSource:
    BASE = "https://api.gdeltproject.org/api/v2/doc/doc"

    async def search_news(self, query: str = "gold price", max_records: int = 10) -> dict:
        params = {
            "query": query,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": str(max_records),
            "sort": "datedesc"
        }
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(self.BASE, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        return {"live": False, "query": query, "error": f"status {resp.status}", "real_data_only": True}
                    try:
                        data = await resp.json()
                    except:
                        text = await resp.text()
                        return {"live": True, "query": query, "articles_raw": text[:500], "real_data_only": True, "source": "GDELT real-time"}
                    articles = data.get("articles", [])
                    return {"live": True, "query": query, "count": len(articles), "articles": articles[:max_records], "source": "GDELT real-time pulling live", "real_data_only": True, "timestamp": datetime.utcnow().isoformat()}
        except Exception as e:
            return {"live": False, "query": query, "error": str(e), "real_data_only": True}

    async def detect_surge(self, query: str, baseline: int = 5) -> dict:
        res = await self.search_news(query, max_records=20)
        if not res.get("live"):
            return {"live": False, "query": query, "real_data_only": True}
        count = res.get("count", 0)
        surge = count > baseline * 2
        return {"live": True, "query": query, "count": count, "surge": surge, "surge_ratio": round(count / max(baseline,1),2), "real_data_only": True, "source": "GDELT surge detection real-time"}

    async def test_live_async(self) -> dict:
        res = await self.search_news("gold price", 5)
        return {"source": "gdelt", "live": res.get("live", False), "real_data_only": True, "no_synthetic": True}
