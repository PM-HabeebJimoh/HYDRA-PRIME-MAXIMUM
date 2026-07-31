"""Volatility-adaptive version.

First principles: the lead-lag impulse is a RELATIVE shock. A 20bp BTC move is
a huge event in a calm regime and noise in a violent one. Fixed basis-point
thresholds therefore select different phenomena in different years. Normalising
the trigger and the barriers by trailing realised volatility makes the strategy
scale-free, which is what a physical law must be.
"""
import numpy as np
from .fastbarrier import first_touch


def rolling_std(x, n):
    c = np.cumsum(np.insert(x, 0, 0.0))
    c2 = np.cumsum(np.insert(x * x, 0, 0.0))
    m = np.full(len(x), np.nan)
    v = np.full(len(x), np.nan)
    m[n - 1:] = (c[n:] - c[:-n]) / n
    v[n - 1:] = (c2[n:] - c2[:-n]) / n
    return np.sqrt(np.maximum(v - m * m, 0.0))


def build_adaptive(btc_close, alt_ohlc, ts, k_sigma, k_stop, k_target,
                   horizon_min, cost_bp, vol_window=240):
    r = np.diff(np.log(btc_close))
    sig = rolling_std(r, vol_window)          # causal: ends at bar t
    sig_prev = np.concatenate([[np.nan], sig[:-1]])   # strictly before signal
    ok = np.isfinite(sig_prev) & (sig_prev > 0)
    trig = np.abs(r) > k_sigma * sig_prev
    s = np.where(ok & trig, np.sign(r), 0)
    idx = np.flatnonzero(s != 0)
    idx = idx[idx + 2 < len(btc_close)]
    side = s[idx].astype(np.int8)
    starts = idx + 1
    vol = sig_prev[idx]

    legs = []
    for name, (O, H, L) in alt_ohlc.items():
        entry = O[starts]
        sb = k_stop * vol
        tb = k_target * vol
        stop = entry * (1 - side * sb)
        tgt = entry * (1 + side * tb)
        out, _ = first_touch(H, L, starts, entry, stop, tgt, side, horizon_min)
        legs.append(np.where(out == 1, tb, np.where(out == -1, -sb, 0.0)))
    basket = np.vstack(legs).mean(axis=0)

    tmin = ts[starts]
    keep, last = [], -1 << 62
    for i, t in enumerate(tmin):
        if t - last >= horizon_min * 60_000:
            keep.append(i)
            last = t
    keep = np.array(keep, dtype=np.int64)
    return keep, basket[keep] - cost_bp / 1e4, tmin[keep]
