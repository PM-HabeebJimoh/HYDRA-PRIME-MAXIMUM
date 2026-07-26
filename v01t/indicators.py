"""
indicators.py — the three primitives behind the v01T elite filter.

  BB%      Bollinger position of the last close inside the 20-period band
  HV ratio short-window volatility divided by long-window volatility
  score    92 for a lower-band squeeze, 85 for an upper-band squeeze, else 72
"""

from __future__ import annotations

import statistics
from typing import Sequence

from . import spec


def compute_bb_percentile(closes: Sequence[float]) -> float:
    """Position of the last close within the 20-period Bollinger band, 0-100.

    Returns the neutral 50.0 when the window is too short or the band has
    zero width.
    """
    if len(closes) < spec.BB_WINDOW:
        return 50.0
    window = list(closes[-spec.BB_WINDOW:])
    sma = sum(window) / spec.BB_WINDOW
    variance = sum((x - sma) ** 2 for x in window) / len(window)
    std = variance ** 0.5
    if std == 0:
        return 50.0
    upper = sma + 2 * std
    lower = sma - 2 * std
    if upper == lower:
        return 50.0
    return round((closes[-1] - lower) / (upper - lower) * 100, 2)


def compute_hv_ratio(closes: Sequence[float]) -> float:
    """Short-term vs long-term realised volatility. Below 1.0 means compression.

    Returns the neutral 1.0 when the series is too short or degenerate.
    """
    if len(closes) < spec.HV_MIN_CLOSES:
        return 1.0
    try:
        rets = [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes))]
        if len(rets) < spec.HV_LONG_WINDOW:
            return 1.0
        short = statistics.stdev(rets[-spec.HV_SHORT_WINDOW:])
        long = statistics.stdev(rets[-spec.HV_LONG_WINDOW:])
        if long == 0:
            return 1.0
        return round(short / long, 3)
    except statistics.StatisticsError:
        return 1.0
    except ZeroDivisionError:
        return 1.0


def score_for(bb_pct: float) -> int:
    """Mechanical score assignment used by the elite filter."""
    if bb_pct < spec.BB_LOW:
        return 92
    if bb_pct > spec.BB_HIGH:
        return 85
    return 72


def is_elite(bb_pct: float, hv_ratio: float, score: int | None = None) -> bool:
    """The v01T elite vol-explosion gate.

        (BB% < 10 OR BB% > 90) AND HV ratio < 0.8 AND score >= 85
    """
    if score is None:
        score = score_for(bb_pct)
    at_band = bb_pct < spec.BB_LOW or bb_pct > spec.BB_HIGH
    return at_band and hv_ratio < spec.HV_MAX and score >= spec.SCORE_MIN
