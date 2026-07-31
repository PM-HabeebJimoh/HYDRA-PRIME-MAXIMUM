"""Vectorised first-touch barrier resolution on real 1m paths.

Ambiguity rule: if a single 1m bar touches both barriers, resolve ADVERSE.
"""
import numpy as np


def first_touch(high, low, starts, entry, stop, target, side, horizon):
    """side +1 long, -1 short. Returns outcome array (+1,-1,0) and bars held."""
    n = len(starts)
    out = np.zeros(n, dtype=np.int8)
    held = np.zeros(n, dtype=np.int32)
    N = len(high)
    for j in range(n):
        s = starts[j]
        e = min(s + horizon, N)
        if s >= e:
            held[j] = 0
            continue
        hi = high[s:e]
        lo = low[s:e]
        if side[j] > 0:
            ts = np.flatnonzero(lo <= stop[j])
            tt = np.flatnonzero(hi >= target[j])
        else:
            ts = np.flatnonzero(hi >= stop[j])
            tt = np.flatnonzero(lo <= target[j])
        is_ = ts[0] if ts.size else np.iinfo(np.int32).max
        it_ = tt[0] if tt.size else np.iinfo(np.int32).max
        if is_ == np.iinfo(np.int32).max and it_ == np.iinfo(np.int32).max:
            out[j] = 0
            held[j] = e - s
        elif is_ <= it_:            # tie within one bar -> adverse
            out[j] = -1
            held[j] = is_ + 1
        else:
            out[j] = +1
            held[j] = it_ + 1
    return out, held
