"""
S05: Options Open Interest Buildup — T-1 WEEK
Smart money building OI in options before price moves.
Free via yfinance option chain.
"""
from .base import BaseSignal, SignalResult
from hydra.data_sources.yahoo import YahooDataSource
import config
import logging
logger = logging.getLogger(__name__)

class OptionsOISignal(BaseSignal):
    name = "S05_OPTIONS_OI"
    timeframe = "1_week"
    lead_time = "3-7 days"
    weight = 1.0

    def __init__(self):
        super().__init__()
        self.yahoo = YahooDataSource()

    async def evaluate(self, instrument: str) -> SignalResult:
        yft = config.YF_TICKERS.get(instrument)
        if not yft:
            return self._make_result(instrument, 0, confidence=0.1, metadata={"error": "no ticker"})

        # Only certain tickers have options: SPX, BTC via proxies, etc.
        # We try, but if no options, return neutral
        try:
            chain = await self.yahoo.get_options_chain(yft)
            if not chain:
                return self._make_result(instrument, 0, confidence=0.2, metadata={"reason": "no options chain"})

            calls = chain.calls
            puts = chain.puts
            if calls.empty or puts.empty:
                return self._make_result(instrument, 0, confidence=0.2, metadata={"reason": "empty chain"})

            # Compute OI buildup: total OI calls vs puts
            call_oi = calls['openInterest'].sum() if 'openInterest' in calls else 0
            put_oi = puts['openInterest'].sum() if 'openInterest' in puts else 0
            total_oi = call_oi + put_oi
            if total_oi == 0:
                return self._make_result(instrument, 0, confidence=0.2, metadata={"reason": "zero OI"})

            # Put/Call ratio
            pcr = put_oi / (call_oi + 1e-10)

            # Unusual OI buildup: high OI far OTM? Check volume
            call_vol = calls['volume'].sum() if 'volume' in calls else 0
            put_vol = puts['volume'].sum() if 'volume' in puts else 0

            # Scoring: PCR low (<0.7) = bullish, high (>1.3) = bearish
            score = 0
            if pcr < 0.7:
                score = 40 + (0.7 - pcr)*50
            elif pcr > 1.3:
                score = -40 - (pcr - 1.3)*30

            # Volume surge adds
            if call_vol > call_oi * 0.1:
                score += 20 if score >=0 else -10
            if put_vol > put_oi * 0.1:
                score -= 20 if score <=0 else 10

            confidence = 0.6 if total_oi > 1000 else 0.4
            return self._make_result(instrument, max(-80, min(80, score)), confidence=confidence, metadata={
                "pcr": round(float(pcr),3),
                "call_oi": int(call_oi),
                "put_oi": int(put_oi),
                "call_vol": int(call_vol),
                "put_vol": int(put_vol)
            })
        except Exception as e:
            logger.debug(f"S05 {instrument}: {e}")
            return self._make_result(instrument, 0, confidence=0.1, metadata={"error": str(e)})
