"""
STREAM 2: CARRY TRADE HARVESTING
Earn interest differential daily while waiting for directional signals.
High-carry pairs: GBPJPY, USDJPY, AUDJPY, NZDJPY, EURJPY
"""
import config
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

class CarryHarvester:
    CARRY_PAIRS = config.CARRY_PAIRS
    POSITIVE_CARRY = config.POSITIVE_CARRY

    def daily_carry_income(self, pair: str, notional: float, leverage: float = 10.0) -> float:
        data = self.CARRY_PAIRS.get(pair, {})
        annual_pct = data.get('net_carry', 0)
        # If negative carry, income negative
        daily_income = notional * leverage * (annual_pct/100) / 365
        return daily_income

    def carry_vs_reversal_risk(self, pair: str, pre_move_score: float, direction: int) -> dict:
        """Should we maintain carry or exit? Exit only when strong reversal against carry"""
        carry_direction = +1  # We are long carry pair (buy high-rate, sell low-rate)
        # Conflict if pre-move is strong against carry direction
        conflict = direction == -1 and abs(pre_move_score) > 80

        daily_income = self.daily_carry_income(pair, 10000, 10)

        return {
            "pair": pair,
            "maintain_carry": not conflict,
            "conflict": conflict,
            "action": "EXIT CARRY — strong reversal signal" if conflict else "MAINTAIN CARRY — income accumulating",
            "daily_income": round(daily_income,2),
            "monthly_income": round(daily_income*30,2),
            "annual_carry_pct": self.CARRY_PAIRS.get(pair, {}).get("net_carry",0),
            "score": pre_move_score,
            "direction": direction,
            "timestamp": datetime.utcnow().isoformat()
        }

    def all_carry_positions(self, capital: float = 10000, leverage: float = 10) -> list:
        positions = []
        for pair in self.POSITIVE_CARRY:
            notional = capital * leverage / len(self.POSITIVE_CARRY)  # split capital
            daily = self.daily_carry_income(pair, capital/len(self.POSITIVE_CARRY), leverage)
            positions.append({
                "pair": pair,
                "notional": round(notional,2),
                "leverage": leverage,
                "annual_carry_pct": self.CARRY_PAIRS[pair]["net_carry"],
                "daily_income": round(daily,2),
                "monthly_income": round(daily*30,2),
                "yearly_income": round(daily*365,2),
                "action": "HOLD — earning carry",
                "timestamp": datetime.utcnow().isoformat()
            })
        return positions

    async def test_live(self) -> dict:
        """Carry doesn't need live data except rates — use Fred to validate rates live"""
        from hydra.data_sources.fred import FredDataSource
        fred = FredDataSource()
        rates = await fred.test_live_async()
        positions = self.all_carry_positions()
        total_monthly = sum(p["monthly_income"] for p in positions)
        return {
            "live": rates.get("live", False),
            "fred_check": rates,
            "positions": positions,
            "total_monthly_carry_on_10k_10x": round(total_monthly,2),
            "count": len(positions)
        }
