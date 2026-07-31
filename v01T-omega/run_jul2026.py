"""v01T July 2026 backtest: original fixed barriers vs ATR-scaled correction.

Data: real Bitfinex 6h candles, 2026-07-01 to 2026-08-01, fetched live.
Both variants use identical v01T gates; only the barriers differ.
"""
import json, sys
import numpy as np

sys.path.insert(0, "/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega")
from omega.indicators import bb_percent, hv_ratio, score_of
from omega.straddle_fix import atr_fraction, barriers, resolve_straddle

JUL0, JUL1 = 1782864000000, 1785542400000


def load(path):
    d = json.load(open(path))
    ts = np.array(sorted(int(k) for k in d), dtype=np.int64)
    ts = ts[(ts >= JUL0) & (ts < JUL1)]
    g = lambda i: np.array([d[str(t)][i] for t in ts])
    return ts, g(0), g(1), g(2), g(3)      # ts, open, close, high, low


def signals(C):
    bb = bb_percent(C, 20)
    hv = hv_ratio(C)
    sc = score_of(bb)
    elite = (np.isfinite(bb) & np.isfinite(hv)
             & ((bb < 10) | (bb > 90)) & (hv < 0.8) & (sc >= 85))
    return np.flatnonzero(elite), bb, hv, sc


def run(name, path, mode, W=4, k_stop=1.5, k_target=1.75,
        sl_fixed=0.0005, tp_fixed=0.005):
    ts, O, C, H, L = load(path)
    idx, bb, hv, sc = signals(C)
    idx = idx[(idx + 1) < len(C) - 1]
    atrf = atr_fraction(H, L, C, 20)

    both = wins = 0
    rets, detail = [], []
    for k in idx:
        e = O[k + 1]
        if mode == "atr":
            b = barriers(atrf[k], k_stop, k_target)
            if b is None:
                continue
            sl, tp = b
        else:
            sl, tp = sl_fixed, tp_fixed
        hi, lo = H[k + 1:k + 1 + W], L[k + 1:k + 1 + W]
        if len(hi) < 2:
            continue
        rl, rs, bs = resolve_straddle(hi, lo, e, sl, tp)
        both += bs
        if rl == tp or rs == tp:
            wins += 1
        rets.append(rl + rs)
        detail.append((int(ts[k]), float(bb[k]), float(hv[k]),
                       sl, tp, rl, rs, rl + rs))
    n = len(rets)
    r = np.array(rets) if n else np.array([0.0])
    return dict(name=name, mode=mode, bars=len(C), squeezes=len(idx), n=n,
                both=both, both_pct=both / n * 100 if n else 0,
                tp_pct=wins / n * 100 if n else 0,
                ev_bp=float(r.mean() * 1e4), detail=detail)
