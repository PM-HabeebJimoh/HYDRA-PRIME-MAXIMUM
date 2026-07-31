"""v01T signal exactly as specified, resolved on real 1-minute paths."""
import numpy as np
from .indicators import bb_percent, hv_ratio, score_of


def v01t_signals(sig_close, bb_lo=10.0, bb_hi=90.0, hv_max=0.8, score_min=85):
    bb = bb_percent(sig_close)
    hv = hv_ratio(sig_close)
    sc = score_of(bb)
    g1 = (bb < bb_lo) | (bb > bb_hi)
    g2 = hv < hv_max
    g3 = sc >= score_min
    ok = np.isfinite(bb) & np.isfinite(hv) & g1 & g2 & g3
    side = np.where(bb < bb_lo, +1, -1)   # band-revert: low band -> long
    return ok, side, bb, hv, sc
