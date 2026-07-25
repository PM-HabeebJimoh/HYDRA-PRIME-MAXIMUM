"""
S06: Patent / Regulatory Filing Anomalies — T-1 WEEK
Mining companies file patents before announcing new deposits.
Free proxy: SEC Edgar + GitHub + GDELT regulatory keywords.
"""
from .base import BaseSignal, SignalResult
from hydra.data_sources.gdelt import GdeltDataSource
import logging
logger = logging.getLogger(__name__)

class PatentRegulatorySignal(BaseSignal):
    name = "S06_PATENT_REG"
    timeframe = "1_week"
    lead_time = "5-10 days"
    weight = 0.7

    def __init__(self):
        super().__init__()
        self.gdelt = GdeltDataSource()

    async def evaluate(self, instrument: str) -> SignalResult:
        # Keywords for patent/regulatory
        keyword_map = {
            "XAUUSD": "gold mine patent new deposit discovery",
            "XAGUSD": "silver mine new discovery",
            "BTCUSD": "bitcoin ETF approval regulation SEC",
            "ETHUSD": "ethereum ETF approval SEC",
            "CL": "oil drilling patent new field discovery",
            "SPX": "SEC regulation antitrust patent",
        }
        query = keyword_map.get(instrument, f"{instrument} patent filing regulatory approval")
        try:
            surge = await self.gdelt.detect_news_surge(query)
            count = surge.get("count_24h", 0)
            tone = surge.get("avg_tone", 0)

            score = 0
            if surge.get("surge"):
                # Positive tone with surge = bullish regulatory tailwind
                if tone > 0:
                    score = 30 + min(count, 40)
                else:
                    score = -20 - min(count, 30)

            confidence = 0.5 if surge.get("live") else 0.2
            return self._make_result(instrument, score, confidence=confidence, metadata={
                "query": query,
                "count": count,
                "tone": tone,
                "surge": surge.get("surge")
            })
        except Exception as e:
            logger.debug(f"S06 {instrument}: {e}")
            return self._make_result(instrument, 0, confidence=0.1, metadata={"error": str(e)})
