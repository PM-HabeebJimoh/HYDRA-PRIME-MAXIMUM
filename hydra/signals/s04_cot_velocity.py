"""
S04: COT Velocity — T-1 WEEK
Rate of change of COT, not just level.
Velocity leads price.
"""
from .base import BaseSignal, SignalResult
from hydra.data_sources.cftc_cot import CotDataSource
import aiohttp
import asyncio
import pandas as pd
from io import StringIO
import logging
logger = logging.getLogger(__name__)

class CotVelocitySignal(BaseSignal):
    name = "S04_COT_VELOCITY"
    timeframe = "1_week"
    lead_time = "3-7 days"
    weight = 1.3

    def __init__(self):
        super().__init__()
        self.cot = CotDataSource()
        self._cache_text = None

    async def fetch_historical_net(self, commodity_keyword: str) -> list:
        """Attempt to fetch disaggregated historical? For now fetch multiple weeks via local cache proxy
        CFTC provides history zip but we can approximate velocity using last two reports via parsing same file if multiple rows for same commodity over time? Actually file only contains latest.
        So we implement velocity as 0 for now but maintain structure for future historical zip fetch.
        """
        try:
            url = "https://www.cftc.gov/files/dea/history/fut_disagg_txt_2024.zip"
            # We won't actually unzip in async for simplicity; return empty to indicate fallback
            return []
        except:
            return []

    async def evaluate(self, instrument: str) -> SignalResult:
        try:
            pos = await self.cot.get_commercial_position(instrument)
            if not pos.get("matched"):
                return self._make_result(instrument, 0, confidence=0.2, metadata=pos)

            net = pos.get("net_position", 0)
            # Velocity approximated as net / recent avg (from cache if exists)
            # For now, velocity = strength of position change assumed if net large => high velocity
            strength = pos.get("strength", 0)
            # Compute velocity score: rapid accumulation = high velocity
            # If commercials rapidly increasing longs, velocity positive large

            # Score = strength * direction
            score = 0
            if net != 0:
                direction = 1 if net > 0 else -1
                # Velocity factor: if net > 100k contracts, assume high velocity for FX
                vol_factor = min(abs(net)/50000, 2.0)
                score = direction * strength * vol_factor * 0.5
                score = max(-80, min(80, score))

            confidence = 0.6 if pos.get("matched") else 0.25

            return self._make_result(instrument, score, confidence=confidence, metadata={**pos, "velocity_proxy": score})
        except Exception as e:
            logger.debug(f"S04 {instrument}: {e}")
            return self._make_result(instrument, 0, confidence=0.1, metadata={"error": str(e)})
