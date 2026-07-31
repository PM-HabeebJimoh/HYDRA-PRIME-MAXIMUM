"""v01T on real PERPETUAL FUTURES, July 2026.

Why futures changes the model fundamentally:

  SPOT   a simultaneous long and short of equal size is exactly zero net
         exposure. Long P&L + short P&L = 0 on every path. The v01T double
         entry is not executable - you pay two spreads to hold nothing.

  PERP   hedge mode lets you carry a long position AND a short position on
         the same contract as two separate books. Each has its own liquidation
         price, its own stop, and its own margin. The straddle is real.

Extra costs that only exist on futures:
  * funding, paid every 8h by whichever side is crowded
  * taker fee on 2 legs in and 2 legs out
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
    return ts, g(0), g(1), g(2), g(3)


def run(path, mode, W, fee_per_leg=0.0, funding_per_8h=0.0):
    """mode 'fixed' = original v01T, 'atr' = corrected."""
    ts, O, C, H, L = load(path)
    bb = bb_percent(C, 20)
    hv = hv_ratio(C)
    sc = score_of(bb)
    elite = (np.isfinite(bb) & np.isfinite(hv)
             & ((bb < 10) | (bb > 90)) & (hv < 0.8) & (sc >= 85))
    idx = np.flatnonzero(elite)
    idx = idx[(idx + 1) < len(C) - 1]
    atrf = atr_fraction(H, L, C, 20)

    out, both = [], 0
    for k in idx:
        e = O[k + 1]
        if mode == "atr":
            b = barriers(atrf[k], 1.5, 1.75)
            if b is None:
                continue
            sl, tp = b
        else:
            sl, tp = 0.0005, 0.005
        hi, lo = H[k + 1:k + 1 + W], L[k + 1:k + 1 + W]
        if len(hi) < 2:
            continue
        rl, rs, bs = resolve_straddle(hi, lo, e, sl, tp)
        both += bs
        # 6h bars: each bar is 0.75 of an 8h funding period.
        # A long and a short on the same contract pay/receive funding
        # symmetrically, so net funding on a balanced straddle is ~0.
        # Only the fee is unavoidable: 2 legs x (in + out).
        gross = rl + rs
        cost = 4 * fee_per_leg
        out.append((int(ts[k]), gross - cost))
    return out, both, len(idx)


def stats(tr, start=10000.0, lev=1.0):
    if not tr:
        return dict(n=0, wr=0.0, roi=0.0, dd=0.0, final=start, wins=0, losses=0)
    r = np.array([x[1] for x in tr])
    eq = start * np.cumprod(1 + lev * r)
    curve = np.concatenate([[start], eq])
    peak = np.maximum.accumulate(curve)
    return dict(n=len(r), wr=float((r > 0).mean() * 100),
                roi=float((curve[-1] / start - 1) * 100),
                dd=float(np.max((peak - curve) / peak) * 100),
                final=float(curve[-1]),
                wins=int((r > 0).sum()), losses=int((r <= 0).sum()))
