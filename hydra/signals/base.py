"""
Base signal definition
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
import abc

@dataclass
class SignalResult:
    instrument: str
    signal_name: str
    score: float  # -100 to +100, direction * strength
    direction: int  # -1, 0, +1
    strength: float # 0-100
    confidence: float # 0-1
    timeframe: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    lead_time_est: str = "unknown"

    @property
    def fire(self) -> bool:
        return abs(self.score) >= 20 and self.confidence >= 0.3

class BaseSignal(abc.ABC):
    name: str = "BASE"
    timeframe: str = "unknown"
    weight: float = 1.0
    lead_time: str = "unknown"

    def __init__(self, **kwargs):
        self.config = kwargs

    @abc.abstractmethod
    async def evaluate(self, instrument: str) -> SignalResult:
        pass

    def _make_result(self, instrument: str, score: float, direction: int = None, strength: float = None, confidence: float = 0.5, metadata: dict = None) -> SignalResult:
        if direction is None:
            direction = 1 if score > 0 else -1 if score < 0 else 0
        if strength is None:
            strength = min(abs(score), 100)
        return SignalResult(
            instrument=instrument,
            signal_name=self.name,
            score=max(-100, min(100, score)),
            direction=direction,
            strength=strength,
            confidence=confidence,
            timeframe=self.timeframe,
            metadata=metadata or {},
            lead_time_est=self.lead_time
        )
