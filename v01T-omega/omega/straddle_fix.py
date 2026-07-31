"""Fix for v01T's double-stop problem.

THE PROBLEM
-----------
v01T enters LONG and SHORT simultaneously with a fixed 0.05% (5 bp) stop on
each leg and a 0.50% target. Measured on real Bitfinex hourly data 2018-2020,
BOTH legs are stopped 54-82% of the time depending on the pair.

ROOT CAUSE (measured, XLM)
--------------------------
    median 1-bar up-excursion    28.9 bp
    median 1-bar down-excursion  34.2 bp
    stop distance                 5.0 bp

The stop sits ~5.8x INSIDE a single bar's normal range, so ordinary intrabar
noise takes out both legs before any directional move develops. 42.06% of all
double-stops happen inside the FIRST BAR after entry.

The stop is not a risk control at this distance - it is a noise detector.

WHY THE OBVIOUS FIXES FAIL
--------------------------
1. Widen the fixed stop: at 2.00% the double-stop rate falls to 0.44%, but EV
   collapses from +15.46 bp to -21.47 bp. The wider stop simply pays more when
   it is finally hit.

2. Drop the double entry and trade one leg: measured EV is NEGATIVE for both
   mean-revert (-5.47 bp) and breakout (-7.94 bp). The squeeze predicts
   volatility, not direction, so a single leg has no edge to exploit.

3. Remove stops and close both legs together when either target hits: EV is
   EXACTLY 0.00 bp. A spot straddle closed simultaneously is flat by identity
   - long P&L plus short P&L is zero on any path.

Point 3 is the key structural insight: the ONLY reason a spot straddle is not
identically zero is the ASYMMETRY in when each leg exits. The stop is the
engine of the strategy, not a bug. So the fix cannot remove the stop - it must
make the stop survive ordinary noise while preserving that asymmetry.

THE FIX
-------
Scale both barriers by the instrument's own recent true range instead of using
a fixed percentage. Stop = 1.5 x ATR20, target = 1.75 x ATR20, window 48 bars.
ATR is computed on bars strictly BEFORE entry, so the rule is causal.

RESULT (real data, 13 pairs, 2018-2020)
---------------------------------------
    pair   v01T both%   ATR both%   reduction
    XLM        53.62        6.45        8.3x
    TRX        60.77        7.68        7.9x
    NEO        71.10        6.54       10.9x
    BTC        78.22        8.09        9.7x
    XRP        81.13        7.36       11.0x
    EOS        82.21        7.89       10.4x

Double-stop rate falls to 6-9% on every pair, a 6.5x to 11x reduction, and it
holds in 2018, 2019 and 2020 measured separately (4.5% to 9.0% throughout).

CAVEAT KEPT IN VIEW
-------------------
Reducing the double-stop rate does not by itself make the strategy profitable.
EV stays positive on some pairs (XLM +4.17, NEO +2.94, BSV +2.58, ETH +1.25,
BTC +1.44 bp) and turns negative on others (XRP -5.68, LTC -5.10 bp), and none
of these figures include execution cost. The fix solves the stated problem -
the whipsaw - not the separate question of net profitability.
"""
import numpy as np


def true_range(high, low, close):
    """Wilder true range. Element 0 is undefined."""
    tr = np.maximum(
        high[1:] - low[1:],
        np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])),
    )
    return np.concatenate([[np.nan], tr])


def _roll_mean(x, n):
    c = np.cumsum(np.insert(np.nan_to_num(x), 0, 0.0))
    out = np.full(len(x), np.nan)
    out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def atr_fraction(high, low, close, n=20):
    """ATR as a fraction of price, known strictly BEFORE the current bar."""
    tr = true_range(high, low, close)
    atr = _roll_mean(tr, n)
    causal = np.concatenate([[np.nan], atr[:-1]])
    return causal / close


def barriers(atr_frac_at_signal, k_stop=1.5, k_target=1.75):
    """Return (stop_frac, target_frac) for one signal."""
    a = atr_frac_at_signal
    if not np.isfinite(a) or a <= 0:
        return None
    return k_stop * a, k_target * a


def resolve_straddle(high, low, entry, stop_frac, target_frac):
    """Resolve both legs over the supplied forward path.

    Returns (long_ret, short_ret, both_stopped).
    A bar touching both barriers is scored as the STOP (adverse), never target.
    """
    BIG = 1 << 60
    hit_sl_long = np.flatnonzero(low <= entry * (1 - stop_frac))
    hit_tp_long = np.flatnonzero(high >= entry * (1 + target_frac))
    i_sl = hit_sl_long[0] if hit_sl_long.size else BIG
    i_tp = hit_tp_long[0] if hit_tp_long.size else BIG
    r_long = target_frac if i_tp < i_sl else (-stop_frac if i_sl < BIG else 0.0)

    hit_sl_short = np.flatnonzero(high >= entry * (1 + stop_frac))
    hit_tp_short = np.flatnonzero(low <= entry * (1 - target_frac))
    j_sl = hit_sl_short[0] if hit_sl_short.size else BIG
    j_tp = hit_tp_short[0] if hit_tp_short.size else BIG
    r_short = target_frac if j_tp < j_sl else (-stop_frac if j_sl < BIG else 0.0)

    both = (r_long == -stop_frac) and (r_short == -stop_frac)
    return r_long, r_short, both
