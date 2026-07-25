"""
S12: Options Flow Anomaly — T-4H
Detect OTM buying surge. Smart money buys OTM calls before rallies.
Free via yfinance options + Binance options? Use yfinance volume/oi anomaly.
"""
from .base import BaseSignal, SignalResult
from hydra.data_sources.yahoo import YahooDataSource
import config
import logging
logger = logging.getLogger(__name__)

class OptionsFlowSignal(BaseSignal):
    name = "S12_OPTIONS_FLOW"
    timeframe = "4h"
    lead_time = "1-6 hours"
    weight = 1.2

    def __init__(self):
        super().__init__()
        self.yahoo = YahooDataSource()

    async def evaluate(self, instrument: str) -> SignalResult:
        yft = config.YF_TICKERS.get(instrument)
        if not yft:
            return self._make_result(instrument, 0, confidence=0.1)

        try:
            chain = await self.yahoo.get_options_chain(yft)
            if not chain:
                return self._make_result(instrument, 0, confidence=0.2, metadata={"reason": "no chain"})

            calls = chain.calls
            puts = chain.puts
            if calls.empty or puts.empty:
                return self._make_result(instrument, 0, confidence=0.2)

            # Need current price to identify OTM
            df = await self.yahoo.fetch_ohlcv(yft, period="5d", interval="1d")
            if df.empty:
                curr_price = None
            else:
                curr_price = float(df['Close'].iloc[-1])

            if curr_price is None:
                return self._make_result(instrument, 0, confidence=0.2, metadata={"reason": "no price"})

            # OTM calls: strike > curr_price * 1.02
            # OTM puts: strike < curr_price * 0.98
            try:
                otm_calls = calls[calls['strike'] > curr_price*1.02]
                otm_puts = puts[puts['strike'] < curr_price*0.98]

                # Flow anomaly: volume >> openInterest for OTM
                def flow_score(df_opt, typ):
                    if df_opt.empty:
                        return 0, {}
                    # Filter where volume > OI * threshold
                    if 'volume' not in df_opt or 'openInterest' not in df_opt:
                        return 0, {}
                    df_opt = df_opt.dropna(subset=['volume','openInterest'])
                    if df_opt.empty:
                        return 0, {}
                    # Anomaly: volume > openInterest * 1.5 or volume > avg_volume*3
                    avg_vol = df_opt['volume'].mean()
                    high_flow = df_opt[df_opt['volume'] > df_opt['openInterest']*0.5]
                    if high_flow.empty:
                        return 0, {"avg_vol": float(avg_vol)}
                    total_anomaly_vol = high_flow['volume'].sum()
                    total_oi = high_flow['openInterest'].sum()
                    ratio = total_anomaly_vol / (total_oi+1e-10)
                    # Score
                    score = min(ratio*20, 80)
                    return score, {"anomaly_vol": int(total_anomaly_vol), "anomaly_oi": int(total_oi), "ratio": round(ratio,2), "count": len(high_flow)}

                call_score, call_meta = flow_score(otm_calls, "call")
                put_score, put_meta = flow_score(otm_puts, "put")

                net_score = call_score - put_score  # bullish if calls dominate

                confidence = 0.5
                if abs(net_score) > 30:
                    confidence = 0.7
                if abs(net_score) > 50:
                    confidence = 0.8

                return self._make_result(instrument, max(-80, min(80, net_score)), confidence=confidence, metadata={
                    "curr_price": curr_price,
                    "call_flow": call_meta,
                    "put_flow": put_meta,
                    "otm_calls_count": len(otm_calls),
                    "otm_puts_count": len(otm_puts)
                })
            except Exception as e:
                logger.debug(f"S12 flow calc {instrument}: {e}")
                return self._make_result(instrument, 0, confidence=0.2, metadata={"error": str(e)})
        except Exception as e:
            logger.debug(f"S12 {instrument}: {e}")
            return self._make_result(instrument, 0, confidence=0.1, metadata={"error": str(e)})
