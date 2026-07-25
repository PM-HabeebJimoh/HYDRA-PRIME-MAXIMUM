"""
STREAM 4: STATISTICAL ARBITRAGE (PAIR CONVERGENCE)
Highest win rate trade in existence: 94%+ (Gatev, Goetzmann, Rouwenhorst 2006)
When physically-linked instruments diverge, trade convergence.
"""
from hydra.data_sources.yahoo import YahooDataSource
import config
import pandas as pd
import numpy as np
import logging
from datetime import datetime
logger = logging.getLogger(__name__)

class StatisticalArbitrageEngine:
    PAIRS = config.STAT_ARB_PAIRS

    def __init__(self):
        self.yahoo = YahooDataSource()

    async def check_pair(self, pair: dict) -> dict:
        try:
            # Fetch both tickers 6mo daily
            data_a = await self.yahoo.fetch_ohlcv(pair['ticker_a'], period="6mo", interval="1d")
            data_b = await self.yahoo.fetch_ohlcv(pair['ticker_b'], period="6mo", interval="1d")

            if data_a.empty or data_b.empty or len(data_a)<30 or len(data_b)<30:
                return {"pair": pair['name'], "trade": False, "error": "insufficient_data"}

            close_a = data_a['Close'].dropna()
            close_b = data_b['Close'].dropna()

            # Align
            df = pd.DataFrame({"a": close_a, "b": close_b}).dropna()
            if len(df) < 30:
                return {"pair": pair['name'], "trade": False, "error": "align insufficient"}

            if pair['type'] == 'price_ratio':
                ratio = df['a'] / df['b']
            elif pair['type'] == 'spread':
                ratio = df['a'] - df['b']
            elif pair['type'] == 'correlation_z':
                corr = df['a'].rolling(21).corr(df['b'])
                ratio = corr
            elif pair['type'] == 'ratio':
                ratio = df['a'] / df['b']
            else:
                ratio = df['a'] / df['b']

            mean = float(ratio.rolling(90).mean().iloc[-1]) if len(ratio)>=90 else float(ratio.mean())
            std = float(ratio.rolling(90).std().iloc[-1]) + 1e-10 if len(ratio)>=90 else float(ratio.std())+1e-10
            curr = float(ratio.iloc[-1])
            z = (curr - mean) / std if std!=0 else 0

            if abs(z) > pair['trade_z']:
                if z > pair['trade_z']:
                    direction = 'SHORT_A_LONG_B'
                    trade_dir_a = -1
                    trade_dir_b = +1
                else:
                    direction = 'LONG_A_SHORT_B'
                    trade_dir_a = +1
                    trade_dir_b = -1

                expected_return = abs(z - pair['close_z']) * float(std)

                return {
                    "pair": pair['name'],
                    "trade": True,
                    "z": round(z,3),
                    "direction": direction,
                    "trade_dir_a": trade_dir_a,
                    "trade_dir_b": trade_dir_b,
                    "instrument_a": pair['a'],
                    "instrument_b": pair['b'],
                    "ticker_a": pair['ticker_a'],
                    "ticker_b": pair['ticker_b'],
                    "expected_return": round(expected_return*100,2) if pair['type']!='price_ratio' else round(abs(z)*2,2),
                    "win_rate": pair['win_rate'],
                    "close_when_z": pair['close_z'],
                    "current_ratio": round(curr,4),
                    "mean_ratio": round(mean,4),
                    "signal_type": "STAT_ARB",
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "pair": pair['name'],
                    "trade": False,
                    "z": round(z,3),
                    "status": "Within normal range",
                    "current_ratio": round(curr,4),
                    "mean_ratio": round(mean,4)
                }
        except Exception as e:
            logger.debug(f"Pair check {pair['name']}: {e}")
            return {"pair": pair['name'], "trade": False, "error": str(e)}

    async def all_pairs(self) -> list:
        import asyncio
        tasks = [self.check_pair(p) for p in self.PAIRS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        out = []
        for r in results:
            if isinstance(r, Exception):
                continue
            out.append(r)
        return out

    async def actionable_pairs(self) -> list:
        all_res = await self.all_pairs()
        return [r for r in all_res if r.get("trade")]
