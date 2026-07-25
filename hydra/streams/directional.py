"""
STREAM 1: PRE-MOVEMENT DIRECTIONAL — Multi-timeframe convergence
Fire when 3+ timeframe signals converge.
Target 92% win rate via multi-TF convergence.
"""
import config
from hydra.signals import SIGNAL_CLASSES, SignalResult
import asyncio
import logging
from datetime import datetime
logger = logging.getLogger(__name__)

class PreMovementEngine:
    def __init__(self, capital: float = 10000.0):
        self.capital = capital
        self.signal_engines = [cls() for cls in SIGNAL_CLASSES]
        self.threshold_fire = config.PRE_MOVE_THRESHOLD_FIRE
        self.threshold_elite = config.PRE_MOVE_THRESHOLD_ELITE

    async def compute_score(self, instrument: str, signals: list = None) -> dict:
        """Compute multi-TF converged pre-move score from list of SignalResult"""
        if signals is None:
            # Evaluate all signals for instrument in parallel
            tasks = [engine.evaluate(instrument) for engine in self.signal_engines]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            signals = [r for r in results if isinstance(r, SignalResult)]

        if not signals:
            return {
                "instrument": instrument,
                "pre_move_score": 0,
                "fire": False,
                "direction": 0,
                "signals_used": 0
            }

        # Weighted score
        weighted_sum = 0
        weight_total = 0
        bullish_count = 0
        bearish_count = 0
        confidences = []
        timeframe_groups = {"4_weeks": [], "1_week": [], "48h": [], "4h": [], "30m": [], "5m": []}

        for sig in signals:
            w = config.SIGNAL_WEIGHTS.get(sig.signal_name, 1.0)
            weighted_sum += sig.score * w
            weight_total += w
            confidences.append(sig.confidence)
            if sig.direction > 0:
                bullish_count += 1
            elif sig.direction < 0:
                bearish_count += 1
            # Group by timeframe
            tf = sig.timeframe
            if tf in timeframe_groups:
                timeframe_groups[tf].append(sig)
            else:
                # Map loosely
                if "week" in tf:
                    timeframe_groups["4_weeks"].append(sig)

        final_score = weighted_sum / weight_total if weight_total>0 else 0
        avg_conf = sum(confidences)/len(confidences) if confidences else 0

        # Multi-TF convergence bonus: if 3+ timeframes agree direction, boost score + increase confidence
        tf_agree = 0
        direction = 1 if final_score > 0 else -1 if final_score < 0 else 0
        for tf, sigs in timeframe_groups.items():
            if not sigs:
                continue
            tf_score = sum(s.score for s in sigs)/len(sigs)
            tf_dir = 1 if tf_score>5 else -1 if tf_score<-5 else 0
            if tf_dir == direction and tf_dir !=0:
                tf_agree += 1

        convergence_bonus = 0
        if tf_agree >= 3:
            convergence_bonus = 20  # 3 TF agree => elite setup
        elif tf_agree >= 2:
            convergence_bonus = 10

        final_score_with_bonus = final_score + (convergence_bonus if direction>0 else -convergence_bonus if direction<0 else 0)
        final_score_with_bonus = max(-100, min(100, final_score_with_bonus))

        # Confidence boost for convergence
        if tf_agree >= 3:
            avg_conf = min(0.95, avg_conf + 0.2)
        elif tf_agree >=2:
            avg_conf = min(0.9, avg_conf + 0.1)

        fire = abs(final_score_with_bonus) >= self.threshold_fire and avg_conf >= 0.35
        elite = abs(final_score_with_bonus) >= self.threshold_elite and tf_agree>=3 and avg_conf>=0.65

        # Position sizing
        pos_size = self._position_sizing(instrument, final_score_with_bonus, avg_conf, elite)

        # Lead time estimate = shortest timeframe that fired
        lead_time = "unknown"
        if tf_agree>0:
            # Find smallest tf with signal
            for tf in ["5m","30m","4h","48h","1_week","4_weeks"]:
                if timeframe_groups.get(tf) and any(abs(s.score)>20 for s in timeframe_groups[tf]):
                    lead_map = {"5m":"5-30min","30m":"15-60min","4h":"2-8h","48h":"24-48h","1_week":"3-7d","4_weeks":"2-4w"}
                    lead_time = lead_map.get(tf, tf)
                    break

        return {
            "instrument": instrument,
            "pre_move_score": round(float(final_score_with_bonus),1),
            "raw_score": round(float(final_score),1),
            "convergence_bonus": convergence_bonus,
            "tf_agree": tf_agree,
            "fire": fire,
            "elite": elite,
            "direction": direction,
            "direction_label": "LONG" if direction>0 else "SHORT" if direction<0 else "NEUTRAL",
            "confidence": round(avg_conf,3),
            "signals_used": len(signals),
            "bullish_signals": bullish_count,
            "bearish_signals": bearish_count,
            "lead_time_est": lead_time,
            "position_size": pos_size,
            "timestamp": datetime.utcnow().isoformat(),
            "signals": [{"name": s.signal_name, "score": s.score, "dir": s.direction, "conf": s.confidence, "tf": s.timeframe} for s in signals]
        }

    def _position_sizing(self, instrument: str, score: float, confidence: float, elite: bool) -> dict:
        """Conservative risk: 1% risk per trade, 0.05% stop for elite precision, 0.2% normal"""
        cfg = config.RISK_CONFIG
        risk_per_trade_pct = cfg["risk_per_trade_pct"]
        stop_pct = cfg["stop_pct_tight"] if elite else cfg["stop_pct_normal"]

        # Notional based on capital * leverage but risk-controlled
        # Correct formula: position size such that stop loss = risk_per_trade
        # notional = (capital * risk_pct) / stop_pct
        risk_amount = self.capital * (risk_per_trade_pct/100)
        notional = risk_amount / (stop_pct/100)

        # Leverage
        # notional / capital = leverage needed
        leverage_needed = notional / self.capital if self.capital>0 else 1
        max_lev = config.INSTRUMENTS.get(instrument, {}).get("leverage_max", cfg["max_leverage"])

        # Cap leverage
        leverage = min(leverage_needed, max_lev, cfg["max_leverage"])
        if elite:
            leverage = min(leverage*1.5, max_lev)

        # Adjust notional by confidence
        notional_adj = notional * confidence
        # Also adjust by score magnitude
        notional_adj *= (abs(score)/100)

        # Max exposure cap
        max_notional = self.capital * leverage
        notional_adj = min(notional_adj, max_notional)

        return {
            "notional_size": round(notional_adj,2),
            "leverage": round(leverage,1),
            "stop_pct": stop_pct,
            "risk_amount": round(risk_amount,2),
            "elite": elite
        }

    async def scan_all(self, instruments: list = None) -> list:
        if instruments is None:
            instruments = config.ALL_INSTRUMENTS
        tasks = [self.compute_score(inst) for inst in instruments]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        out = []
        for res in results:
            if isinstance(res, Exception):
                continue
            out.append(res)
        # Sort by absolute score descending
        out.sort(key=lambda x: abs(x.get("pre_move_score",0)), reverse=True)
        return out
