"""
S10: Volatility Squeeze — T-4H
Physics: When volatility compresses to extreme lows, it MUST expand. Mean reversion of vol is most robust.
Buy when BB percentile <5% -> explosion loading.
"""
from .base import BaseSignal, SignalResult
from .helpers import compute_bollinger_bands, safe_last
from hydra.data_sources.yahoo import YahooDataSource
import config
import pandas as pd
import numpy as np
import logging
logger = logging.getLogger(__name__)

class VolatilitySqueezeSignal(BaseSignal):
    name = "S10_VOL_SQUEEZE"
    timeframe = "4h"
    lead_time = "2-8 hours"
    weight = 1.2

    def __init__(self):
        super().__init__()
        self.yahoo = YahooDataSource()

    async def evaluate(self, instrument: str) -> SignalResult:
        yft = config.YF_TICKERS.get(instrument)
        if not yft:
            return self._make_result(instrument, 0, confidence=0.1)

        try:
            df = await self.yahoo.fetch_ohlcv(yft, period="1y", interval="1d")
            if df.empty or len(df) < 60:
                return self._make_result(instrument, 0, confidence=0.2, metadata={"reason": "insufficient"})

            close = df['Close'].dropna()
            sma20, upper, lower, bw = compute_bollinger_bands(close, 20, 2)
            bw_curr = safe_last(bw)
            if bw_curr is None:
                return self._make_result(instrument, 0, confidence=0.2)

            # BB percentile vs 1y
            bw_series = bw.dropna()
            if len(bw_series) < 50:
                return self._make_result(instrument, 0, confidence=0.2)
            percentile = float((bw_series <= bw_curr).mean() * 100)

            # HV ratio 5d vs 20d
            returns = close.pct_change()
            hv5 = returns.rolling(5).std() * np.sqrt(252)
            hv20 = returns.rolling(20).std() * np.sqrt(252)
            hv5_last = safe_last(hv5)
            hv20_last = safe_last(hv20)
            hv_ratio = (hv5_last / (hv20_last + 1e-10)) if hv5_last and hv20_last else 1.0

            # Squeeze detection
            extreme_compression = percentile < 10 and hv_ratio < 0.5
            moderate_compression = percentile < 25 and hv_ratio < 0.8

            score = 0
            confidence = 0.3
            setup_quality = "NONE"

            if extreme_compression:
                score = 80
                setup_quality = "ELITE" if percentile < 3 else "STRONG"
                confidence = 0.85
            elif moderate_compression:
                score = 40
                setup_quality = "GOOD"
                confidence = 0.55
            elif percentile < 40:
                score = 15
                setup_quality = "WATCH"
                confidence = 0.35

            # Also detect expansion already starting - if bw rising quickly, confirm
            bw_change_3d = float(bw.pct_change(3).iloc[-1]) if len(bw)>3 else 0
            if bw_change_3d > 0.1 and percentile < 30:
                score += 20  # explosion already starting
                confidence = max(confidence, 0.7)

            # Direction? Squeeze itself doesn't give direction, but we combine with trend
            # Use close vs sma20 to estimate explosion direction bias
            sma20_last = safe_last(sma20)
            direction_bias = 0
            if sma20_last:
                if float(close.iloc[-1]) > sma20_last:
                    direction_bias = 1
                else:
                    direction_bias = -1
            # Score is always positive magnitude for vol explosion, but we attach direction bias in metadata
            final_score = score * (direction_bias if direction_bias!=0 else 1)

            return self._make_result(
                instrument,
                final_score,
                confidence=confidence,
                metadata={
                    "bb_percentile": round(percentile,1),
                    "bw": round(bw_curr,5),
                    "hv_ratio": round(hv_ratio,3),
                    "hv5": round(hv5_last,4) if hv5_last else None,
                    "hv20": round(hv20_last,4) if hv20_last else None,
                    "setup_quality": setup_quality,
                    "bw_change_3d": round(bw_change_3d,3),
                    "direction_bias": direction_bias,
                    "type": "VOL_EXPLOSION"
                }
            )
        except Exception as e:
            logger.debug(f"S10 {instrument}: {e}")
            return self._make_result(instrument, 0, confidence=0.1, metadata={"error": str(e)})
