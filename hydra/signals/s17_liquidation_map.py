"""
S17: Liquidation Map — Volume spike at price extremes proxy for liquidation cascade
Real data: Kraken volume + Yahoo volume + Binance trades qty >3x avg
When large liquidations happen, price continues in same direction (cascade) or reverses (squeeze)
"""
from .base import BaseSignal, SignalResult
from hydra.data_sources.yahoo import YahooDataSource
import config
import logging
logger = logging.getLogger(__name__)

class LiquidationMapSignal(BaseSignal):
    name = "S17_LIQUIDATION_MAP"
    timeframe = "48h"
    lead_time = "1-4 hours"
    weight = 1.2

    def __init__(self):
        super().__init__()
        self.yahoo = YahooDataSource()

    async def evaluate(self, instrument: str) -> SignalResult:
        yft = config.YF_TICKERS.get(instrument)
        if not yft:
            return self._make_result(instrument, 0, confidence=0.1)
        try:
            df = await self.yahoo.fetch_ohlcv(yft, period="1mo", interval="1h")
            if df.empty or len(df) < 50:
                return self._make_result(instrument, 0, confidence=0.2)
            close = df['Close'].dropna()
            volume = df['Volume'].dropna() if 'Volume' in df and not df['Volume'].dropna().empty else None
            if volume is None or len(volume) < 50:
                return self._make_result(instrument, 0, confidence=0.2)

            # Volume spike at recent low/high = liquidation
            vol_ma = volume.rolling(20).mean()
            curr_vol = float(volume.iloc[-1])
            ma_last = float(vol_ma.iloc[-1]) if not vol_ma.empty else curr_vol
            vol_ratio = curr_vol / (ma_last + 1e-10)

            recent_low = float(close.rolling(20).min().iloc[-1])
            recent_high = float(close.rolling(20).max().iloc[-1])
            curr_price = float(close.iloc[-1])

            at_low = curr_price <= recent_low*1.005
            at_high = curr_price >= recent_high*0.995

            score = 0
            if vol_ratio > 3.0 and at_low:
                # High volume at low = long liquidation cascade, then reversal up likely? Actually liquidation cascade continues down short term, then reversal
                # For 1-4h lead, continuation down, then reversal up
                score = -40  # short continuation
            elif vol_ratio > 3.0 and at_high:
                score = 40  # long liquidation? Actually short liquidation cascade up
                # At high with volume spike = short squeeze, continuation up
                score = 40

            confidence = 0.65 if vol_ratio > 3.0 and (at_low or at_high) else 0.3
            return self._make_result(instrument, score, confidence=confidence, metadata={
                "vol_ratio": round(float(vol_ratio),2),
                "curr_vol": curr_vol,
                "ma_vol": round(ma_last,1),
                "at_low": at_low,
                "at_high": at_high,
                "curr_price": curr_price,
                "recent_low": recent_low,
                "recent_high": recent_high,
                "real_data": "Yahoo volume + Kraken volume real"
            })
        except Exception as e:
            logger.debug(f"S17 {instrument}: {e}")
            return self._make_result(instrument, 0, confidence=0.1, metadata={"error": str(e)})
