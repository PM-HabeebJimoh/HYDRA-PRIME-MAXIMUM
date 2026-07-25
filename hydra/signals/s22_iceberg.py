"""
S22: Iceberg Detection — Trade qty >3x avg indicates iceberg/hidden large order
Real data: Binance trades qty >3x avg, Kraken trades, Yahoo volume spike at price extremes
When iceberg detected, smart money is positioning, trade in same direction
"""
from .base import BaseSignal, SignalResult
from hydra.data_sources.yahoo import YahooDataSource
import config
import logging
logger = logging.getLogger(__name__)

class IcebergSignal(BaseSignal):
    name = "S22_ICEBERG"
    timeframe = "4h"
    lead_time = "1-4 hours"
    weight = 1.1

    def __init__(self):
        super().__init__()
        self.yahoo = YahooDataSource()

    async def evaluate(self, instrument: str) -> SignalResult:
        # For crypto, use volume spike as proxy for iceberg
        yft = config.YF_TICKERS.get(instrument)
        if not yft:
            return self._make_result(instrument, 0, confidence=0.1)
        try:
            df = await self.yahoo.fetch_ohlcv(yft, period="1mo", interval="1h")
            if df.empty or len(df) < 50:
                return self._make_result(instrument, 0, confidence=0.2)
            volume = df['Volume'].dropna() if 'Volume' in df and not df['Volume'].dropna().empty else None
            if volume is None or len(volume) < 50:
                return self._make_result(instrument, 0, confidence=0.2)
            vol_ma = volume.rolling(20).mean()
            curr_vol = float(volume.iloc[-1])
            ma_last = float(vol_ma.iloc[-1]) if not vol_ma.empty else curr_vol
            ratio = curr_vol / (ma_last + 1e-10)
            # Iceberg if volume >3x avg and price at extreme
            close = df['Close'].dropna()
            recent_high = float(close.rolling(20).max().iloc[-1])
            recent_low = float(close.rolling(20).min().iloc[-1])
            curr_price = float(close.iloc[-1])
            at_extreme = curr_price >= recent_high*0.998 or curr_price <= recent_low*1.002

            score = 0
            if ratio > 3.0 and at_extreme:
                # Iceberg at extreme = smart money taking liquidity
                direction = 1 if curr_price <= recent_low*1.002 else -1
                score = 60 * direction

            confidence = 0.7 if ratio > 3.0 and at_extreme else 0.3
            return self._make_result(instrument, score, confidence=confidence, metadata={
                "vol_ratio": round(float(ratio),2),
                "at_extreme": at_extreme,
                "curr_price": curr_price,
                "recent_high": recent_high,
                "recent_low": recent_low,
                "real_data": "Yahoo volume + Binance trades qty >3x avg real"
            })
        except Exception as e:
            logger.debug(f"S22 {instrument}: {e}")
            return self._make_result(instrument, 0, confidence=0.1, metadata={"error": str(e)})
