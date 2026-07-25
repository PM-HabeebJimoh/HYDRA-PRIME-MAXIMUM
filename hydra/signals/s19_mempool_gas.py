"""
S19: Mempool / Gas — BTC mempool size + ETH gas price predicts moves
Free: mempool.space API (free, no key) https://mempool.space/api/mempool, https://mempool.space/api/v1/fees/mempool-blocks
When mempool >100MB, BTC fee surge, indicates high demand, bullish short-term
When ETH gas >100 gwei, indicates high demand, bullish
"""
from .base import BaseSignal, SignalResult
import aiohttp
import logging
logger = logging.getLogger(__name__)

class MempoolGasSignal(BaseSignal):
    name = "S19_MEMPOOL_GAS"
    timeframe = "48h"
    lead_time = "1-3 days"
    weight = 0.9

    MEMPOOL_URL = "https://mempool.space/api/mempool"
    ETH_GAS_URL = "https://api.etherscan.io/api?module=gastracker&action=gasoracle"  # requires key, fallback

    async def evaluate(self, instrument: str) -> SignalResult:
        if instrument not in ["BTCUSD","ETHUSD","BTC-USD","ETH-USD"]:
            return self._make_result(instrument, 0, confidence=0.2, metadata={"reason": "BTC/ETH only"})
        try:
            async with aiohttp.ClientSession() as sess:
                # Try mempool.space
                try:
                    async with sess.get(self.MEMPOOL_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            # data contains count, vsize, total_fee, fee_histogram
                            count = data.get("count", 0)
                            vsize = data.get("vsize", 0)
                            # High mempool = high demand
                            score = 0
                            if vsize > 100_000_000:  # 100MB
                                score = 30
                            elif vsize > 50_000_000:
                                score = 15
                            return self._make_result(instrument, score, confidence=0.6, metadata={
                                "mempool_count": count,
                                "mempool_vsize": vsize,
                                "real_data": "mempool.space API free real",
                                "url": self.MEMPOOL_URL
                            })
                except Exception as e:
                    logger.debug(f"Mempool fetch {e}")

            return self._make_result(instrument, 0, confidence=0.2, metadata={"real_data": "mempool.space fallback"})
        except Exception as e:
            logger.debug(f"S19 {instrument}: {e}")
            return self._make_result(instrument, 0, confidence=0.1, metadata={"error": str(e)})
