"""
S11: Dark Pool / Block Trade Detection — T-4H
Proxy via volume spikes at price extremes + large trades in Binance for crypto.
When block trades appear, smart money is positioning.
"""
from .base import BaseSignal, SignalResult
from hydra.data_sources.yahoo import YahooDataSource
from hydra.data_sources.binance import BinanceDataSource
import config
import pandas as pd
import logging
logger = logging.getLogger(__name__)

class DarkPoolSignal(BaseSignal):
    name = "S11_DARK_POOL"
    timeframe = "4h"
    lead_time = "1-4 hours"
    weight = 1.0

    def __init__(self):
        super().__init__()
        self.yahoo = YahooDataSource()
        self.binance = BinanceDataSource()

    async def evaluate(self, instrument: str) -> SignalResult:
        yft = config.YF_TICKERS.get(instrument)
        if not yft:
            return self._make_result(instrument, 0, confidence=0.1)

        try:
            # For crypto, use Binance block detection via trade size
            if config.INSTRUMENTS.get(instrument, {}).get("type") == "crypto":
                binance_sym = config.INSTRUMENTS[instrument].get("binance")
                if binance_sym:
                    trades = await self.binance.get_trades(binance_sym, limit=100)
                    if trades:
                        qtys = [float(t["qty"]) for t in trades]
                        avg_qty = sum(qtys)/len(qtys)
                        max_qty = max(qtys)
                        # Block if max > 5x avg
                        if max_qty > avg_qty * 5:
                            # Determine direction by price vs aggregated
                            # If large trades were buyerMaker false = buy vol aggressive
                            large_trades = [t for t in trades if float(t["qty"]) > avg_qty*3]
                            buy_large = sum(1 for t in large_trades if not t.get("isBuyerMaker"))
                            sell_large = len(large_trades) - buy_large
                            direction = 1 if buy_large > sell_large else -1 if sell_large > buy_large else 0
                            score = 60 * direction
                            return self._make_result(instrument, score, confidence=0.7, metadata={
                                "avg_qty": round(avg_qty,4),
                                "max_qty": round(max_qty,4),
                                "block_ratio": round(max_qty/avg_qty,2),
                                "buy_large": buy_large,
                                "sell_large": sell_large,
                                "type": "dark_pool_crypto"
                            })

            # For FX/metal etc., proxy via Yahoo volume anomaly at price extremes
            df = await self.yahoo.fetch_ohlcv(yft, period="1mo", interval="1h")
            if df.empty or len(df) < 50:
                return self._make_result(instrument, 0, confidence=0.2)

            close = df['Close'].dropna()
            volume = df['Volume'].dropna() if 'Volume' in df and not df['Volume'].dropna().empty else pd.Series([0]*len(df))

            # Volume spike detection
            if len(volume) > 20 and volume.sum() > 0:
                vol_ma = volume.rolling(20).mean()
                vol_std = volume.rolling(20).std()
                curr_vol = float(volume.iloc[-1])
                ma_last = float(vol_ma.iloc[-1]) if not pd.isna(vol_ma.iloc[-1]) else 0
                std_last = float(vol_std.iloc[-1]) if not pd.isna(vol_std.iloc[-1]) else 1

                z = (curr_vol - ma_last) / (std_last + 1e-10)
                # Also price at high/low of recent range
                recent_high = float(close.rolling(20).max().iloc[-1])
                recent_low = float(close.rolling(20).min().iloc[-1])
                curr_price = float(close.iloc[-1])
                at_extreme = curr_price >= recent_high*0.998 or curr_price <= recent_low*1.002

                if z > 2.0 and at_extreme:
                    # Block at extreme = smart money taking liquidity
                    direction = 1 if curr_price <= recent_low*1.002 else -1  # if at low and volume spike = accumulation bullish
                    score = min(z*15, 70) * direction
                    return self._make_result(instrument, score, confidence=0.65, metadata={
                        "vol_z": round(z,2),
                        "curr_vol": curr_vol,
                        "ma_vol": round(ma_last,1),
                        "at_extreme": at_extreme,
                        "curr_price": curr_price,
                        "recent_high": recent_high,
                        "recent_low": recent_low,
                        "type": "dark_pool_volume"
                    })

            return self._make_result(instrument, 0, confidence=0.3, metadata={"reason": "no block"})
        except Exception as e:
            logger.debug(f"S11 {instrument}: {e}")
            return self._make_result(instrument, 0, confidence=0.1, metadata={"error": str(e)})
