"""
FRED — Federal Reserve Economic Data — ONLY REAL LIVE DATA PULLING
No synthetic fallback
"""
import aiohttp
import logging
logger = logging.getLogger(__name__)
from datetime import datetime

class FredDataSource:
    BASE_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    SERIES = ["DFF", "DGS10", "T10Y2Y", "DEXUSEU", "DEXJPUS", "DTWEXBGS"]

    async def fetch_series(self, series_id: str = "DFF") -> dict:
        url = f"{self.BASE_CSV}?id={series_id}"
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        return {"live": False, "series": series_id, "error": f"status {resp.status}", "real_data_only": True}
                    text = await resp.text()
                    lines = text.strip().split("\n")
                    if len(lines) < 2:
                        return {"live": False, "series": series_id, "error": "empty csv", "real_data_only": True}
                    last = lines[-1]
                    return {"live": True, "series": series_id, "last_line": last, "rows": len(lines), "source": "FRED real-time pulling live", "real_data_only": True, "timestamp": datetime.utcnow().isoformat()}
        except Exception as e:
            return {"live": False, "series": series_id, "error": str(e), "real_data_only": True}

    async def test_live_async(self) -> dict:
        res = await self.fetch_series("DFF")
        return {"source": "fred", "live": res.get("live", False), "sample": res, "real_data_only": True, "no_synthetic": True}
