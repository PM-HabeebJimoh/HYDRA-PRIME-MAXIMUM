"""Barriers scaled to the TRADED instrument's own volatility.

This corrects a unit error that was invisible until the signal was decomposed.
The impulse is detected in BTC space (|r_btc| > k*sigma_btc), but the position
is held in ALT space. Sizing the barriers with sigma_BTC therefore applies the
wrong yardstick: in 2017 the alts were 2-4x more volatile than BTC, so a
"1.5 sigma_btc" stop was a fraction of an alt sigma and was hit by pure alt
noise before the lead-lag impulse could arrive.

Measured pure signal strength E[alt_{t+1}|impulse]/sigma_alt is positive and
large in every year (2017 +0.399, 2018 +0.280, 2019 +0.264), so the edge was
always there -- only the barrier yardstick was wrong.
"""
import numpy as np
from .adaptive import rolling_std


def alt_vol(panel_close, window=240):
    """Trailing realised vol of the alt's own 1m log returns, causal."""
    lc = np.log(panel_close)
    r = np.diff(lc)
    r = np.where(np.isfinite(r), r, 0.0)
    s = rolling_std(r, window)
    return np.concatenate([[np.nan], s])          # sigma known at bar t-1


def _touch(hi, lo, entry, stop, target, side):
    if side > 0:
        ts_ = np.flatnonzero(lo <= stop)
        tt_ = np.flatnonzero(hi >= target)
    else:
        ts_ = np.flatnonzero(hi >= stop)
        tt_ = np.flatnonzero(lo <= target)
    BIG = 1 << 60
    i_s = ts_[0] if ts_.size else BIG
    i_t = tt_[0] if tt_.size else BIG
    if i_s == BIG and i_t == BIG:
        return 0, len(hi)
    if i_s <= i_t:
        return -1, int(i_s) + 1
    return 1, int(i_t) + 1


def emit(ts, btc_close, panel, k_sigma, k_stop, k_target, horizon_min,
         cost_bp, vol_window=240, entry_delay=0, min_edge_mult=0.0):
    r = np.diff(np.log(btc_close))
    sg = rolling_std(r, vol_window)
    sp = np.concatenate([[np.nan], sg[:-1]])
    ok = np.isfinite(sp) & (sp > 0)
    s = np.where(ok & (np.abs(r) > k_sigma * sp), np.sign(r), 0)
    idx = np.flatnonzero(s != 0)
    idx = idx[idx + 2 + entry_delay < len(btc_close)]
    N = len(btc_close)

    av = {nm: alt_vol(panel[nm]["close"], vol_window) for nm in panel}
    ev = []
    for i in idx:
        st = i + 1 + entry_delay
        en = min(st + horizon_min, N)
        side = int(s[i])
        for nm in panel:
            p = panel[nm]
            if not p["present"][st]:
                continue
            e0 = p["open"][st]
            va = av[nm][i]                      # alt sigma known before entry
            if not (np.isfinite(e0) and np.isfinite(va) and va > 0):
                continue
            # cost physics: the target must clear the fee by a real margin
            if k_target * va < min_edge_mult * (cost_bp / 1e4):
                continue
            hi = p["high"][st:en]
            lo = p["low"][st:en]
            m = np.isfinite(hi) & np.isfinite(lo)
            if m.sum() < 2:
                continue
            sb, tb = k_stop * va, k_target * va
            o, nb = _touch(hi[m], lo[m], e0,
                           e0 * (1 - side * sb), e0 * (1 + side * tb), side)
            ret = tb if o == 1 else (-sb if o == -1 else 0.0)
            ev.append((int(st), int(min(st + nb, N)),
                       float(ret - cost_bp / 1e4), nm, int(i)))
    return ev
