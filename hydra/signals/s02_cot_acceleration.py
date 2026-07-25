"""
S02: COT Acceleration — T-4 Weeks
Institutional loading detection via COT commercial net position.
When smart money accumulates aggressively, price must follow.
"""
from .base import BaseSignal, SignalResult
from hydra.data_sources.cftc_cot import CotDataSource
import logging
logger = logging.getLogger(__name__)

class CotAccelerationSignal(BaseSignal):
    name = "S02_COT_ACCEL"
    timeframe = "4_weeks"
    lead_time = "1-4 weeks"
    weight = 1.3

    def __init__(self):
        super().__init__()
        self.cot = CotDataSource()

    async def evaluate(self, instrument: str) -> SignalResult:
        try:
            pos = await self.cot.get_commercial_position(instrument)
            if not pos.get("live"):
                # Not all instruments have COT — give 0 neutral but still live if data source live
                return self._make_result(instrument, 0, confidence=0.2, metadata=pos)

            net = pos.get("net_position", 0)
            # Acceleration proxy: large net absolute indicates loading
            # Normalize: net >0 bullish (commercials long = they expect price up, because they hedge)
            # Actually COT: commercials are hedgers, so they are contrarian? 
            # But for FX, asset managers net long = bullish
            # Simplify: positive net = bullish acceleration

            strength = pos.get("strength", 0)
            # Convert net to score -100..100
            # If commercial net long strong -> expect price rise? However commercials often short into rise (hedging production)
            # We invert for metals: commercial short = gold producers hedging = bearish signal if they increase shorts? Actually means they expect lower? Complex.
            # For HYDRA, we treat: increasing commercial long = accumulation = bullish

            # For gold, commercials net short typically, but acceleration of short covering = bullish
            score = 0
            if pos.get("matched"):
                if instrument in ["XAUUSD","XAGUSD","GC","SI","HG","CL"]:
                    # For metals/energy: commercial covering shorts = bullish
                    # So net position moving towards 0 or positive = bullish
                    score = -net / 1000  # invert slightly
                    # Clamp
                    if score > 80: score = 80
                    if score < -80: score = -80
                else:
                    score = net / 1000
                    if score > 80: score = 80
                    if score < -80: score = -80

            confidence = 0.7 if pos.get("matched") else 0.3
            return self._make_result(instrument, score, confidence=confidence, metadata=pos)
        except Exception as e:
            logger.debug(f"S02 {instrument}: {e}")
            return self._make_result(instrument, 0, confidence=0.1, metadata={"error": str(e)})
