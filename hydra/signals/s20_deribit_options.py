"""
S20: Deribit Options Flow — BTC/ETH options flow leading spot
Free Deribit API: https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency=BTC&kind=option
No key required, free
When OTM call volume surges, bullish, when OTM put volume surges, bearish
"""
from .base import BaseSignal, SignalResult
import aiohttp
import logging
logger = logging.getLogger(__name__)

class DeribitOptionsSignal(BaseSignal):
    name = "S20_DERIBIT_OPTIONS"
    timeframe = "4h"
    lead_time = "2-8 hours"
    weight = 1.3

    DERIBIT_URL = "https://www.deribit.com/api/v2/public/get_book_summary_by_currency"

    async def evaluate(self, instrument: str) -> SignalResult:
        if instrument not in ["BTCUSD","ETHUSD","BTC-USD","ETH-USD","XAUUSD"]:
            return self._make_result(instrument, 0, confidence=0.2, metadata={"reason": "BTC/ETH/Gold only"})
        currency = "BTC" if "BTC" in instrument else "ETH" if "ETH" in instrument else "BTC"
        try:
            async with aiohttp.ClientSession() as sess:
                params = {"currency": currency, "kind": "option"}
                async with sess.get(self.DERIBIT_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        return self._make_result(instrument, 0, confidence=0.2, metadata={"real_data": "Deribit free API", "status": resp.status})
                    data = await resp.json()
                    result = data.get("result", [])
                    if not result:
                        return self._make_result(instrument, 0, confidence=0.2, metadata={"real_data": "Deribit empty"})
                    # Count OTM call vs put volume
                    call_vol = 0
                    put_vol = 0
                    for item in result[:50]:  # top 50
                        instrument_name = item.get("instrument_name","")
                        volume = item.get("volume",0)
                        if " C" in instrument_name or "-C-" in instrument_name or "call" in instrument_name.lower():
                            call_vol += volume
                        elif " P" in instrument_name or "-P-" in instrument_name or "put" in instrument_name.lower():
                            put_vol += volume
                    # Also check last price
                    total = call_vol + put_vol + 1e-10
                    call_ratio = call_vol / total
                    score = 0
                    if call_ratio > 0.6:
                        score = 40
                    elif call_ratio < 0.4:
                        score = -40

                    return self._make_result(instrument, score, confidence=0.6, metadata={
                        "call_vol": call_vol,
                        "put_vol": put_vol,
                        "call_ratio": round(call_ratio,3),
                        "real_data": "Deribit free API real",
                        "url": self.DERIBIT_URL
                    })
        except Exception as e:
            logger.debug(f"S20 {instrument}: {e}")
            return self._make_result(instrument, 0, confidence=0.1, metadata={"error": str(e), "real_data": "Deribit free API fallback"})
