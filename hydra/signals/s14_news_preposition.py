"""
S14: News Event Pre-Positioning — T-30 MINUTES
GDELT surge detection before price moves.
Scheduled events: FOMC, ECB etc. Reaction takes 2-4h to complete. Trade continuation.
"""
from .base import BaseSignal, SignalResult
from hydra.data_sources.gdelt import GdeltDataSource
import config
import logging
logger = logging.getLogger(__name__)

class NewsPrepositionSignal(BaseSignal):
    name = "S14_NEWS_PREPOS"
    timeframe = "30m"
    lead_time = "15-30 minutes"
    weight = 1.2

    def __init__(self):
        super().__init__()
        self.gdelt = GdeltDataSource()

    async def evaluate(self, instrument: str) -> SignalResult:
        keyword = config.GDELT_KEYWORDS.get(instrument, instrument)
        try:
            surge = await self.gdelt.detect_news_surge(keyword)
            count = surge.get("count_24h", 0)
            tone = surge.get("avg_tone", 0)
            is_surge = surge.get("surge", False)

            # Also check central bank event keywords if applicable
            event_boost = 0
            for bank, info in config.CENTRAL_BANK_CALENDAR.items():
                if instrument in info["instruments"]:
                    # Check event keyword
                    ev = await self.gdelt.query_news(bank, timespan="24h", max_records=10)
                    if ev.get("count",0) > 5:
                        event_boost = 20
                        surge["central_bank_event"] = bank
                        break

            score = 0
            confidence = 0.3

            if is_surge:
                # Tone determines direction
                if tone > 0.5:
                    score = 30 + min(count*1.5, 50) + event_boost
                elif tone < -0.5:
                    score = -30 - min(count*1.5, 50) - event_boost
                else:
                    # High count but neutral tone = volatility expected, not direction
                    score = 0
                    surge["volatility_expected"] = True

                confidence = 0.65 if count > 20 else 0.5
                if event_boost > 0:
                    confidence = 0.75

            return self._make_result(instrument, max(-80, min(80, score)), confidence=confidence, metadata=surge)
        except Exception as e:
            logger.debug(f"S14 {instrument}: {e}")
            return self._make_result(instrument, 0, confidence=0.1, metadata={"error": str(e)})
