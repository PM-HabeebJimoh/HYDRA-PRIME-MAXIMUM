"""
Performance Tracking — ROI, win rate, monthly projections
"""
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

class PerformanceTracker:
    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.trades = []  # list of dicts
        self.wins = 0
        self.losses = 0
        self.daily_pnl_history = []
        self.start_time = datetime.utcnow()

    def record_trade(self, instrument: str, direction: int, score: float, notional: float, result: str = "pending", pnl: float = 0.0):
        trade = {
            "instrument": instrument,
            "direction": direction,
            "score": score,
            "notional": notional,
            "result": result,
            "pnl": pnl,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.trades.append(trade)
        if result == "win":
            self.wins += 1
            self.current_capital += pnl
        elif result == "loss":
            self.losses += 1
            self.current_capital += pnl  # pnl negative
        return trade

    def update_pnl(self, daily_pnl: float):
        self.daily_pnl_history.append({"date": datetime.utcnow().date().isoformat(), "pnl": daily_pnl})

    def get_stats(self) -> dict:
        total = self.wins + self.losses
        win_rate = (self.wins / total * 100) if total>0 else 0
        total_return_pct = (self.current_capital - self.initial_capital) / self.initial_capital * 100 if self.initial_capital>0 else 0
        today_trades = len([t for t in self.trades if t["timestamp"][:10] == datetime.utcnow().date().isoformat()])
        today_wins = len([t for t in self.trades if t["timestamp"][:10] == datetime.utcnow().date().isoformat() and t["result"]=="win"])

        # Monthly projection based on realistic math from blueprint
        # Conservative 60%/mo, Realistic 110%/mo
        conservative_monthly = 61.9
        realistic_monthly = 110.9
        optimistic_monthly = 300.0  # with compounding optimization

        # Compounding projection from current capital at 100%/month
        months = 6
        compounding = []
        cap = self.current_capital
        for m in range(1, months+1):
            cap = cap * 2  # 100%/month
            compounding.append({"month": m, "capital": round(cap,2)})

        return {
            "capital_initial": self.initial_capital,
            "capital_current": round(self.current_capital,2),
            "total_return_pct": round(total_return_pct,2),
            "total_trades": total,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": round(win_rate,1),
            "trades_today": today_trades,
            "win_rate_today": round((today_wins/max(today_trades,1)*100),1) if today_trades else 0,
            "daily_pnl": round(sum(d["pnl"] for d in self.daily_pnl_history[-1:]),2) if self.daily_pnl_history else 0,
            "runtime_days": (datetime.utcnow() - self.start_time).days,
            "projections": {
                "conservative_monthly_pct": conservative_monthly,
                "realistic_monthly_pct": realistic_monthly,
                "optimistic_monthly_pct": optimistic_monthly,
                "compounding_100pct_monthly_6mo": compounding
            }
        }
