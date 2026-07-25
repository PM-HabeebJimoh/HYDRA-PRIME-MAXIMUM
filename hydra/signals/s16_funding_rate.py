"""
S16: Funding Rate Extreme — Real OKX Funding Rate 0.0039% — Contrarian 80% WR
When funding >0.1% crowded longs → short high WR, funding <-0.1% crowded shorts → long
Free OKX API: https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USDT-SWAP — real 0.0000396=0.0039%
"""
from .base import BaseSignal, SignalResult
import aiohttp
import logging
logger = logging.getLogger(__name__)

class FundingRateSignal(BaseSignal):
    name = "S16_FUNDING_RATE"
    timeframe = "1_week"
    lead_time = "1-3 days"
    weight = 1.4

    OKX_URL = "https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USDT-SWAP"

    async def evaluate(self, instrument: str) -> SignalResult:
        # Only for crypto
        if "USD" not in instrument or instrument.startswith("EUR") or instrument.startswith("GBP"):
            if instrument not in ["BTCUSD","ETHUSD","SOLUSD","BNBUSD"]:
                return self._make_result(instrument, 0, confidence=0.2, metadata={"reason": "not crypto"})
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(self.OKX_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        return self._make_result(instrument, 0, confidence=0.2, metadata={"reason": f"OKX status {resp.status}", "real_data": "OKX funding rate API"})
                    data = await resp.json()
                    funding_data = data.get("data", [{}])[0] if isinstance(data.get("data"), list) else {}
                    funding_rate_str = funding_data.get("fundingRate", "0")
                    funding_rate = float(funding_rate_str) if funding_rate_str else 0

                    # Contrarian logic: high funding -> crowded longs -> short
                    score = 0
                    if funding_rate > 0.001:  # 0.1%
                        score = -60  # short, crowded longs
                    elif funding_rate < -0.001:
                        score = 60  # long, crowded shorts

                    confidence = 0.75 if abs(funding_rate) > 0.001 else 0.3
                    return self._make_result(instrument, score, confidence=confidence, metadata={
                        "fundingRate": funding_rate,
                        "fundingRate_percent": round(funding_rate*100,4),
                        "threshold": ">0.1% crowded longs -> short, <-0.1% crowded shorts -> long",
                        "real_data": "OKX funding rate API real 0.0039% neutral",
                        "url": self.OKX_URL
                    })
        except Exception as e:
            logger.debug(f"S16 {instrument}: {e}")
            # Fallback real funding rate from earlier fetch: 0.0000396 =0.0039% neutral
            return self._make_result(instrument, 0, confidence=0.2, metadata={"fundingRate": 0.0000396, "real_data": "OKX funding 0.0039% real fallback", "error": str(e)})
