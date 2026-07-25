"""
GitHub commits — bitcoin/bitcoin repo — ONLY REAL LIVE DATA PULLING
No synthetic fallback
"""
import aiohttp
import logging
logger = logging.getLogger(__name__)
from datetime import datetime

class GithubDataSource:
    BASE = "https://api.github.com"

    async def get_commit_activity(self, repo: str = "bitcoin/bitcoin") -> dict:
        url = f"{self.BASE}/repos/{repo}/stats/commit_activity"
        headers = {"User-Agent": "HYDRA-PRIME-MAXIMUM"}
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        return {"live": False, "repo": repo, "error": f"status {resp.status}", "real_data_only": True}
                    data = await resp.json()
                    if not data or isinstance(data, dict):
                        return {"live": False, "repo": repo, "error": "no data or rate limit", "real_data_only": True}
                    total = sum(w.get("total",0) for w in data[-4:])
                    return {"live": True, "repo": repo, "last_4w_commits": total, "weeks": data[-4:], "source": "GitHub real-time pulling live", "real_data_only": True, "timestamp": datetime.utcnow().isoformat()}
        except Exception as e:
            return {"live": False, "repo": repo, "error": str(e), "real_data_only": True}

    async def test_live_async(self) -> dict:
        res = await self.get_commit_activity("bitcoin/bitcoin")
        return {"source": "github", "live": res.get("live", False), "real_data_only": True, "no_synthetic": True}
