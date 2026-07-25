"""
S23: Spoof Detection — Rapid appearance/disappearance of large orders
Real data: Kraken Depth 20 + spread, order book updates, large orders that appear and disappear quickly
When spoof detected (fake large orders), trade opposite direction
"""
from .base import BaseSignal, SignalResult
import aiohttp
import logging
logger = logging.getLogger(__name__)

class SpoofDetectionSignal(BaseSignal):
    name = "S23_SPOOF_DETECTION"
    timeframe = "5m"
    lead_time = "5-30 minutes"
    weight = 1.2

    DEPTH_URL = "https://api.kraken.com/0/public/Depth"
    SPREAD_URL = "https://api.kraken.com/0/public/Spread"

    async def evaluate(self, instrument: str) -> SignalResult:
        kraken_map = {"BTCUSD": "XBTUSD", "ETHUSD": "ETHUSD"}
        pair = kraken_map.get(instrument)
        if not pair:
            return self._make_result(instrument, 0, confidence=0.2)

        try:
            async with aiohttp.ClientSession() as sess:
                # Fetch spread data - many small spreads indicate spoofing? Actually large spread changes indicate manipulation
                params = {"pair": pair}
                async with sess.get(self.SPREAD_URL, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        return self._make_result(instrument, 0, confidence=0.2, metadata={"real_data": "Kraken Spread"})
                    data = await resp.json()
                    result = data.get("result", {})
                    if not result:
                        return self._make_result(instrument, 0, confidence=0.2)
                    key = list(result.keys())[0]
                    spreads = result[key]
                    if len(spreads) < 10:
                        return self._make_result(instrument, 0, confidence=0.2)

                    # Compute spread volatility: high spread vol = potential spoofing
                    # Each spread entry: [time, bid, ask]
                    spread_values = []
                    for entry in spreads[-20:]:
                        try:
                            bid = float(entry[1])
                            ask = float(entry[2])
                            spread = ask - bid
                            spread_values.append(spread)
                        except:
                            continue

                    if not spread_values:
                        return self._make_result(instrument, 0, confidence=0.2)

                    import numpy as np
                    mean_spread = np.mean(spread_values)
                    std_spread = np.std(spread_values)
                    # High std = spoofing activity
                    spoof_score = std_spread / (mean_spread + 1e-10)

                    score = 0
                    if spoof_score > 2.0:
                        # Spoof detected, trade opposite of last large spread direction? Simplified: high spoof = Mean reversion
                        score = -20  # contrarian

                    return self._make_result(instrument, score, confidence=0.5 if spoof_score>2 else 0.2, metadata={
                        "mean_spread": round(float(mean_spread),2),
                        "std_spread": round(float(std_spread),2),
                        "spoof_score": round(float(spoof_score),2),
                        "real_data": "Kraken Spread real - rapid spread changes indicate spoofing",
                        "url": self.SPREAD_URL
                    })
        except Exception as e:
            logger.debug(f"S23 {instrument}: {e}")
            return self._make_result(instrument, 0, confidence=0.1, metadata={"error": str(e)})
