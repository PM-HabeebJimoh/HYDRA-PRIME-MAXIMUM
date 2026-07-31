"""v01T-OMEGA engine on the per-asset panel. Real bars only, weight 0 when absent."""
import numpy as np
from .adaptive import rolling_std


def _first_touch_nan(high, low, s, e, entry, stop, target, side):
    hi = high[s:e]
    lo = low[s:e]
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
        return 0
    return -1 if i_s <= i_t else +1     # tie inside one bar -> adverse


def run(ts, btc_close, panel, k_sigma, k_stop, k_target, horizon_min,
        cost_bp, vol_window=240, entry_delay=0, min_legs=3):
    r = np.diff(np.log(btc_close))
    sg = rolling_std(r, vol_window)
    sp = np.concatenate([[np.nan], sg[:-1]])
    ok = np.isfinite(sp) & (sp > 0)
    s = np.where(ok & (np.abs(r) > k_sigma * sp), np.sign(r), 0)
    idx = np.flatnonzero(s != 0)
    idx = idx[idx + 2 + entry_delay < len(btc_close)]

    N = len(btc_close)
    names = list(panel)
    out_ret, out_ts, out_n = [], [], []
    last = -(1 << 62)
    for i in idx:
        t = ts[i]
        if t - last < horizon_min * 60_000:
            continue
        st = i + 1 + entry_delay
        en = min(st + horizon_min, N)
        side = int(s[i])
        vol = sp[i]
        sb, tb = k_stop * vol, k_target * vol
        legs = []
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
            o = _first_touch_nan(hi[m], lo[m], 0, m.sum(), e0,
                                 e0 * (1 - side * sb), e0 * (1 + side * tb), side)
            legs.append(tb if o == 1 else (-sb if o == -1 else 0.0))
        if len(legs) < min_legs:
            continue
        out_ret.append(float(np.mean(legs)) - cost_bp / 1e4)
        out_ts.append(t)
        out_n.append(len(legs))
        last = t
    return np.array(out_ret), np.array(out_ts, dtype=np.int64), np.array(out_n)
