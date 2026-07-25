"""
Reddit — public API for sentiment — ONLY REAL LIVE DATA PULLING
No synthetic fallback
"""
import aiohttp
import logging
logger = logging.getLogger(__name__)
from datetime import datetime

class RedditDataSource:
    BASE = "https://www.reddit.com"

    async def get_subreddit_new(self, subreddit: str = "Bitcoin", limit: int = 10) -> dict:
        url = f"{self.BASE}/r/{subreddit}/new.json"
        params = {"limit": str(limit)}
        headers = {"User-Agent": "HYDRA-PRIME-MAXIMUM/1.0"}
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        return {"live": False, "subreddit": subreddit, "error": f"status {resp.status}", "real_data_only": True}
                    data = await resp.json()
                    posts = data.get("data", {}).get("children", [])
                    return {"live": True, "subreddit": subreddit, "count": len(posts), "posts": [{"title": p.get("data",{}).get("title"), "score": p.get("data",{}).get("score")} for p in posts[:5]], "source": "Reddit real-time pulling live", "real_data_only": True, "timestamp": datetime.utcnow().isoformat()}
        except Exception as e:
            return {"live": False, "subreddit": subreddit, "error": str(e), "real_data_only": True}

    async def test_live_async(self) -> dict:
        res = await self.get_subreddit_new("Bitcoin", 5)
        return {"source": "reddit", "live": res.get("live", False), "real_data_only": True, "no_synthetic": True}
