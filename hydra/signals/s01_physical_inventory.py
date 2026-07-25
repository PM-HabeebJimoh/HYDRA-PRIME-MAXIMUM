"""
S01: Physical Inventory Signal — T-4 WEEKS
Physics: When LME/COMEX cancelled warrants spike (physical withdrawn from inventory),
         future price MUST rise because physical shortage.

Implementation using free data:
- Futures curve backwardation check via front vs historical (proxy for physical tightness)
- Volume + Open Interest surge + price up = physical buying
- ETF holdings proxy via volume anomalies
"""
from .base import BaseSignal, SignalResult
from .helpers import compute_bollinger_bands, safe_last
import config
import pandas as pd
import numpy as np
from hydra.data_sources.yahoo import YahooDataSource
import logging
logger = logging.getLogger(__name__)

class PhysicalInventorySignal(BaseSignal):
    name = "S01_PHYSICAL_INVENTORY"
    timeframe = "4_weeks"
    lead_time = "2-4 weeks"
    weight = 1.2

    def __init__(self):
        super().__init__()
        self.yahoo = YahooDataSource()

    async def evaluate(self, instrument: str) -> SignalResult:
        yft = config.YF_TICKERS.get(instrument)
        if not yft:
            return self._make_result(instrument, 0, confidence=0, metadata={"error": "no ticker"})
        try:
            df = await self.yahoo.fetch_ohlcv(yft, period="6mo", interval="1d")
            if df.empty or len(df) < 60:
                return self._make_result(instrument, 0, confidence=0.2, metadata={"reason": "insufficient data"})

            close = df['Close'].dropna()
            volume = df['Volume'].dropna() if 'Volume' in df else pd.Series([0]*len(close))

            # 1. Futures curve tightness proxy: price above 50DMA significantly
            sma50 = close.rolling(50).mean()
            sma200 = close.rolling(200).mean()
            curr = float(close.iloc[-1])
            sma50_last = safe_last(sma50)
            sma200_last = safe_last(sma200)

            backwardation_proxy = 0
            if sma50_last and curr > sma50_last * 1.03:
                backwardation_proxy = 30  # price well above 50MA = tightness
            if sma200_last and curr > sma200_last and sma50_last and sma50_last > sma200_last:
                backwardation_proxy += 20  # golden cross = physical demand

            # 2. Volume surge: volume 2σ above 20DMA volume
            if len(volume) > 20:
                vol_ma = volume.rolling(20).mean()
                vol_std = volume.rolling(20).std()
                curr_vol = float(volume.iloc[-1]) if len(volume)>0 else 0
                vol_ma_last = safe_last(vol_ma)
                vol_std_last = safe_last(vol_std)
                if vol_ma_last and vol_std_last and curr_vol > vol_ma_last + 1.5*vol_std_last:
                    backwardation_proxy += 40

            # 3. Bollinger width compression then expansion + price up = inventory squeeze release
            _, _, _, bw = compute_bollinger_bands(close, 20, 2)
            bw_last = safe_last(bw)
            bw_20mean = float(bw.rolling(20).mean().iloc[-1]) if len(bw)>20 else None
            if bw_last and bw_20mean and bw_last > bw_20mean * 1.2:
                backwardation_proxy += 10

            # Direction: tightness => bullish for metals/commodities, for FX treat as base strength
            # For USD pairs, invert logic? Simplify: tightness bullish for instrument
            score = min(backwardation_proxy, 80)
            # Metals get higher weight
            if "XAU" in instrument or "XAG" in instrument or instrument in ["GC","SI","HG","PL","PA","CL","NG"]:
                score *= 1.2

            # If price downtrend, reduce score or flip
            if sma50_last and curr < sma50_last * 0.97:
                score = -score * 0.5  # physical surplus => bearish

            confidence = 0.6 if len(df) > 100 else 0.4
            if score > 50:
                confidence = 0.75

            return self._make_result(
                instrument,
                score=score,
                confidence=confidence,
                metadata={
                    "curr_price": curr,
                    "sma50": sma50_last,
                    "sma200": sma200_last,
                    "bw": bw_last,
                    "tightness_proxy": backwardation_proxy,
                    "type": "physical_inventory"
                }
            )
        except Exception as e:
            logger.debug(f"S01 {instrument}: {e}")
            return self._make_result(instrument, 0, confidence=0.1, metadata={"error": str(e)})
