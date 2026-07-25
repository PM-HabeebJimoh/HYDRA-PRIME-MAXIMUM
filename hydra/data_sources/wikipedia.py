"""
Wikipedia pageviews — Wikimedia REST API — ONLY REAL LIVE DATA PULLING AT RUNTIME
No synthetic fallback — error if fetch fails
Real-time pulling live for last 7 days
"""
import aiohttp
import logging
from datetime import datetime, timedelta
logger = logging.getLogger(__name__)

class WikipediaDataSource:
    BASE = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user"

    async def get_pageviews(self, article: str = "Gold", days: int = 7) -> dict:
        end = datetime.utcnow()
        start = end - timedelta(days=days)
        start_str = start.strftime("%Y%m%d")
        end_str = end.strftime("%Y%m%d")
        url = f"{self.BASE}/{article}/daily/{start_str}/{end_str}"
        headers = {"User-Agent": "HYDRA-PRIME-MAXIMUM/1.0"}
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        return {"live": False, "article": article, "error": f"status {resp.status}", "real_data_only": True, "no_synthetic": True}
                    data = await resp.json()
                    items = data.get("items", [])
                    views = [it.get("views", 0) for it in items]
                    if not views:
                        return {"live": False, "article": article, "error": "no views", "real_data_only": True}
                    avg = sum(views) / len(views) if views else 0
                    last = views[-1] if views else 0
                    spike_ratio = last / avg if avg > 0 else 0
                    spike = spike_ratio > 2.0
                    return {
                        "live": True,
                        "article": article,
                        "views": views,
                        "views_last_7d": views[-7:],
                        "avg_7d": round(avg,1),
                        "last": last,
                        "spike_ratio": round(spike_ratio,2),
                        "spike": spike,
                        "signal": 1 if spike else 0,
                        "strength": min(spike_ratio*20, 100) if spike else 0,
                        "real_data_only": True,
                        "no_synthetic": True,
                        "source": "Wikimedia API real-time pulling live for last 7 days",
                        "timestamp": datetime.utcnow().isoformat()
                    }
        except Exception as e:
            logger.debug(f"Wiki fetch {article}: {e}")
            return {"live": False, "article": article, "error": str(e), "real_data_only": True, "no_synthetic": True}

    async def batch_check(self, article_map: dict) -> dict:
        tasks = [self.get_pageviews(article) for article in article_map.values()]
        import asyncio
        results = await asyncio.gather(*tasks, return_exceptions=True)
        out = {}
        for (inst, art), res in zip(article_map.items(), results):
            if isinstance(res, Exception):
                out[inst] = {"live": False, "error": str(res), "real_data_only": True}
            else:
                out[inst] = res
        return out

    async def test_live_async(self) -> dict:
        try:
            res = await self.get_pageviews("Gold", days=7)
            return {"source": "wikipedia", "live": res.get("live", False), "sample": res, "real_data_only": True, "no_synthetic": True}
        except Exception as e:
            return {"source": "wikipedia", "live": False, "error": str(e), "real_data_only": True}
