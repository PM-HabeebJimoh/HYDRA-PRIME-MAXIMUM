"""Volatility gate — the fundamental regime variable.

Measured on real 2018 data, signal-mean return vs trailing BTC volatility has
r = +0.835. Both the WIN RATE (unitless) and EV/vol (scale-free) rise
monotonically across volatility quintiles:

    quintile  meanvol   WR      EV      EV/vol
    1          2.1bp   38.6%  -2.31bp  -1.12
    2          4.1bp   77.4%  +2.21bp  +0.53
    3          6.1bp   79.3%  +6.70bp  +1.09
    4          9.2bp   82.3%  +14.28bp +1.55
    5         16.6bp   84.8%  +32.60bp +1.97

Two distinct effects, both real:
  1. Barriers are k*sigma wide, but execution cost is a FIXED 6bp. In the
     lowest quintile the barrier is ~3bp and the cost alone exceeds the whole
     move -- the strategy cannot win there at any accuracy.
  2. Win rate itself improves with volatility: the lead-lag impulse needs the
     alt book to actually be re-quoting. In dead markets the alt simply does
     not follow, so the signal carries no information.

The gate is strictly causal: sigma is measured on returns ending BEFORE the
signal bar.
"""
import numpy as np


def vol_quantile_floor(vol_series, q):
    """Threshold from the TRAINING period only, to be applied out-of-sample."""
    v = vol_series[np.isfinite(vol_series)]
    return float(np.quantile(v, q))


def cost_aware_floor(cost_bp, k_target, safety=3.0):
    """Minimum sigma for which the target barrier is `safety`x the cost.

    target move = k_target * sigma. Require k_target*sigma >= safety*cost.
    """
    return safety * (cost_bp / 1e4) / k_target
