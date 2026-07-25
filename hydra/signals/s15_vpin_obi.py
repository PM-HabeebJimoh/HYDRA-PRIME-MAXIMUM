"""
S15: VPIN + Order Book Imbalance + Microstructure Pressure — T-5 MINUTES
Highest frequency pre-movement signals.
VPIN: Volume-synchronized probability of informed trading
OBI: Order book imbalance (bid vs ask)
Iceberg detection via trade flow
Fires every few minutes.
"""
from .base import BaseSignal, SignalResult
from hydra.data_sources.binance import BinanceDataSource
from hydra.data_sources.yahoo import YahooDataSource
import config
import pandas as pd
import numpy as np
import logging
logger = logging.getLogger(__name__)

class VpinObiSignal(BaseSignal):
    name = "S15_VPIN_OBI"
    timeframe = "5m"
    lead_time = "5-30 minutes"
    weight = 1.5

    def __init__(self):
        super().__init__()
        self.binance = BinanceDataSource()
        self.yahoo = YahooDataSource()

    async def evaluate(self, instrument: str) -> SignalResult:
        try:
            # Crypto path — use Binance live OBI + microstructure
            if config.INSTRUMENTS.get(instrument, {}).get("type") == "crypto":
                binance_sym = config.INSTRUMENTS[instrument].get("binance")
                if binance_sym:
                    obi_data = await self.binance.compute_obi(binance_sym)
                    micro = await self.binance.compute_microstructure(binance_sym)

                    score = 0
                    meta = {"obi": obi_data, "micro": micro}
                    confidence = 0.4

                    obi = obi_data.get("obi",0)
                    imbalance = micro.get("imbalance",0)
                    vpin_proxy = micro.get("vpin_proxy",0)

                    # Conditions
                    if abs(obi) > 0.3:
                        score += obi*100  # OBI already -1..1 => *100 = -100..100
                        confidence = max(confidence, 0.6)

                    if abs(imbalance) > 0.3:
                        score += imbalance*80
                        confidence = max(confidence, 0.65)

                    if vpin_proxy > 0.4:
                        # Informed trading active -> direction from imbalance
                        score += (imbalance*50) if imbalance!=0 else (obi*50)
                        confidence = 0.75
                        meta["informed_active"] = True

                    # Combined
                    final_score = max(-90, min(90, score))
                    # If both OBI and imbalance agree => strong signal
                    if obi>0.2 and imbalance>0.2:
                        final_score = max(final_score, 60)
                        confidence = 0.85
                    elif obi<-0.2 and imbalance<-0.2:
                        final_score = min(final_score, -60)
                        confidence = 0.85

                    return self._make_result(instrument, final_score, confidence=confidence, metadata=meta)

            # FX / Metals / Indices: proxy VPIN via Yahoo high-freq (1h) volume + price
            yft = config.YF_TICKERS.get(instrument)
            if not yft:
                return self._make_result(instrument, 0, confidence=0.1)

            df = await self.yahoo.fetch_ohlcv(yft, period="5d", interval="1h")
            if df.empty or len(df) < 20:
                return self._make_result(instrument, 0, confidence=0.2)

            close = df['Close'].dropna()
            volume = df['Volume'].dropna() if 'Volume' in df and not df['Volume'].dropna().empty else pd.Series([1]*len(df))

            # VPIN proxy: Volume Imbalance vs Price movement correlation
            # Compute buy/sell volume proxy: if close up, assume buy vol dominates
            rets = close.pct_change().dropna()
            # Classify as buy vol if ret>0
            buy_vol = []
            sell_vol = []
            for i in range(max(0,len(rets)-20), len(rets)):
                idx = rets.index[i]
                try:
                    vol = float(volume.loc[idx]) if idx in volume.index else 0
                except:
                    vol = 0
                if rets.iloc[i] > 0:
                    buy_vol.append(vol)
                    sell_vol.append(0)
                else:
                    buy_vol.append(0)
                    sell_vol.append(vol)

            if not buy_vol:
                return self._make_result(instrument, 0, confidence=0.2)

            total_buy = sum(buy_vol)
            total_sell = sum(sell_vol)
            total = total_buy + total_sell
            if total == 0:
                vpin_proxy = 0
                imbalance = 0
            else:
                imbalance = (total_buy - total_sell)/total
                vpin_proxy = abs(total_buy - total_sell)/total

            # OBI proxy via recent candles: count bullish vs bearish wicks
            recent = df.tail(20)
            try:
                bullish_candles = len(recent[recent['Close'] > recent['Open']]) if 'Open' in recent else 10
                bearish_candles = 20 - bullish_candles
                obi_proxy = (bullish_candles - bearish_candles)/20
            except:
                obi_proxy = 0

            score = 0
            confidence = 0.4
            if abs(obi_proxy) > 0.3:
                score += obi_proxy*60
                confidence = 0.55
            if abs(imbalance) > 0.3:
                score += imbalance*60
                confidence = 0.6
            if vpin_proxy > 0.4:
                # Informed trading active
                score += imbalance*40
                confidence = 0.7

            final_score = max(-80, min(80, score))
            return self._make_result(instrument, final_score, confidence=confidence, metadata={
                "obi_proxy": round(obi_proxy,3),
                "imbalance": round(imbalance,3),
                "vpin_proxy": round(vpin_proxy,3),
                "buy_vol": total_buy,
                "sell_vol": total_sell,
                "type": "vpin_obi_proxy"
            })

        except Exception as e:
            logger.debug(f"S15 {instrument}: {e}")
            return self._make_result(instrument, 0, confidence=0.1, metadata={"error": str(e)})
