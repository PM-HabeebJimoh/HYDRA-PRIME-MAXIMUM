"""
Risk Management — Hard stops, max DD <10%, correlation exposure limits
"""
import config
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(self, capital: float = 10000.0):
        self.initial_capital = capital
        self.peak_capital = capital
        self.current_capital = capital
        self.current_dd = 0.0
        self.max_dd = 0.0
        self.positions = []  # list of open positions
        self.daily_pnl = 0.0
        self.hard_stop_hit = False
        self.pause_until = None

    def update_capital(self, new_capital: float):
        self.current_capital = new_capital
        if new_capital > self.peak_capital:
            self.peak_capital = new_capital
        dd = (self.peak_capital - new_capital) / self.peak_capital * 100 if self.peak_capital>0 else 0
        self.current_dd = dd
        if dd > self.max_dd:
            self.max_dd = dd

        # Check hard stop
        if dd >= config.RISK_CONFIG["max_dd_hard_stop"]:
            self.hard_stop_hit = True
            logger.warning(f"HARD STOP HIT: DD {dd:.2f}% >= {config.RISK_CONFIG['max_dd_hard_stop']}% — PAUSE 24H")
            from datetime import timedelta
            self.pause_until = datetime.utcnow() + timedelta(hours=24)
        elif dd >= config.RISK_CONFIG["max_dd_pause"]:
            logger.warning(f"DD {dd:.2f}% >= {config.RISK_CONFIG['max_dd_pause']}% — PAUSE 1 WEEK AUDIT")
            from datetime import timedelta
            self.pause_until = datetime.utcnow() + timedelta(days=7)

    def check_can_trade(self) -> dict:
        if self.hard_stop_hit:
            if self.pause_until and datetime.utcnow() < self.pause_until:
                return {"can_trade": False, "reason": f"Hard stop DD {self.current_dd:.1f}% — paused until {self.pause_until}", "dd": self.current_dd}
            else:
                # Reset after pause
                self.hard_stop_hit = False
                self.pause_until = None
        if len(self.positions) >= config.RISK_CONFIG["max_positions"]:
            return {"can_trade": False, "reason": f"Max positions {config.RISK_CONFIG['max_positions']} reached", "positions": len(self.positions)}
        return {"can_trade": True, "dd": self.current_dd, "positions": len(self.positions)}

    def check_correlation_exposure(self, instrument: str, proposed_trades: list) -> bool:
        """Avoid >3 correlated trades"""
        # Define correlation clusters
        clusters = {
            "usd_majors": ["EURUSD","GBPUSD","AUDUSD","NZDUSD"],
            "jpy_crosses": ["USDJPY","EURJPY","GBPJPY","AUDJPY","NZDJPY"],
            "metals": ["XAUUSD","XAGUSD","HG","PL","PA"],
            "crypto": ["BTCUSD","ETHUSD","SOLUSD","BNBUSD","XRPUSD"],
            "risk": ["SPX","NDX","AUDUSD","BTCUSD"]
        }
        # Count how many proposed trades in same cluster as instrument
        for cluster, members in clusters.items():
            if instrument in members:
                count = sum(1 for t in proposed_trades if t.get("instrument") in members)
                if count >= config.RISK_CONFIG["max_correlation_exposure"]:
                    return False
        return True

    def position_size_ok(self, notional: float, capital: float) -> bool:
        max_notional = capital * config.RISK_CONFIG["max_leverage"]
        return notional <= max_notional

    def get_status(self) -> dict:
        return {
            "current_capital": round(self.current_capital,2),
            "peak_capital": round(self.peak_capital,2),
            "current_dd": round(self.current_dd,2),
            "max_dd": round(self.max_dd,2),
            "max_dd_limit": config.RISK_CONFIG["max_dd_hard_stop"],
            "positions": len(self.positions),
            "hard_stop_hit": self.hard_stop_hit,
            "pause_until": self.pause_until.isoformat() if self.pause_until else None,
            "can_trade": self.check_can_trade()["can_trade"]
        }
