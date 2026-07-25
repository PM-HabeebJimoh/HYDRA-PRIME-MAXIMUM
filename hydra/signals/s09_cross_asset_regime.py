"""
S09: Cross-Asset Regime Shift — T-48H
Bonds → FX → Metals shift detection
When bonds sell off, USDJPY typically rises, then gold reacts.
Detect regime via yield curve + DXY + SPX relationships.
"""
from .base import BaseSignal, SignalResult
from hydra.data_sources.yahoo import YahooDataSource
from hydra.data_sources.fred import FredDataSource
import config
import pandas as pd
import logging
logger = logging.getLogger(__name__)

class CrossAssetRegimeSignal(BaseSignal):
    name = "S09_REGIME_SHIFT"
    timeframe = "48h"
    lead_time = "1-3 days"
    weight = 1.3

    def __init__(self):
        super().__init__()
        self.yahoo = YahooDataSource()
        self.fred = FredDataSource()

    async def evaluate(self, instrument: str) -> SignalResult:
        try:
            # Fetch regime proxies: 10Y yield, DXY proxy via UUP? Actually ^TNX, SPX, DXY via DX-Y.NYB
            tickers = {"TNX": "^TNX", "SPX": "^GSPC", "DXY": "DX-Y.NYB", "VIX": "^VIX"}
            batch = await self.yahoo.fetch_batch(tickers, period="1mo", interval="1d")

            tnx = batch.get("TNX")
            spx = batch.get("SPX")
            dxy = batch.get("DXY")
            vix = batch.get("VIX")

            regime_score = 0
            meta = {}
            confidence = 0.4

            # TNX rising = risk-on, USDJPY bullish, Gold bearish
            if tnx is not None and not tnx.empty:
                tnx_close = tnx['Close'].dropna()
                if len(tnx_close) > 10:
                    ret_5d = float(tnx_close.pct_change(5).iloc[-1])
                    meta["tnx_5d"] = round(ret_5d,4)
                    if ret_5d > 0.03:  # >3% rise in yield over 5d
                        regime_score += 30
                        confidence = 0.65
                    elif ret_5d < -0.03:
                        regime_score -= 30
                        confidence = 0.65

            # DXY
            if dxy is not None and not dxy.empty:
                dxy_close = dxy['Close'].dropna()
                if len(dxy_close) > 10:
                    ret_5d = float(dxy_close.pct_change(5).iloc[-1])
                    meta["dxy_5d"] = round(ret_5d,4)
                    if "USD" in instrument:
                        # DXY up bullish for USD pairs? Actually EURUSD down when DXY up
                        if instrument.startswith("EUR") or instrument.startswith("GBP") or instrument.startswith("AUD") or "XAU" in instrument:
                            regime_score -= ret_5d*1000
                        else:
                            regime_score += ret_5d*1000

            # VIX spike = risk-off => USDJPY down, Gold up
            if vix is not None and not vix.empty:
                vix_close = vix['Close'].dropna()
                if len(vix_close) > 10:
                    curr_vix = float(vix_close.iloc[-1])
                    meta["vix"] = curr_vix
                    if curr_vix > 25:
                        # risk-off
                        if "JPY" in instrument or "XAU" in instrument or "XAG" in instrument:
                            regime_score += 20
                        elif instrument.startswith("AUD") or instrument.startswith("NZD"):
                            regime_score -= 20

            # Clamp and map to instrument
            score = max(-70, min(70, regime_score))

            # Adjust direction per instrument class
            final_score = score
            # Example inversion handled above, but keep generic
            if instrument in ["EURUSD","GBPUSD","AUDUSD","NZDUSD","XAUUSD","XAGUSD"]:
                final_score = -score if regime_score>0 and "USD" in str(meta) else score
                # Actually for gold: yield up = gold down, so score negative
                if tnx is not None and not tnx.empty:
                    if meta.get("tnx_5d",0) > 0.03 and "XAU" in instrument:
                        final_score = -abs(score)

            return self._make_result(instrument, final_score, confidence=confidence, metadata=meta)
        except Exception as e:
            logger.debug(f"S09 {instrument}: {e}")
            return self._make_result(instrument, 0, confidence=0.1, metadata={"error": str(e)})
