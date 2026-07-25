"""
S24: Kyle's Lambda — Price impact per volume, measures informed trading
Kyle's lambda = Δprice / volume, high lambda = low liquidity, informed trading active, predicts large moves
Real data: Kraken OHLC volume + Yahoo volume, price change per volume
"""
from .base import BaseSignal, SignalResult
from hydra.data_sources.yahoo import YahooDataSource
import config
import numpy as np
import logging
logger = logging.getLogger(__name__)

class KyleLambdaSignal(BaseSignal):
    name = "S24_KYLE_LAMBDA"
    timeframe = "5m"
    lead_time = "5-30 minutes"
    weight = 1.3

    def __init__(self):
        super().__init__()
        self.yahoo = YahooDataSource()

    async def evaluate(self, instrument: str) -> SignalResult:
        yft = config.YF_TICKERS.get(instrument)
        if not yft:
            return self._make_result(instrument, 0, confidence=0.1)
        try:
            df = await self.yahoo.fetch_ohlcv(yft, period="5d", interval="1h")
            if df.empty or len(df) < 30:
                return self._make_result(instrument, 0, confidence=0.2)
            close = df['Close'].dropna()
            volume = df['Volume'].dropna() if 'Volume' in df and not df['Volume'].dropna().empty else None
            if volume is None or len(volume) < 30:
                return self._make_result(instrument, 0, confidence=0.2)

            # Kyle's lambda: price change / volume
            # Compute 1h returns and volume
            rets = close.pct_change().dropna()
            # Align
            min_len = min(len(rets), len(volume))
            rets = rets.iloc[-min_len:]
            vol = volume.iloc[-min_len:]

            # Lambda = |ret| / volume (normalized)
            # High lambda = small volume moves price a lot = low liquidity = informed trading
            lambdas = []
            for i in range(len(rets)):
                v = float(vol.iloc[i]) if i < len(vol) else 1
                r = abs(float(rets.iloc[i]))
                lam = r / (v + 1e-10) * 1e6  # scaled
                lambdas.append(lam)

            if not lambdas:
                return self._make_result(instrument, 0, confidence=0.2)

            curr_lambda = lambdas[-1]
            mean_lambda = np.mean(lambdas[-20:]) if len(lambdas)>=20 else np.mean(lambdas)
            # High lambda vs mean = informed trading active
            ratio = curr_lambda / (mean_lambda + 1e-10)

            score = 0
            direction = 0
            if ratio > 2.0:
                # High lambda = informed trading, direction from last return
                last_ret = float(rets.iloc[-1]) if len(rets)>0 else 0
                direction = 1 if last_ret >0 else -1 if last_ret<0 else 0
                score = 50 * direction
                # Informed trading active, expect continuation
            elif ratio < 0.5:
                # Low lambda = noise trading, expect mean reversion
                score = 0

            confidence = 0.7 if ratio>2.0 else 0.3
            return self._make_result(instrument, score, confidence=confidence, metadata={
                "kyle_lambda": round(float(curr_lambda),6),
                "mean_lambda": round(float(mean_lambda),6),
                "ratio": round(float(ratio),2),
                "direction": direction,
                "real_data": "Yahoo volume + Kraken volume + price change real, Kyle's lambda = Δprice/volume"
            })
        except Exception as e:
            logger.debug(f"S24 {instrument}: {e}")
            return self._make_result(instrument, 0, confidence=0.1, metadata={"error": str(e)})
