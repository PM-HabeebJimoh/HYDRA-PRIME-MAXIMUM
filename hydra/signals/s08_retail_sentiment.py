"""
S08: Retail Sentiment — Wikipedia + Google Trends spike
T-48H: When gold's Wikipedia page spikes 3x, retail is about to buy.
Also Reddit + Google Trends.
"""
from .base import BaseSignal, SignalResult
from hydra.data_sources.wikipedia import WikipediaDataSource
from hydra.data_sources.reddit import RedditDataSource
import config
import logging
logger = logging.getLogger(__name__)

class RetailSentimentSignal(BaseSignal):
    name = "S08_RETAIL_SENTIMENT"
    timeframe = "48h"
    lead_time = "24-72 hours"
    weight = 1.0

    def __init__(self):
        super().__init__()
        self.wiki = WikipediaDataSource()
        self.reddit = RedditDataSource()

    async def evaluate(self, instrument: str) -> SignalResult:
        try:
            wiki_article = config.WIKI_ARTICLES.get(instrument)
            wiki_res = None
            if wiki_article:
                wiki_res = await self.wiki.get_pageviews(wiki_article, days=14)

            reddit_res = await self.reddit.get_sentiment()

            score = 0
            meta = {}
            confidence = 0.3

            if wiki_res and wiki_res.get("live"):
                meta["wiki"] = wiki_res
                if wiki_res.get("spike"):
                    # Spike = retail about to buy = bullish in short term, but contrarian longer?
                    # For T-48h, spike predicts immediate retail inflow -> bullish momentum
                    ratio = wiki_res.get("spike_ratio", 1)
                    score += 40 + min((ratio-2)*20, 40)
                    confidence = 0.65
                else:
                    # No spike, neutral
                    score += 0

            if reddit_res and reddit_res.get("live"):
                sent = reddit_res.get("sentiment", {}).get(instrument)
                if sent:
                    meta["reddit"] = sent
                    if sent.get("surge"):
                        score += 20
                        confidence = max(confidence, 0.6)

            # Try Google Trends via pytrends if available (optional)
            try:
                # Import lazily
                from pytrends.request import TrendReq
                # This can be rate-limited, so we only do for major instruments and with low timeout
                # Skip for now to avoid blocking; mark as attempt
                meta["gtrends"] = "skipped - rate limit protection"
            except ImportError:
                meta["gtrends"] = "pytrends not installed"

            # Cap score
            score = max(-70, min(70, score))
            return self._make_result(instrument, score, confidence=confidence, metadata=meta)
        except Exception as e:
            logger.debug(f"S08 {instrument}: {e}")
            return self._make_result(instrument, 0, confidence=0.1, metadata={"error": str(e)})
