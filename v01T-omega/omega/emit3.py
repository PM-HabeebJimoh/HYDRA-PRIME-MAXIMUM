"""Signal emission with alt-scaled barriers + causal liquidity gating."""
import numpy as np
from .adaptive import rolling_std
from .altscaled import alt_vol, _touch
from .liquidity import tradable_mask


def emit(ts, btc_close, panel, k_sigma, k_stop, k_target, horizon_min,
         cost_bp, vol_window=240, min_edge_mult=3.0, entry_delay=0,
         liq_window=1440, min_cov=0.90):
    r = np.diff(np.log(btc_close))
    sg = rolling_std(r, vol_window)
    sp = np.concatenate([[np.nan], sg[:-1]])
    ok = np.isfinite(sp) & (sp > 0)
    s = np.where(ok & (np.abs(r) > k_sigma * sp), np.sign(r), 0)
    idx = np.flatnonzero(s != 0)
    idx = idx[idx + 2 + entry_delay < len(btc_close)]
    N = len(btc_close)

    av = {nm: alt_vol(panel[nm]["close"], vol_window) for nm in panel}
    tm = tradable_mask(panel, liq_window, min_cov)

    ev = []
    for i in idx:
        st = i + 1 + entry_delay
        en = min(st + horizon_min, N)
        side = int(s[i])
        for nm in panel:
            p = panel[nm]
            if not tm[nm][i]:            # not continuously quoted -> untradable
                continue
            if not p["present"][st]:
                continue
            e0 = p["open"][st]
            va = av[nm][i]
            if not (np.isfinite(e0) and np.isfinite(va) and va > 0):
                continue
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
