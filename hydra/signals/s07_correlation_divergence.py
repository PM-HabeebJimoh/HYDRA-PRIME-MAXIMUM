"""
S07: Correlation Divergence — T-48 HOURS
When correlated instruments diverge, they must revert. Must-revert physics.
"""
from .base import BaseSignal, SignalResult
from .helpers import compute_zscore, safe_last
from hydra.data_sources.yahoo import YahooDataSource
import config
import pandas as pd
import logging
logger = logging.getLogger(__name__)

class CorrelationDivergenceSignal(BaseSignal):
    name = "S07_CORR_DIVERG"
    timeframe = "48h"
    lead_time = "24-48 hours"
    weight = 1.2

    # Predefined correlated clusters
    CORRELATED_PAIRS = {
        "XAUUSD": ["XAGUSD", "SPX", "TNX"], # Gold vs Silver, vs SPX, vs 10Y yield proxy
        "EURUSD": ["GBPUSD", "AUDUSD", "SPX"],
        "USDJPY": ["TNX", "SPX", "N225"],
        "AUDUSD": ["HG", "CL", "SPX"],
        "BTCUSD": ["ETHUSD", "SOLUSD", "SPX"],
        "CL": ["HG", "SPX", "USDCAD"],
        "SPX": ["NDX", "DJI", "BTCUSD"],
    }

    def __init__(self):
        super().__init__()
        self.yahoo = YahooDataSource()

    async def evaluate(self, instrument: str) -> SignalResult:
        correlates = self.CORRELATED_PAIRS.get(instrument, [])
        # Add generic fallback: if no mapping, compare to SPX and Gold
        if not correlates:
            if instrument.startswith("EUR") or instrument.startswith("GBP"):
                correlates = ["EURUSD", "GBPUSD", "SPX"]
            elif "USD" in instrument and instrument != "BTCUSD":
                correlates = ["SPX", "TNX"]
            else:
                correlates = ["SPX", "BTCUSD"]

        yft_main = config.YF_TICKERS.get(instrument)
        if not yft_main:
            return self._make_result(instrument, 0, confidence=0.1, metadata={"error": "no ticker"})

        try:
            # Fetch main
            df_main = await self.yahoo.fetch_ohlcv(yft_main, period="3mo", interval="1d")
            if df_main.empty or len(df_main) < 30:
                return self._make_result(instrument, 0, confidence=0.2, metadata={"reason": "insufficient data"})

            close_main = df_main['Close'].dropna()
            main_ret_5d = float(close_main.pct_change(5).iloc[-1]) if len(close_main)>5 else 0

            divergences = []
            total_score = 0

            # Fetch correlates in parallel
            tickers = {c: config.YF_TICKERS.get(c, c) for c in correlates if config.YF_TICKERS.get(c)}
            if not tickers:
                return self._make_result(instrument, 0, confidence=0.2, metadata={"reason": "no correlates"})

            batch = await self.yahoo.fetch_batch(tickers, period="3mo", interval="1d")

            for corr_inst, df_corr in batch.items():
                if df_corr.empty or len(df_corr)<30:
                    continue
                close_corr = df_corr['Close'].dropna()
                # Align last dates
                # Compute correlation over 21 days
                try:
                    # Align lengths
                    min_len = min(len(close_main), len(close_corr))
                    a = close_main.iloc[-min_len:]
                    b = close_corr.iloc[-min_len:]
                    # Compute rolling correlation
                    corr_21 = a.rolling(21).corr(b)
                    corr_curr = safe_last(corr_21)
                    if corr_curr is None:
                        continue
                    mean_corr = float(corr_21.rolling(90).mean().iloc[-1]) if len(corr_21)>90 else 0.5
                    # If historically correlated (>0.6) but recent return diverged
                    corr_ret_5d = float(b.pct_change(5).iloc[-1]) if len(b)>5 else 0
                    return_diff = main_ret_5d - corr_ret_5d

                    # High historical corr but large return diff = divergence
                    if abs(mean_corr) > 0.6 and abs(return_diff) > 0.02:
                        # Expect reversion: if main underperformed vs correlated, bullish for main
                        score = return_diff * -1000  # invert, magnify
                        score = max(-60, min(60, score))
                        divergences.append({"pair": corr_inst, "corr": round(corr_curr,2), "mean_corr": round(mean_corr,2), "ret_diff": round(return_diff,4), "score": round(score,1)})
                        total_score += score
                except Exception as e:
                    logger.debug(f"S07 divergence {instrument}-{corr_inst}: {e}")
                    continue

            if not divergences:
                return self._make_result(instrument, 0, confidence=0.3, metadata={"reason": "no divergence"})

            avg_score = total_score / len(divergences)
            confidence = 0.65 if len(divergences)>=2 else 0.45
            return self._make_result(instrument, avg_score, confidence=confidence, metadata={"divergences": divergences, "main_5d_ret": round(main_ret_5d,4)})
        except Exception as e:
            logger.debug(f"S07 {instrument}: {e}")
            return self._make_result(instrument, 0, confidence=0.1, metadata={"error": str(e)})
