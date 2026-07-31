"""Emit EVERY signal with its real resolution bar. Nothing discarded."""
import numpy as np
from .adaptive import rolling_std


def _touch(hi, lo, entry, stop, target, side):
    """Return (outcome, bars_to_resolve). Tie inside one bar -> adverse."""
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
         cost_bp, vol_window=240, entry_delay=0, per_leg=True):
    """Yield one event per (signal, instrument) leg -- these are genuinely
    separate positions in separate books, so they may overlap in time."""
    r = np.diff(np.log(btc_close))
    sg = rolling_std(r, vol_window)
    sp = np.concatenate([[np.nan], sg[:-1]])
    ok = np.isfinite(sp) & (sp > 0)
    s = np.where(ok & (np.abs(r) > k_sigma * sp), np.sign(r), 0)
    idx = np.flatnonzero(s != 0)
    idx = idx[idx + 2 + entry_delay < len(btc_close)]
    N = len(btc_close)
    names = list(panel)
    ev = []
    for i in idx:
        st = i + 1 + entry_delay
        en = min(st + horizon_min, N)
        side = int(s[i])
        vol = sp[i]
        sb, tb = k_stop * vol, k_target * vol
        for nm in names:
            p = panel[nm]
            if not p["present"][st]:
                continue
            e0 = p["open"][st]
            if not np.isfinite(e0):
                continue
            hi = p["high"][st:en]
            lo = p["low"][st:en]
            m = np.isfinite(hi) & np.isfinite(lo)
            if m.sum() < 2:
                continue
            o, nb = _touch(hi[m], lo[m], e0,
                           e0 * (1 - side * sb), e0 * (1 + side * tb), side)
            ret = tb if o == 1 else (-sb if o == -1 else 0.0)
            ev.append((int(st), int(min(st + nb, N)), float(ret - cost_bp / 1e4), nm, int(i)))
    return ev
