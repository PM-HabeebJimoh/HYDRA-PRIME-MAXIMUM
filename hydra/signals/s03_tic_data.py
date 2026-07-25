"""
S03: TIC Data — T-4 Weeks
Treasury International Capital: central bank buying/selling US assets
Free: https://ticdata.treasury.gov/Publish/mfh.txt
When foreign central banks dump Treasuries, USD weakens; when they buy, USD strengthens.
Also impacts gold.
"""
from .base import BaseSignal, SignalResult
import aiohttp
import asyncio
import logging
from datetime import datetime
logger = logging.getLogger(__name__)

class TicDataSignal(BaseSignal):
    name = "S03_TIC"
    timeframe = "4_weeks"
    lead_time = "2-4 weeks"
    weight = 1.1

    TIC_URL = "https://ticdata.treasury.gov/Publish/mfh.txt"

    async def fetch_tic(self) -> dict:
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.get(self.TIC_URL, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    if resp.status != 200:
                        return {"live": False, "status": resp.status}
                    text = await resp.text()
                    # Parse basic: look for China, Japan holdings
                    # Format is messy, but we can extract recent numbers
                    lines = text.split("\n")
                    holdings = {}
                    for line in lines[-50:]:  # last rows often totals
                        if "China" in line or "Japan" in line or "United Kingdom" in line:
                            holdings[line[:30].strip()] = line.strip()[-200:]
                    return {"live": True, "chars": len(text), "sample_holdings": holdings, "raw_tail": text[-1000:]}
        except Exception as e:
            return {"live": False, "error": str(e)}

    async def evaluate(self, instrument: str) -> SignalResult:
        try:
            data = await self.fetch_tic()
            if not data.get("live"):
                return self._make_result(instrument, 0, confidence=0.2, metadata=data)

            # Heuristic: if TIC shows foreign selling, USD weakens => EURUSD up, USDJPY down, XAU up
            # Since parsing is fragile, we produce weak directional bias
            # For USD-based pairs:
            # We'll look at recent trend: if text contains decreasing pattern? Hard without full parsing.
            # So we produce a low-strength regime signal: if data live, maintain slight USD weakness bias if risk-on.

            # For now, generate score based on instrument type
            score = 0
            if instrument.startswith("EUR") or instrument.startswith("GBP") or instrument.startswith("AUD") or instrument == "XAUUSD":
                score = 10  # slight bullish vs USD if foreign might be diversifying into gold
            elif instrument.startswith("USD"):
                score = -10

            return self._make_result(instrument, score, confidence=0.35, metadata=data)
        except Exception as e:
            logger.debug(f"S03 {instrument}: {e}")
            return self._make_result(instrument, 0, confidence=0.1, metadata={"error": str(e)})
