"""
S13: Cross-Asset Temporal Lead — T-30 MINUTES
Crypto/futures lead FX.
Real physics: BTC leads risk sentiment, bond futures lead FX.
When crypto surges 5% but EURUSD hasn't moved, EURUSD will follow within 30-60 min.
"""
from .base import BaseSignal, SignalResult
from hydra.data_sources.yahoo import YahooDataSource
from hydra.data_sources.binance import BinanceDataSource
import config
import pandas as pd
import logging
logger = logging.getLogger(__name__)

class CrossAssetLeadSignal(BaseSignal):
    name = "S13_CROSS_LEAD"
    timeframe = "30m"
    lead_time = "15-60 minutes"
    weight = 1.5

    # Lead-lag relationships empirically documented
    LEAD_MAP = {
        "EURUSD": ["BTCUSD", "SPX", "TNX"],  # BTC up => risk-on => EURUSD up
        "GBPUSD": ["EURUSD", "SPX", "BTCUSD"],
        "USDJPY": ["TNX", "SPX", "N225"],  # TNX up => USDJPY up
        "AUDUSD": ["BTCUSD", "SPX", "HG", "CL"],
        "XAUUSD": ["BTCUSD", "TNX", "DXY"], # Crypto up + yields down => gold up
        "XAGUSD": ["XAUUSD", "BTCUSD", "HG"],
        "BTCUSD": ["SPX", "NDX"],  # SPX leads BTC slightly in some regimes
        "SPX": ["TNX", "VIX"],  # Bonds lead stocks
        "CL": ["SPX", "USDCAD"],
        "HG": ["SPX", "AUDUSD", "BTCUSD"],
    }

    def __init__(self):
        super().__init__()
        self.yahoo = YahooDataSource()
        self.binance = BinanceDataSource()

    async def evaluate(self, instrument: str) -> SignalResult:
        leaders = self.LEAD_MAP.get(instrument, ["SPX", "BTCUSD", "TNX"])
        yft_target = config.YF_TICKERS.get(instrument)
        if not yft_target:
            return self._make_result(instrument, 0, confidence=0.1)

        try:
            # Fetch target 1h data last few days to get recent move
            df_target = await self.yahoo.fetch_ohlcv(yft_target, period="5d", interval="1h")
            if df_target.empty:
                return self._make_result(instrument, 0, confidence=0.2)

            # Compute target's 4h return
            close_target = df_target['Close'].dropna()
            if len(close_target) < 5:
                return self._make_result(instrument, 0, confidence=0.2)
            target_ret_4h = float(close_target.pct_change(4).iloc[-1])

            # Fetch leaders
            leader_tickers = {lead: config.YF_TICKERS.get(lead, lead) for lead in leaders if config.YF_TICKERS.get(lead)}
            batch = await self.yahoo.fetch_batch(leader_tickers, period="5d", interval="1h")

            lead_signals = []
            total_lead_score = 0

            for lead_inst, df_lead in batch.items():
                if df_lead.empty or len(df_lead) < 5:
                    continue
                close_lead = df_lead['Close'].dropna()
                lead_ret_4h = float(close_lead.pct_change(4).iloc[-1]) if len(close_lead)>4 else 0

                # Lead detection: if leader moved significantly (>0.5%) but target hasn't (<0.2%)
                # Then expect target to catch up
                if abs(lead_ret_4h) > 0.005 and abs(target_ret_4h) < 0.002:
                    # Leader up 0.5%+, target flat => bullish for target if positively correlated
                    # Correlation assumption: BTC -> EURUSD positive, TNX -> USDJPY positive, etc.
                    correlation_positive = True
                    # Specific cases: TNX vs XAUUSD negative
                    if instrument in ["XAUUSD","XAGUSD"] and lead_inst == "TNX":
                        correlation_positive = False
                    if instrument in ["EURUSD","GBPUSD"] and lead_inst == "TNX" and lead_ret_4h>0:
                        # Yields up often USD up = EURUSD down
                        correlation_positive = False

                    expected_dir = 1 if (lead_ret_4h>0 and correlation_positive) or (lead_ret_4h<0 and not correlation_positive) else -1
                    magnitude = min(abs(lead_ret_4h)*1000, 60)  # 0.5% => 5 points *? scale to 0-60
                    # Actually amplify: 0.5% move * 1000 = 5, we want bigger -> *2000
                    magnitude = min(abs(lead_ret_4h)*2000, 70)

                    score = magnitude * expected_dir
                    lead_signals.append({
                        "leader": lead_inst,
                        "lead_ret_4h": round(lead_ret_4h,4),
                        "target_ret_4h": round(target_ret_4h,4),
                        "expected_dir": expected_dir,
                        "score": round(score,1)
                    })
                    total_lead_score += score

            if not lead_signals:
                # Check for same-direction momentum: leader and target both moving but leader leading by larger magnitude
                for lead_inst, df_lead in batch.items():
                    if df_lead.empty:
                        continue
                    close_lead = df_lead['Close'].dropna()
                    lead_ret_4h = float(close_lead.pct_change(4).iloc[-1]) if len(close_lead)>4 else 0
                    # If both up but leader up more => continuation
                    if abs(lead_ret_4h) > abs(target_ret_4h)*1.5 and abs(lead_ret_4h) > 0.002:
                        if (lead_ret_4h>0 and target_ret_4h>=0) or (lead_ret_4h<0 and target_ret_4h<=0):
                            score = min(abs(lead_ret_4h)*1500, 50) * (1 if lead_ret_4h>0 else -1)
                            # Apply correlation logic
                            if instrument in ["XAUUSD"] and lead_inst=="TNX":
                                score = -score
                            lead_signals.append({
                                "leader": lead_inst,
                                "type": "momentum_continuation",
                                "lead_ret_4h": round(lead_ret_4h,4),
                                "target_ret_4h": round(target_ret_4h,4),
                                "score": round(score,1)
                            })
                            total_lead_score += score

            if not lead_signals:
                return self._make_result(instrument, 0, confidence=0.3, metadata={"target_ret_4h": round(target_ret_4h,4)})

            avg_score = total_lead_score / len(lead_signals)
            confidence = 0.7 if len(lead_signals)>=2 else 0.5
            if any(abs(ls["lead_ret_4h"])>0.01 for ls in lead_signals):
                confidence = 0.8

            return self._make_result(instrument, max(-80, min(80, avg_score)), confidence=confidence, metadata={
                "target_ret_4h": round(target_ret_4h,4),
                "lead_signals": lead_signals
            })
        except Exception as e:
            logger.debug(f"S13 {instrument}: {e}")
            return self._make_result(instrument, 0, confidence=0.1, metadata={"error": str(e)})
